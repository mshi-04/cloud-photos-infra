import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from firebase_admin import messaging

from cloud_photos.common.auth import IdentityId
from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.errors import ValidationError
from cloud_photos.common.request import parse_body
from cloud_photos.push_notification.constants import FIELD_SUCCESS_COUNT
from cloud_photos.push_notification.db import delete_device_token, query_device_tokens
from cloud_photos.push_notification.fcm import build_upload_complete_notification, get_firebase_app, send_notification
from cloud_photos.push_notification.models import SuccessCount
from cloud_photos.push_notification.response import error, success

logger = logging.getLogger(__name__)
# This handler records each delivery at INFO, so it does not depend on the runtime's default level.
logger.setLevel(logging.INFO)


def handler(event: Mapping[str, Any], _context: object) -> dict[str, Any]:
    identity_id = IdentityId.from_event(event)
    if identity_id is None:
        return error(HTTPStatus.UNAUTHORIZED, "Unauthorized")

    body = parse_body(event)
    if body is None:
        return error(HTTPStatus.BAD_REQUEST, "Invalid request body")

    try:
        success_count = SuccessCount.parse(body.get(FIELD_SUCCESS_COUNT))
    except ValidationError as e:
        return error(HTTPStatus.BAD_REQUEST, str(e))

    if success_count.is_zero:
        logger.info("Nothing uploaded, skipping notification: user=%s", identity_id)
        return success(HTTPStatus.NO_CONTENT)

    logger.info("Notifying upload complete: user=%s successCount=%d", identity_id, success_count.value)

    try:
        tokens = query_device_tokens(identity_id)
    except (BotoCoreError, ClientError):
        logger.exception("Failed to query device tokens: user=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
    if not tokens:
        logger.info("No device tokens registered for user=%s", identity_id)
        return success(HTTPStatus.NO_CONTENT)

    try:
        get_firebase_app()
    except (BotoCoreError, ClientError, ValueError):
        # ValueError covers a secret that is not valid JSON or not a valid service account.
        logger.exception("Failed to initialize Firebase: user=%s", identity_id)
        return error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    notification = build_upload_complete_notification(success_count)
    sent_count = sum(_notify_device(identity_id, token, notification) for token in tokens)

    logger.info("Notification done: user=%s sent=%d total=%d", identity_id, sent_count, len(tokens))
    return success(HTTPStatus.CREATED, {"sentCount": sent_count})


def _notify_device(identity_id: IdentityId, device_token: DeviceToken, notification: messaging.Notification) -> bool:
    """Send to one device and return whether it was delivered. A failure never stops the other devices."""
    try:
        send_notification(device_token, notification)
    except messaging.UnregisteredError:
        logger.info("Deleting unregistered token: user=%s token=%s", identity_id, device_token)
        _delete_unregistered_token(identity_id, device_token)
        return False
    except Exception:
        # FCM reports network and server failures with several exception types. One device's failure,
        # whatever its type, must not stop delivery to the others, so it is recorded and skipped.
        logger.exception("FCM send failed: user=%s token=%s", identity_id, device_token)
        return False
    logger.info("FCM sent: user=%s token=%s", identity_id, device_token)
    return True


def _delete_unregistered_token(identity_id: IdentityId, device_token: DeviceToken) -> None:
    try:
        delete_device_token(identity_id, device_token)
    except (BotoCoreError, ClientError):
        # Keep sending to the other devices; the stale token is retried on the next notification.
        logger.exception("Failed to delete unregistered token: user=%s token=%s", identity_id, device_token)
