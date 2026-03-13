import json
import time
from http import HTTPStatus
from typing import Any, Dict, Optional

from auth import get_identity_id
from constants import (
    FIELD_CLOUD_STORAGE_PATH,
    FIELD_CONTENT_TYPE,
    FIELD_FILE_SIZE,
    FIELD_MEDIA_ID,
    FIELD_MEDIA_TYPE,
    FIELD_UPLOADED_AT,
    FIELD_USER_ID,
    PRIVATE_PATH_PREFIX,
)
from db import dynamodb_client, serialize_item, table_name
from models import CreateUploadRecordRequest, ValidationError
from response import error, success


def _parse_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    return body


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    identity_id = get_identity_id(event)
    if not identity_id:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body_dict = _parse_body(event)
    if body_dict is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    try:
        request_data = CreateUploadRecordRequest.from_dict(body_dict)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    # IDOR prevention: verify cloudStoragePath belongs to the requester
    expected_prefix = f"{PRIVATE_PATH_PREFIX}{identity_id}/"
    if not request_data.cloud_storage_path.startswith(expected_prefix):
        return error(HTTPStatus.FORBIDDEN, "cloudStoragePath does not match your identity")

    item = {
        FIELD_USER_ID: identity_id,
        FIELD_MEDIA_ID: request_data.media_id,
        FIELD_CLOUD_STORAGE_PATH: request_data.cloud_storage_path,
        FIELD_CONTENT_TYPE: request_data.content_type,
        FIELD_MEDIA_TYPE: request_data.media_type,
        FIELD_UPLOADED_AT: int(time.time() * 1000),
    }

    if request_data.file_size is not None:
        item[FIELD_FILE_SIZE] = request_data.file_size

    condition = f"attribute_not_exists({FIELD_USER_ID}) AND attribute_not_exists({FIELD_MEDIA_ID})"
    try:
        dynamodb_client.put_item(
            TableName=table_name,
            Item=serialize_item(item),
            ConditionExpression=condition,
        )
    except dynamodb_client.exceptions.ConditionalCheckFailedException:
        return success(HTTPStatus.OK, {"message": "Record already exists, skipped"})

    return success(HTTPStatus.CREATED, {"message": "created"})
