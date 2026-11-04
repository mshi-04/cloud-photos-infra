import functools
import os
import time
from typing import TYPE_CHECKING, Any

import boto3

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.dynamodb import serialize_item
from cloud_photos.common.tables import FIELD_DEVICE_TOKEN, FIELD_USER_ID
from cloud_photos.device_tokens.constants import (
    FIELD_PLATFORM,
    FIELD_REGISTERED_AT,
    FIELD_UPDATED_AT,
)
from cloud_photos.device_tokens.models import Platform

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_dynamodb import DynamoDBClient


@functools.cache
def get_dynamodb_client() -> "DynamoDBClient":
    return boto3.client("dynamodb")


@functools.cache
def get_table_name() -> str:
    return os.environ["TABLE_NAME"]


def _key(identity_id: IdentityId, device_token: DeviceToken) -> dict[str, Any]:
    # The raw values are taken out only here, right before the DynamoDB call.
    return serialize_item({FIELD_USER_ID: identity_id.value, FIELD_DEVICE_TOKEN: device_token.value})


def save_device_token(identity_id: IdentityId, device_token: DeviceToken, platform: Platform) -> None:
    """Create the token, or update its platform while keeping the first registration time."""
    now = int(time.time() * 1000)
    get_dynamodb_client().update_item(
        TableName=get_table_name(),
        Key=_key(identity_id, device_token),
        UpdateExpression="SET #platform = :platform, #registeredAt = if_not_exists(#registeredAt, :now), #updatedAt = :now",
        ExpressionAttributeNames={
            "#platform": FIELD_PLATFORM,
            "#registeredAt": FIELD_REGISTERED_AT,
            "#updatedAt": FIELD_UPDATED_AT,
        },
        ExpressionAttributeValues=serialize_item({":platform": platform.value, ":now": now}),
    )


def delete_device_token(identity_id: IdentityId, device_token: DeviceToken) -> None:
    get_dynamodb_client().delete_item(TableName=get_table_name(), Key=_key(identity_id, device_token))
