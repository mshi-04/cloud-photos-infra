import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from cloud_photos.media_uploads.auth import IdentityId
from cloud_photos.media_uploads.constants import FIELD_MEDIA_ID
from cloud_photos.media_uploads.db import mark_upload_record_deleted
from cloud_photos.media_uploads.models import MediaId
from cloud_photos.media_uploads.response import error, success

logger = logging.getLogger(__name__)


def _media_id_from_path(event: Mapping[str, Any]) -> MediaId | None:
    path_parameters = event.get("pathParameters")
    if not isinstance(path_parameters, Mapping):
        return None
    media_id = path_parameters.get(FIELD_MEDIA_ID)
    if not isinstance(media_id, str) or not media_id:
        return None
    return MediaId(media_id)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    media_id = _media_id_from_path(event)
    if media_id is None:
        return error(HTTPStatus.BAD_REQUEST, "Missing mediaId")

    try:
        deleted = mark_upload_record_deleted(identity_id, media_id)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to logically delete item: userId=%s, mediaId=%s", identity_id, media_id.value)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    if not deleted:
        return error(HTTPStatus.NOT_FOUND, "Media not found")
    return success(HTTPStatus.OK, {"message": "logically deleted"})
