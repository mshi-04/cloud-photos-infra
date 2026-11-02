import functools
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cloud_photos.common.auth import IdentityId
from cloud_photos.media_uploads.constants import (
    FIELD_CLOUD_STORAGE_PATH,
    FIELD_CONTENT_TYPE,
    FIELD_FILE_SIZE,
    FIELD_IS_DELETED,
    FIELD_MEDIA_ID,
    FIELD_MEDIA_TYPE,
    FIELD_UPDATED_AT,
    FIELD_UPLOADED_AT,
    FIELD_USER_ID,
)
from cloud_photos.media_uploads.models import CreateUploadRecordRequest, MediaId, PageCursor, PageLimit

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_dynamodb import DynamoDBClient

CONDITIONAL_CHECK_FAILED: Final = "ConditionalCheckFailedException"

_serializer = TypeSerializer()
_deserializer = TypeDeserializer()


@functools.cache
def get_dynamodb_client() -> "DynamoDBClient":
    return boto3.client("dynamodb")


@functools.cache
def get_table_name() -> str:
    return os.environ["TABLE_NAME"]


def serialize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: _serializer.serialize(v) for k, v in item.items()}


def _convert_decimals(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    if isinstance(value, Mapping):
        return {k: _convert_decimals(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_convert_decimals(v) for v in value]
    return value


def deserialize_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: _convert_decimals(_deserializer.deserialize(v)) for k, v in item.items()}


def _key(identity_id: IdentityId, media_id: MediaId) -> dict[str, Any]:
    # The raw values are taken out only here, right before the DynamoDB call.
    return serialize_item({FIELD_USER_ID: identity_id.value, FIELD_MEDIA_ID: media_id.value})


def _is_conditional_check_failure(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") == CONDITIONAL_CHECK_FAILED


def put_upload_record(identity_id: IdentityId, request: CreateUploadRecordRequest, uploaded_at: int) -> bool:
    """Create the upload record. Return False without changing it when the record already exists."""
    item: dict[str, Any] = {
        FIELD_USER_ID: identity_id.value,
        FIELD_MEDIA_ID: request.media_id.value,
        FIELD_CLOUD_STORAGE_PATH: request.cloud_storage_path.value,
        FIELD_CONTENT_TYPE: request.content_type,
        FIELD_MEDIA_TYPE: request.media_type.value,
        FIELD_UPLOADED_AT: uploaded_at,
    }
    if request.file_size is not None:
        item[FIELD_FILE_SIZE] = request.file_size.value

    try:
        get_dynamodb_client().put_item(
            TableName=get_table_name(),
            Item=serialize_item(item),
            ConditionExpression=f"attribute_not_exists({FIELD_USER_ID}) AND attribute_not_exists({FIELD_MEDIA_ID})",
        )
    except ClientError as e:
        if _is_conditional_check_failure(e):
            return False
        raise
    return True


def mark_upload_record_deleted(identity_id: IdentityId, media_id: MediaId) -> bool:
    """Logically delete the upload record. Return False when the record does not exist."""
    updated_at = int(time.time() * 1000)
    try:
        get_dynamodb_client().update_item(
            TableName=get_table_name(),
            Key=_key(identity_id, media_id),
            UpdateExpression=f"SET {FIELD_IS_DELETED} = :val, {FIELD_UPDATED_AT} = :time",
            ExpressionAttributeValues=serialize_item({":val": True, ":time": updated_at}),
            ConditionExpression=f"attribute_exists({FIELD_USER_ID})",
        )
    except ClientError as e:
        if _is_conditional_check_failure(e):
            return False
        raise
    return True


@dataclass(frozen=True, slots=True)
class UploadRecordPage:
    records: list[dict[str, Any]]
    last_evaluated_key: dict[str, Any] | None


def query_upload_records(identity_id: IdentityId, limit: PageLimit, cursor: PageCursor | None) -> UploadRecordPage:
    """Return one page of the caller's upload records, with numbers converted to plain JSON types."""
    params: dict[str, Any] = {
        "TableName": get_table_name(),
        "KeyConditionExpression": f"{FIELD_USER_ID} = :user_id",
        "ExpressionAttributeValues": serialize_item({":user_id": identity_id.value}),
        "Limit": limit.value,
    }
    if cursor is not None:
        params["ExclusiveStartKey"] = _key(cursor.identity_id, cursor.media_id)

    response = get_dynamodb_client().query(**params)
    last_evaluated_key = response.get("LastEvaluatedKey")
    return UploadRecordPage(
        records=[deserialize_item(item) for item in response.get("Items", [])],
        last_evaluated_key=None if last_evaluated_key is None else deserialize_item(last_evaluated_key),
    )
