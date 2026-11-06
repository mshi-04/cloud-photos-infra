import functools
import json
import os
from typing import TYPE_CHECKING, Final

import boto3
import firebase_admin
from firebase_admin import credentials, messaging

from cloud_photos.common.device_token import DeviceToken
from cloud_photos.push_notification.models import SuccessCount

if TYPE_CHECKING:
    # The stubs are a development dependency; the Lambda runtime never imports them.
    from mypy_boto3_secretsmanager import SecretsManagerClient

NOTIFICATION_TITLE: Final = "アップロード完了"


@functools.cache
def get_secretsmanager_client() -> "SecretsManagerClient":
    return boto3.client("secretsmanager")


@functools.cache
def get_firebase_app() -> firebase_admin.App:
    """Initialize Firebase once per execution environment. A failed attempt is not cached."""
    secret = get_secretsmanager_client().get_secret_value(SecretId=os.environ["FIREBASE_CREDENTIALS_SECRET_ARN"])
    service_account_info = json.loads(secret["SecretString"])
    return firebase_admin.initialize_app(credentials.Certificate(service_account_info))


def build_upload_complete_notification(success_count: SuccessCount) -> messaging.Notification:
    return messaging.Notification(title=NOTIFICATION_TITLE, body=f"{success_count.value}件のメディアをアップロードしました")


def send_notification(device_token: DeviceToken, notification: messaging.Notification) -> None:
    # The raw token is taken out only here, right before the FCM call.
    messaging.send(messaging.Message(notification=notification, token=device_token.value))
