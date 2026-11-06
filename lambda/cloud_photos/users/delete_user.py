import functools
import logging
import os
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Any

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.response import error, success
from cloud_photos.common.tables import FIELD_DEVICE_TOKEN, FIELD_MEDIA_ID
from cloud_photos.users.constants import (
    SUBSYSTEM_DEVICE_TOKENS,
    SUBSYSTEM_S3,
    SUBSYSTEM_UPLOAD_RECORDS,
)
from cloud_photos.users.db import delete_dynamodb_records
from cloud_photos.users.storage import delete_s3_objects

logger = logging.getLogger(__name__)
# The deletion of a user's data is recorded even when the runtime's default level is WARNING.
logger.setLevel(logging.INFO)


def _try_delete(subsystem: str, identity_id: IdentityId, delete: Callable[[], None]) -> bool:
    """Run one store's deletion and return whether it succeeded."""
    try:
        delete()
    except Exception:
        # Each store is deleted independently, so that a failure in one does not keep the user's data in the others.
        logger.exception("Failed to delete %s data for %s", subsystem, identity_id)
        return False
    return True


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.UNAUTHORIZED, "Unauthorized")

    # Read the whole configuration first, so that a missing variable stops the request before anything is deleted.
    bucket = os.environ["S3_BUCKET_NAME"]
    upload_records_table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]
    device_tokens_table = os.environ["DEVICE_TOKENS_TABLE_NAME"]

    logger.info("Deleting user data for %s", identity_id)

    deletions: list[tuple[str, Callable[[], None]]] = [
        (SUBSYSTEM_S3, functools.partial(delete_s3_objects, bucket, identity_id)),
        (
            SUBSYSTEM_UPLOAD_RECORDS,
            functools.partial(delete_dynamodb_records, upload_records_table, identity_id, FIELD_MEDIA_ID),
        ),
        (
            SUBSYSTEM_DEVICE_TOKENS,
            functools.partial(delete_dynamodb_records, device_tokens_table, identity_id, FIELD_DEVICE_TOKEN),
        ),
    ]
    failed_subsystems = [subsystem for subsystem, delete in deletions if not _try_delete(subsystem, identity_id, delete)]

    if failed_subsystems:
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Failed to delete data from: {', '.join(failed_subsystems)}")
    return success(HTTPStatus.OK, {"message": "User data deleted"})
