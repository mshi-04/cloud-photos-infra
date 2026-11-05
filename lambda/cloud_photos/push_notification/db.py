import functools
import os
from typing import TYPE_CHECKING, Any

import boto3

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.dynamodb import deserialize_item, serialize_item
from cloud_photos.common.tables import FIELD_DEVICE_TOKEN, FIELD_USER_ID

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_dynamodb import DynamoDBClient


@functools.cache
def get_dynamodb_client() -> "DynamoDBClient":
    return boto3.client("dynamodb")


@functools.cache
def get_table_name() -> str:
    return os.environ["TABLE_NAME"]


def query_device_tokens(identity_id: IdentityId) -> list[DeviceToken]:
    """Return every device token of the user, following LastEvaluatedKey across pages."""
    params: dict[str, Any] = {
        "TableName": get_table_name(),
        "KeyConditionExpression": "#uid = :uid",
        "ExpressionAttributeNames": {"#uid": FIELD_USER_ID},
        "ExpressionAttributeValues": serialize_item({":uid": identity_id.value}),
        "ProjectionExpression": FIELD_DEVICE_TOKEN,
    }
    tokens: list[DeviceToken] = []
    while True:
        result = get_dynamodb_client().query(**params)
        tokens.extend(DeviceToken.parse(deserialize_item(item)[FIELD_DEVICE_TOKEN]) for item in result.get("Items", []))
        # A page can be empty and still have more pages after it.
        last_evaluated_key = result.get("LastEvaluatedKey")
        if not last_evaluated_key:
            return tokens
        params["ExclusiveStartKey"] = last_evaluated_key


def delete_device_token(identity_id: IdentityId, device_token: DeviceToken) -> None:
    get_dynamodb_client().delete_item(
        TableName=get_table_name(),
        Key=serialize_item({FIELD_USER_ID: identity_id.value, FIELD_DEVICE_TOKEN: device_token.value}),
    )
