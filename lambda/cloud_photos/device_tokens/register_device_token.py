import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from cloud_photos.common.errors import ValidationError
from cloud_photos.common.request import parse_body
from cloud_photos.device_tokens.auth import IdentityId
from cloud_photos.device_tokens.db import save_device_token
from cloud_photos.device_tokens.models import RegisterDeviceTokenRequest
from cloud_photos.device_tokens.response import error, success

logger = logging.getLogger(__name__)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body = parse_body(event)
    if body is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    try:
        request = RegisterDeviceTokenRequest.parse(body)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    try:
        save_device_token(identity_id, request.device_token, request.platform)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to register device token: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    return success(HTTPStatus.CREATED, {"message": "registered"})
