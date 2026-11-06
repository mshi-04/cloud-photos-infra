import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.errors import ValidationError
from cloud_photos.common.response import error, success
from cloud_photos.media_uploads.db import mark_upload_record_deleted
from cloud_photos.media_uploads.models import DeleteUploadRecordRequest

logger = logging.getLogger(__name__)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    try:
        request = DeleteUploadRecordRequest.parse(event.get("pathParameters"))
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    try:
        deleted = mark_upload_record_deleted(identity_id, request.media_id)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to logically delete item: userId=%s, mediaId=%s", identity_id, request.media_id.value)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    if not deleted:
        return error(HTTPStatus.NOT_FOUND, "Media not found")
    return success(HTTPStatus.OK, {"message": "logically deleted"})
