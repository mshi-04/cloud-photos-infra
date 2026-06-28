import json
import os
from unittest.mock import MagicMock

import pytest

import delete_user
from delete_user import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"


def _make_event(identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
    }


class TestDeleteUser:
    def test_returns_401_when_no_identity_id(self, aws_resources):
        event = {"requestContext": {"identity": {}}}
        resp = handler(event, None)
        assert resp["statusCode"] == 401

    def test_unauthorized_does_not_touch_storage(self, monkeypatch):
        s3_mock = MagicMock()
        ddb_mock = MagicMock()
        monkeypatch.setattr(delete_user, "_delete_s3_objects", s3_mock)
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", ddb_mock)

        resp = handler({"requestContext": {"identity": {}}}, None)

        assert resp["statusCode"] == 401
        assert json.loads(resp["body"])["message"] == "Unauthorized"
        assert s3_mock.call_count == 0
        assert ddb_mock.call_count == 0

    def test_returns_200_with_message_when_all_succeed(self, aws_resources, monkeypatch):
        monkeypatch.setattr(delete_user, "_delete_s3_objects", MagicMock())
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", MagicMock())

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 200
        assert json.loads(resp["body"]) == {"message": "User data deleted"}

    def test_returns_500_when_only_s3_fails(self, aws_resources, monkeypatch):
        monkeypatch.setattr(delete_user, "_delete_s3_objects", MagicMock(side_effect=RuntimeError("boom")))
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", MagicMock())

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        assert "S3" in json.loads(resp["body"])["message"]

    def test_returns_500_when_only_upload_records_fail(self, aws_resources, monkeypatch):
        upload_table = os.environ["UPLOAD_RECORDS_TABLE_NAME"]

        def fail_upload(table_name, identity_id, sort_key_name):
            if table_name == upload_table:
                raise RuntimeError("boom")

        monkeypatch.setattr(delete_user, "_delete_s3_objects", MagicMock())
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", MagicMock(side_effect=fail_upload))

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        assert "DynamoDB/upload_records" in json.loads(resp["body"])["message"]

    def test_returns_500_when_only_device_tokens_fail(self, aws_resources, monkeypatch):
        device_table = os.environ["DEVICE_TOKENS_TABLE_NAME"]

        def fail_device(table_name, identity_id, sort_key_name):
            if table_name == device_table:
                raise RuntimeError("boom")

        monkeypatch.setattr(delete_user, "_delete_s3_objects", MagicMock())
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", MagicMock(side_effect=fail_device))

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        assert "DynamoDB/device_tokens" in json.loads(resp["body"])["message"]

    def test_returns_500_with_all_failed_subsystems(self, aws_resources, monkeypatch):
        monkeypatch.setattr(delete_user, "_delete_s3_objects", MagicMock(side_effect=RuntimeError("boom")))
        monkeypatch.setattr(delete_user, "_delete_dynamodb_records", MagicMock(side_effect=RuntimeError("boom")))

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        message = json.loads(resp["body"])["message"]
        assert "S3" in message
        assert "DynamoDB/upload_records" in message
        assert "DynamoDB/device_tokens" in message

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


def _make_items(count):
    return [{"userId": {"S": IDENTITY_ID}, "mediaId": {"S": f"media-{i:03d}"}} for i in range(count)]


class TestBatchDeleteItems:
    def test_retries_then_succeeds_on_unprocessed_items(self, monkeypatch):
        monkeypatch.setattr(delete_user.time, "sleep", MagicMock())
        dynamodb = MagicMock()
        dynamodb.batch_write_item.side_effect = [
            {"UnprocessedItems": {"tbl": [{"DeleteRequest": {}}]}},
            {"UnprocessedItems": {}},
        ]

        delete_user._batch_delete_items(dynamodb, "tbl", _make_items(1), "mediaId")

        assert dynamodb.batch_write_item.call_count == 2

    def test_raises_after_max_retries_exceeded(self, monkeypatch):
        sleep_mock = MagicMock()
        monkeypatch.setattr(delete_user.time, "sleep", sleep_mock)
        dynamodb = MagicMock()
        dynamodb.batch_write_item.return_value = {"UnprocessedItems": {"tbl": [{"DeleteRequest": {}}]}}

        with pytest.raises(RuntimeError, match="UnprocessedItems"):
            delete_user._batch_delete_items(dynamodb, "tbl", _make_items(1), "mediaId")

        assert dynamodb.batch_write_item.call_count == 6
        assert sleep_mock.call_count == 5

    def test_splits_items_into_chunks_of_25(self):
        dynamodb = MagicMock()
        dynamodb.batch_write_item.return_value = {"UnprocessedItems": {}}

        delete_user._batch_delete_items(dynamodb, "tbl", _make_items(30), "mediaId")

        assert dynamodb.batch_write_item.call_count == 2
        batch_sizes = [len(call.kwargs["RequestItems"]["tbl"]) for call in dynamodb.batch_write_item.call_args_list]
        assert batch_sizes == [25, 5]


class TestFlushS3Batch:
    def test_raises_when_response_has_errors(self):
        s3 = MagicMock()
        s3.delete_objects.return_value = {
            "Errors": [{"Code": "AccessDenied", "Key": "k1"}, {"Code": "InternalError", "Key": "k2"}]
        }

        with pytest.raises(RuntimeError) as exc:
            delete_user._flush_s3_batch(s3, "bucket", [{"Key": "k1", "VersionId": "v1"}])

        assert "2 object(s) failed" in str(exc.value)
        assert "AccessDenied" in str(exc.value)

    def test_no_raise_when_no_errors(self):
        s3 = MagicMock()
        s3.delete_objects.return_value = {}

        delete_user._flush_s3_batch(s3, "bucket", [{"Key": "k1", "VersionId": "v1"}])


class TestDeleteS3Objects:
    def test_flushes_at_1000_for_versions_and_markers_then_remainder(self, aws_resources, monkeypatch):
        fake_s3 = MagicMock()
        fake_s3.delete_objects.return_value = {}
        versions = [{"Key": f"k{i}", "VersionId": f"v{i}"} for i in range(1100)]
        markers = [{"Key": f"dk{i}", "VersionId": f"dv{i}"} for i in range(1000)]
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Versions": versions, "DeleteMarkers": markers}]
        fake_s3.get_paginator.return_value = paginator
        monkeypatch.setattr(delete_user, "_get_s3", lambda: fake_s3)

        delete_user._delete_s3_objects(IDENTITY_ID)

        batches = [call.kwargs["Delete"]["Objects"] for call in fake_s3.delete_objects.call_args_list]
        assert [len(b) for b in batches] == [1000, 1000, 100]


class TestDeleteDynamodbRecords:
    def test_continues_query_with_last_evaluated_key(self, monkeypatch):
        fake = MagicMock()
        fake.query.side_effect = [
            {
                "Items": [{"userId": {"S": IDENTITY_ID}, "mediaId": {"S": "m1"}}],
                "LastEvaluatedKey": {"userId": {"S": IDENTITY_ID}, "mediaId": {"S": "m1"}},
            },
            {"Items": [{"userId": {"S": IDENTITY_ID}, "mediaId": {"S": "m2"}}]},
        ]
        fake.batch_write_item.return_value = {"UnprocessedItems": {}}
        monkeypatch.setattr(delete_user, "_get_dynamodb", lambda: fake)

        delete_user._delete_dynamodb_records("tbl", IDENTITY_ID, "mediaId")

        assert fake.query.call_count == 2
        assert fake.query.call_args_list[1].kwargs["ExclusiveStartKey"] == {
            "userId": {"S": IDENTITY_ID},
            "mediaId": {"S": "m1"},
        }
        assert fake.batch_write_item.call_count == 2
