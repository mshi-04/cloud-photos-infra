import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.errors import AuthorizationError, ValidationError
from cloud_photos.common.response import error, success
from cloud_photos.media_uploads.db import query_upload_records
from cloud_photos.media_uploads.models import GetUploadRecordsRequest

logger = logging.getLogger(__name__)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.FORBIDDEN, "Unauthorized")

    params = event.get("queryStringParameters") or {}
    try:
        request = GetUploadRecordsRequest.parse(params, identity_id)
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))
    except AuthorizationError as e:
        return error(HTTPStatus.FORBIDDEN, str(e))

    try:
        page = query_upload_records(identity_id, request.limit, request.cursor)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to query upload records: userId=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    body: dict[str, Any] = {"records": page.records}
    if page.last_evaluated_key is not None:
        body["lastEvaluatedKey"] = page.last_evaluated_key
    return success(HTTPStatus.OK, body)
