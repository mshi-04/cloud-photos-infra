import json
import logging
import os
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, messaging

from cloud_photos.push_notification import auth
from cloud_photos.push_notification import response
from cloud_photos.push_notification.constants import FIELD_DEVICE_TOKEN, FIELD_USER_ID

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Firebase App is reused across warm starts
_firebase_app: Optional[firebase_admin.App] = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    import boto3

    secret_arn = os.environ["FIREBASE_CREDENTIALS_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    secret_value = client.get_secret_value(SecretId=secret_arn)
    service_account_info = json.loads(secret_value["SecretString"])

    cred = credentials.Certificate(service_account_info)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _query_device_tokens(dynamodb, table_name: str, user_id: str) -> List[str]:
    params: Dict[str, Any] = {
        "TableName": table_name,
        "KeyConditionExpression": "#uid = :uid",
        "ExpressionAttributeNames": {"#uid": FIELD_USER_ID},
        "ExpressionAttributeValues": {":uid": {"S": user_id}},
        "ProjectionExpression": FIELD_DEVICE_TOKEN,
    }
    tokens: List[str] = []
    while True:
        result = dynamodb.query(**params)
        tokens.extend(item[FIELD_DEVICE_TOKEN]["S"] for item in result.get("Items", []))
        # A page can be empty and still have more pages after it.
        last_evaluated_key = result.get("LastEvaluatedKey")
        if not last_evaluated_key:
            return tokens
        params["ExclusiveStartKey"] = last_evaluated_key


def _delete_device_token(dynamodb, table_name: str, user_id: str, token: str) -> None:
    dynamodb.delete_item(
        TableName=table_name,
        Key={
            FIELD_USER_ID: {"S": user_id},
            FIELD_DEVICE_TOKEN: {"S": token},
        },
    )


def _parse_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    return body


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    import boto3

    user_id = auth.get_identity_id(event)
    if not user_id:
        return response.error(401, "Unauthorized")

    body = _parse_body(event)
    if body is None:
        return response.error(400, "Invalid request body")

    success_count = body.get("successCount")
    # bool is a subclass of int, so reject it explicitly.
    if isinstance(success_count, bool) or not isinstance(success_count, int) or success_count < 0:
        return response.error(400, "successCount must be a non-negative integer")

    masked = auth.mask_identity(user_id)
    if success_count == 0:
        logger.info("Nothing uploaded, skipping notification: user=%s", masked)
        return response.success(204)

    table_name = os.environ["TABLE_NAME"]
    dynamodb = boto3.client("dynamodb")

    logger.info("Notifying upload complete: user=%s successCount=%d", masked, success_count)

    try:
        tokens = _query_device_tokens(dynamodb, table_name, user_id)
    except Exception:
        logger.exception("Failed to query device tokens: user=%s", masked)
        return response.error(500, "Internal server error")
    if not tokens:
        logger.info("No device tokens registered for user=%s", masked)
        return response.success(204)

    try:
        _get_firebase_app()
    except Exception:
        logger.exception("Failed to initialize Firebase: user=%s", masked)
        return response.error(500, "Internal server error")

    notification_body = f"{success_count}件のメディアをアップロードしました"
    notification = messaging.Notification(
        title="アップロード完了",
        body=notification_body,
    )

    sent_count = 0
    for token in tokens:
        message = messaging.Message(notification=notification, token=token)
        try:
            messaging.send(message)
            sent_count += 1
            logger.info("FCM sent: user=%s token=***%s", masked, token[-4:])
        except messaging.UnregisteredError:
            logger.info("Deleting unregistered token: user=%s token=***%s", masked, token[-4:])
            try:
                _delete_device_token(dynamodb, table_name, user_id, token)
            except Exception:
                # Keep sending to the other devices; the stale token is retried on the next notification.
                logger.exception("Failed to delete unregistered token: user=%s token=***%s", masked, token[-4:])
        except Exception as e:
            logger.error("FCM send failed: user=%s token=***%s error=%s", masked, token[-4:], e, exc_info=True)

    logger.info("Notification done: user=%s sent=%d total=%d", masked, sent_count, len(tokens))
    return response.success(201, {"sentCount": sent_count})
