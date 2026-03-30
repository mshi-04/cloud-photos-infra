import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boto3
import pytest
from moto import mock_aws

import delete_user

S3_BUCKET_NAME = "test-media-bucket"
UPLOAD_RECORDS_TABLE_NAME = "test-upload-records"
DEVICE_TOKENS_TABLE_NAME = "test-device-tokens"
REGION = "ap-northeast-1"


@pytest.fixture
def aws_resources():
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = REGION
        os.environ["S3_BUCKET_NAME"] = S3_BUCKET_NAME
        os.environ["UPLOAD_RECORDS_TABLE_NAME"] = UPLOAD_RECORDS_TABLE_NAME
        os.environ["DEVICE_TOKENS_TABLE_NAME"] = DEVICE_TOKENS_TABLE_NAME

        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket=S3_BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        s3.put_bucket_versioning(
            Bucket=S3_BUCKET_NAME,
            VersioningConfiguration={"Status": "Enabled"},
        )

        dynamodb = boto3.client("dynamodb", region_name=REGION)
        dynamodb.create_table(
            TableName=UPLOAD_RECORDS_TABLE_NAME,
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
        dynamodb.create_table(
            TableName=DEVICE_TOKENS_TABLE_NAME,
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

        delete_user._reset_for_testing()

        yield {"s3": s3, "dynamodb": dynamodb}

        delete_user._reset_for_testing()
        del os.environ["S3_BUCKET_NAME"]
        del os.environ["UPLOAD_RECORDS_TABLE_NAME"]
        del os.environ["DEVICE_TOKENS_TABLE_NAME"]
        del os.environ["AWS_DEFAULT_REGION"]
