from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from cloud_photos.push_notification import db, fcm, notify_upload_complete

TABLE_NAME = "test-device-tokens"
REGION = "ap-northeast-1"


@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    monkeypatch.setattr(notify_upload_complete, "get_firebase_app", MagicMock())


@pytest.fixture
def real_firebase_init(monkeypatch):
    """Use the real Firebase initialization, so that tests can make it fail."""
    monkeypatch.setattr(notify_upload_complete, "get_firebase_app", fcm.get_firebase_app)
    fcm.get_firebase_app.cache_clear()
    fcm.get_secretsmanager_client.cache_clear()
    yield
    fcm.get_firebase_app.cache_clear()
    fcm.get_secretsmanager_client.cache_clear()


@pytest.fixture
def dynamodb_table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    with mock_aws():
        client = boto3.client("dynamodb", region_name=REGION)
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "deviceToken", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "deviceToken", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Recreate the cached client and table name inside the moto mock.
        db.get_dynamodb_client.cache_clear()
        db.get_table_name.cache_clear()

        yield client

        db.get_dynamodb_client.cache_clear()
        db.get_table_name.cache_clear()
