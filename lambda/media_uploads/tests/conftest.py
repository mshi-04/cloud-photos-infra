import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boto3
import pytest
from moto import mock_aws

import db

TABLE_NAME = "test-media-uploads"
REGION = "ap-northeast-1"


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
                {"AttributeName": "mediaId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "mediaId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        db._reset_for_testing()

        yield client

        db._reset_for_testing()
        del os.environ["TABLE_NAME"]
        del os.environ["AWS_DEFAULT_REGION"]
