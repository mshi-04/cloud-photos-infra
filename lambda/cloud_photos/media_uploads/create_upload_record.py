import logging
import time
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from cloud_photos.common.errors import ValidationError
from cloud_photos.common.request import parse_body
from cloud_photos.media_uploads.auth import IdentityId
from cloud_photos.media_uploads.db import put_upload_record
from cloud_photos.media_uploads.models import CreateUploadRecordRequest
from cloud_photos.media_uploads.response import error, success

logger = logging.getLogger(__name__)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    body = parse_body(event)
    if body is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")

    try:
        request = CreateUploadRecordRequest.parse(body)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    # IDOR prevention: the record must point at an object under the caller's own prefix.
    if not request.cloud_storage_path.belongs_to(identity_id):
        return error(HTTPStatus.FORBIDDEN, "cloudStoragePath does not match your identity")

    uploaded_at = int(time.time() * 1000)
    try:
        created = put_upload_record(identity_id, request, uploaded_at)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to create upload record: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    if not created:
        return success(HTTPStatus.OK, {"message": "Record already exists, skipped"})
    return success(HTTPStatus.CREATED, {"message": "created", "uploadedAt": uploaded_at})
