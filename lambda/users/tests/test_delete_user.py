import os

from moto import mock_aws

from delete_user import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"


def _make_event(identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
    }


@mock_aws
class TestDeleteUser:
    def test_returns_401_when_no_identity_id(self, aws_resources):
        event = {"requestContext": {"identity": {}}}
        resp = handler(event, None)
        assert resp["statusCode"] == 401

    def test_returns_200_when_no_data(self, aws_resources):
        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200

    def test_deletes_s3_objects(self, aws_resources):
        s3 = aws_resources["s3"]
        bucket = os.environ["S3_BUCKET_NAME"]
        s3.put_object(Bucket=bucket, Key=f"private/{IDENTITY_ID}/photo.jpg", Body=b"data")

        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200

        versions = s3.list_object_versions(Bucket=bucket, Prefix=f"private/{IDENTITY_ID}/")
        assert len(versions.get("Versions", [])) == 0
        assert len(versions.get("DeleteMarkers", [])) == 0

    def test_deletes_upload_records(self, aws_resources):
        dynamodb = aws_resources["dynamodb"]
        table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]
        dynamodb.put_item(
            TableName=table,
            Item={
                "userId": {"S": IDENTITY_ID},
                "mediaId": {"S": "media-001"},
                "cloudStoragePath": {"S": f"private/{IDENTITY_ID}/media-001.jpg"},
            },
        )

        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200

        result = dynamodb.query(
            TableName=table,
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": {"S": IDENTITY_ID}},
        )
        assert result["Count"] == 0

    def test_deletes_device_tokens(self, aws_resources):
        dynamodb = aws_resources["dynamodb"]
        table = os.environ["DEVICE_TOKENS_TABLE_NAME"]
        dynamodb.put_item(
            TableName=table,
            Item={
                "userId": {"S": IDENTITY_ID},
                "deviceToken": {"S": "token-001"},
                "platform": {"S": "android"},
            },
        )

        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200

        result = dynamodb.query(
            TableName=table,
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": {"S": IDENTITY_ID}},
        )
        assert result["Count"] == 0

    def test_deletes_chunked_upload_records(self, aws_resources):
        dynamodb = aws_resources["dynamodb"]
        table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]

        for i in range(30):
            dynamodb.put_item(
                TableName=table,
                Item={
                    "userId": {"S": IDENTITY_ID},
                    "mediaId": {"S": f"media-{i:03d}"},
                },
            )

        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200

        result = dynamodb.query(
            TableName=table,
            KeyConditionExpression="userId = :uid",
            ExpressionAttributeValues={":uid": {"S": IDENTITY_ID}},
        )
        assert result["Count"] == 0
