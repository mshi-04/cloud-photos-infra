import functools
import logging
import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import boto3

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.dynamodb import serialize_item
from cloud_photos.common.tables import FIELD_USER_ID
from cloud_photos.users.constants import (
    BATCH_WRITE_BASE_WAIT_SECONDS,
    DYNAMODB_BATCH_WRITE_SIZE,
    MAX_BATCH_WRITE_RETRIES,
)

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_dynamodb import DynamoDBClient
    from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef, WriteRequestTypeDef

logger = logging.getLogger(__name__)


@functools.cache
def get_dynamodb_client() -> "DynamoDBClient":
    return boto3.client("dynamodb")


def _write_with_retries(dynamodb: "DynamoDBClient", table_name: str, requests: Sequence["WriteRequestTypeDef"]) -> None:
    """Run batch_write_item, retrying UnprocessedItems with exponential backoff."""
    unprocessed: Mapping[str, Sequence[Any]] = {table_name: requests}
    for attempt in range(MAX_BATCH_WRITE_RETRIES + 1):
        result = dynamodb.batch_write_item(RequestItems=unprocessed)
        unprocessed = result.get("UnprocessedItems", {})
        if not unprocessed:
            return
        if attempt == MAX_BATCH_WRITE_RETRIES:
            break
        wait = BATCH_WRITE_BASE_WAIT_SECONDS * (2**attempt)
        logger.warning(
            "UnprocessedItems in %s, retrying in %.1fs (attempt %d/%d)",
            table_name,
            wait,
            attempt + 1,
            MAX_BATCH_WRITE_RETRIES,
        )
        time.sleep(wait)
    raise RuntimeError(
        f"batch_write_item still had UnprocessedItems after {MAX_BATCH_WRITE_RETRIES} retries for table {table_name}"
    )


def _batch_delete_items(
    dynamodb: "DynamoDBClient",
    table_name: str,
    items: Sequence[Mapping[str, "AttributeValueTypeDef"]],
    sort_key_name: str,
) -> None:
    for start in range(0, len(items), DYNAMODB_BATCH_WRITE_SIZE):
        chunk = items[start : start + DYNAMODB_BATCH_WRITE_SIZE]
        requests: list[WriteRequestTypeDef] = [
            {"DeleteRequest": {"Key": {FIELD_USER_ID: item[FIELD_USER_ID], sort_key_name: item[sort_key_name]}}} for item in chunk
        ]
        _write_with_retries(dynamodb, table_name, requests)


def delete_dynamodb_records(table_name: str, identity_id: IdentityId, sort_key_name: str) -> None:
    """Delete every item of the user in the table, following LastEvaluatedKey across pages."""
    dynamodb = get_dynamodb_client()
    params: dict[str, Any] = {
        "TableName": table_name,
        "KeyConditionExpression": f"{FIELD_USER_ID} = :uid",
        "ExpressionAttributeValues": serialize_item({":uid": identity_id.value}),
        "ProjectionExpression": f"{FIELD_USER_ID}, {sort_key_name}",
    }
    while True:
        result = dynamodb.query(**params)
        _batch_delete_items(dynamodb, table_name, result.get("Items", []), sort_key_name)
        last_evaluated_key = result.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            return
        params = {**params, "ExclusiveStartKey": last_evaluated_key}
