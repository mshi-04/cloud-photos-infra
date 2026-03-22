import logging
import time
from http import HTTPStatus
from typing import Any, Dict

from auth import get_identity_id, mask_identity
from constants import (
    FIELD_DEVICE_TOKEN,
    FIELD_PLATFORM,
    FIELD_REGISTERED_AT,
    FIELD_UPDATED_AT,
    FIELD_USER_ID,
    VALID_PLATFORMS,
)
from db import dynamodb_client, serialize_item, table_name
from request_utils import parse_body
from response import error, success

logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    identity_id = get_identity_id(event)
    if not identity_id:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body_dict = parse_body(event)
    if body_dict is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    device_token = body_dict.get(FIELD_DEVICE_TOKEN)
    if not device_token or not isinstance(device_token, str):
        return error(HTTPStatus.BAD_REQUEST, "deviceToken is required")

    platform = body_dict.get(FIELD_PLATFORM)
    if platform not in VALID_PLATFORMS:
        return error(HTTPStatus.BAD_REQUEST, f"platform must be one of: {', '.join(VALID_PLATFORMS)}")

    now = int(time.time() * 1000)
    try:
        dynamodb_client.update_item(
            TableName=table_name,
            Key=serialize_item({
                FIELD_USER_ID: identity_id,
                FIELD_DEVICE_TOKEN: device_token,
            }),
            UpdateExpression=(
                "SET #platform = :platform, "
                "#registeredAt = if_not_exists(#registeredAt, :now), "
                "#updatedAt = :now"
            ),
            ExpressionAttributeNames={
                "#platform": FIELD_PLATFORM,
                "#registeredAt": FIELD_REGISTERED_AT,
                "#updatedAt": FIELD_UPDATED_AT,
            },
            ExpressionAttributeValues=serialize_item({
                ":platform": platform,
                ":now": now,
            }),
        )
    except Exception:
        logger.exception("Failed to register device token: userId=%s", mask_identity(identity_id))
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.CREATED, {"message": "registered"})
