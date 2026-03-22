import json
import logging
import time
from http import HTTPStatus
from typing import Any, Dict, Optional

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
from response import error, success

logger = logging.getLogger(__name__)


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

    device_token = body_dict.get(FIELD_DEVICE_TOKEN)
    if not device_token or not isinstance(device_token, str):
        return error(HTTPStatus.BAD_REQUEST, "deviceToken is required")

    platform = body_dict.get(FIELD_PLATFORM)
    if platform not in VALID_PLATFORMS:
        return error(HTTPStatus.BAD_REQUEST, f"platform must be one of: {', '.join(VALID_PLATFORMS)}")

    now = int(time.time() * 1000)
    try:
        dynamodb_client.put_item(
            TableName=table_name,
            Item=serialize_item({
                FIELD_USER_ID: identity_id,
                FIELD_DEVICE_TOKEN: device_token,
                FIELD_PLATFORM: platform,
                FIELD_REGISTERED_AT: now,
                FIELD_UPDATED_AT: now,
            }),
        )
    except Exception:
        logger.exception("Failed to register device token: userId=%s", mask_identity(identity_id))
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.CREATED, {"message": "registered"})
