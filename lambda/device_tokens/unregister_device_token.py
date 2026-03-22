import logging
from http import HTTPStatus
from typing import Any, Dict

from auth import get_identity_id, mask_identity
from constants import FIELD_DEVICE_TOKEN, FIELD_USER_ID
from db import get_dynamodb_client, get_table_name, serialize_item
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

    try:
        get_dynamodb_client().delete_item(
            TableName=get_table_name(),
            Key=serialize_item(
                {
                    FIELD_USER_ID: identity_id,
                    FIELD_DEVICE_TOKEN: device_token,
                }
            ),
        )
    except Exception:
        logger.exception("Failed to unregister device token: userId=%s", mask_identity(identity_id))
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.OK, {"message": "unregistered"})
