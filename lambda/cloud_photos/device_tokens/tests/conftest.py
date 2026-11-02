import boto3
import pytest
from moto import mock_aws

from cloud_photos.device_tokens import db

TABLE_NAME = "test-device-tokens"
REGION = "ap-northeast-1"


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
