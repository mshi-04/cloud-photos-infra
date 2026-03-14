import logging
import time
from http import HTTPStatus
from typing import Any, Dict

from auth import get_identity_id, mask_identity
from constants import FIELD_MEDIA_ID, FIELD_USER_ID
from db import dynamodb_client, serialize_item, table_name
from response import error, success

logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    identity_id = get_identity_id(event)
    if not identity_id:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    media_id = (event.get("pathParameters") or {}).get(FIELD_MEDIA_ID)
    if not media_id:
        return error(HTTPStatus.BAD_REQUEST, "Missing mediaId")

    key = {
        FIELD_USER_ID: identity_id,
        FIELD_MEDIA_ID: media_id,
    }
    
    updated_at = int(time.time() * 1000)

    try:
        dynamodb_client.update_item(
            TableName=table_name,
            Key=serialize_item(key),
            UpdateExpression="SET isDeleted = :val, updatedAt = :time",
            ExpressionAttributeValues={
                ":val": {"BOOL": True},
                ":time": {"N": str(updated_at)}
            }
        )
    except Exception:
        logger.exception("Failed to logically delete item: userId=%s, mediaId=%s", mask_identity(identity_id), media_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.OK, {"message": "logically deleted"})