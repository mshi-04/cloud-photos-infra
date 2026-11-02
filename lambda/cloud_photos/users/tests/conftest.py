import boto3
import pytest
from moto import mock_aws

from cloud_photos.users import delete_user

S3_BUCKET_NAME = "test-media-bucket"
UPLOAD_RECORDS_TABLE_NAME = "test-upload-records"
DEVICE_TOKENS_TABLE_NAME = "test-device-tokens"
REGION = "ap-northeast-1"


@pytest.fixture
def aws_resources(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("S3_BUCKET_NAME", S3_BUCKET_NAME)
    monkeypatch.setenv("UPLOAD_RECORDS_TABLE_NAME", UPLOAD_RECORDS_TABLE_NAME)
    monkeypatch.setenv("DEVICE_TOKENS_TABLE_NAME", DEVICE_TOKENS_TABLE_NAME)
    with mock_aws():
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

        # Recreate the cached clients inside the moto mock.
        delete_user.get_s3_client.cache_clear()
        delete_user.get_dynamodb_client.cache_clear()

        yield {"s3": s3, "dynamodb": dynamodb}

        delete_user.get_s3_client.cache_clear()
        delete_user.get_dynamodb_client.cache_clear()
