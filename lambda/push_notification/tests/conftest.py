import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TABLE_NAME = "test-device-tokens"
REGION = "ap-northeast-1"


@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    import notify_upload_complete

    monkeypatch.setattr(notify_upload_complete, "_firebase_app", MagicMock())


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["TABLE_NAME"] = TABLE_NAME

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

        yield client

        del os.environ["TABLE_NAME"]
        del os.environ["AWS_DEFAULT_REGION"]
