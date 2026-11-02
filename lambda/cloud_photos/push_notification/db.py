import functools
import os
from typing import Any

import boto3
from botocore.client import BaseClient

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.device_token import DeviceToken
from cloud_photos.push_notification.constants import FIELD_DEVICE_TOKEN, FIELD_USER_ID


@functools.cache
def get_dynamodb_client() -> BaseClient:
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
        "ExpressionAttributeValues": {":uid": {"S": identity_id.value}},
        "ProjectionExpression": FIELD_DEVICE_TOKEN,
    }
    tokens: list[DeviceToken] = []
    while True:
        result = get_dynamodb_client().query(**params)
        tokens.extend(DeviceToken(item[FIELD_DEVICE_TOKEN]["S"]) for item in result.get("Items", []))
        # A page can be empty and still have more pages after it.
        last_evaluated_key = result.get("LastEvaluatedKey")
        if not last_evaluated_key:
            return tokens
        params["ExclusiveStartKey"] = last_evaluated_key


def delete_device_token(identity_id: IdentityId, device_token: DeviceToken) -> None:
    get_dynamodb_client().delete_item(
        TableName=get_table_name(),
        Key={
            FIELD_USER_ID: {"S": identity_id.value},
            FIELD_DEVICE_TOKEN: {"S": device_token.value},
        },
    )
