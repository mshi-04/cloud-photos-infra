import json
import os

import pytest
from moto import mock_aws

from cloud_photos.media_uploads import db
from cloud_photos.media_uploads.create_upload_record import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
MEDIA_ID = "media-001"
CLOUD_STORAGE_PATH = f"private/{IDENTITY_ID}/{MEDIA_ID}.jpg"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }


def _valid_body(**kwargs):
    data = {
        "mediaId": MEDIA_ID,
        "cloudStoragePath": CLOUD_STORAGE_PATH,
        "contentType": "image/jpeg",
        "mediaType": "IMAGE",
    }
    data.update(kwargs)
    return data


@mock_aws
class TestCreateUploadRecord:
    def test_create_success(self, dynamodb_table):
        event = _make_event(_valid_body())
        resp = handler(event, None)
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["message"] == "created"
        assert "uploadedAt" in body

    def test_duplicate_skipped(self, dynamodb_table):
        event = _make_event(_valid_body())
        handler(event, None)
        resp = handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "skipped" in body["message"]

    def test_unauthorized_no_identity(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "body": json.dumps(_valid_body())}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    @pytest.mark.parametrize("request_context", [None, {"identity": None}], ids=["request_context_null", "identity_null"])
    def test_unauthorized_null_identity(self, dynamodb_table, request_context):
        event = {"requestContext": request_context, "body": json.dumps(_valid_body())}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_idor_prevention(self, dynamodb_table):
        body = _valid_body(cloudStoragePath="private/other-user/evil.jpg")
        resp = handler(_make_event(body), None)
        assert resp["statusCode"] == 403

    def test_invalid_json_body(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "body": "not-json",
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_missing_media_id(self, dynamodb_table):
        body = _valid_body()
        del body["mediaId"]
        resp = handler(_make_event(body), None)
        assert resp["statusCode"] == 400

    def test_invalid_media_type(self, dynamodb_table):
        resp = handler(_make_event(_valid_body(mediaType="GIF")), None)
        assert resp["statusCode"] == 400

    @pytest.mark.parametrize("file_size", [10**40, 1e300])
    def test_file_size_out_of_dynamodb_range_is_rejected(self, dynamodb_table, file_size):
        resp = handler(_make_event(_valid_body(fileSize=file_size)), None)
        assert resp["statusCode"] == 400

    def test_with_file_size(self, dynamodb_table):
        resp = handler(_make_event(_valid_body(fileSize=512000)), None)
        assert resp["statusCode"] == 201

    def test_saves_record(self, dynamodb_table):
        resp = handler(_make_event(_valid_body(fileSize=512000)), None)
        item = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "mediaId": {"S": MEDIA_ID}},
        )["Item"]
        assert item == {
            "userId": {"S": IDENTITY_ID},
            "mediaId": {"S": MEDIA_ID},
            "cloudStoragePath": {"S": CLOUD_STORAGE_PATH},
            "contentType": {"S": "image/jpeg"},
            "mediaType": {"S": "IMAGE"},
            "fileSize": {"N": "512000"},
            "uploadedAt": {"N": str(json.loads(resp["body"])["uploadedAt"])},
        }

    def test_dynamodb_failure_returns_500_without_internal_details(self, dynamodb_table, caplog):
        dynamodb_table.delete_table(TableName=os.environ["TABLE_NAME"])

        resp = handler(_make_event(_valid_body()), None)

        assert resp["statusCode"] == 500
        assert json.loads(resp["body"]) == {"message": "Internal server error"}
        assert "Failed to create upload record" in caplog.text
        assert IDENTITY_ID not in caplog.text

    def test_unexpected_error_is_not_turned_into_500(self, dynamodb_table, monkeypatch):
        # Only AWS call failures become 500. A configuration error propagates as a Lambda error,
        # which API Gateway returns as 502.
        monkeypatch.delenv("TABLE_NAME")
        db.get_table_name.cache_clear()

        with pytest.raises(KeyError, match="TABLE_NAME"):
            handler(_make_event(_valid_body()), None)
