import json
import os

import pytest
from moto import mock_aws

from cloud_photos.media_uploads import db
from cloud_photos.media_uploads.delete_upload_record import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
MEDIA_ID = "media-001"


def _make_event(media_id=MEDIA_ID, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "pathParameters": {"mediaId": media_id},
    }


def _seed_record(client, identity_id=IDENTITY_ID, media_id=MEDIA_ID):
    client.put_item(
        TableName=os.environ["TABLE_NAME"],
        Item={
            "userId": {"S": identity_id},
            "mediaId": {"S": media_id},
            "cloudStoragePath": {"S": f"private/{identity_id}/{media_id}.jpg"},
            "contentType": {"S": "image/jpeg"},
            "mediaType": {"S": "IMAGE"},
            "uploadedAt": {"N": "1700000000000"},
        },
    )


@mock_aws
class TestDeleteUploadRecord:
    def test_logical_delete_success(self, dynamodb_table):
        _seed_record(dynamodb_table)
        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "logically deleted" in body["message"]

    def test_sets_is_deleted_flag(self, dynamodb_table):
        _seed_record(dynamodb_table)
        handler(_make_event(), None)
        item = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "mediaId": {"S": MEDIA_ID}},
        )["Item"]
        assert item["isDeleted"] == {"BOOL": True}

    def test_record_not_found(self, dynamodb_table):
        resp = handler(_make_event(media_id="nonexistent"), None)
        assert resp["statusCode"] == 404

    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "pathParameters": {"mediaId": MEDIA_ID}}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    @pytest.mark.parametrize("request_context", [None, {"identity": None}], ids=["request_context_null", "identity_null"])
    def test_unauthorized_null_identity(self, dynamodb_table, request_context):
        event = {"requestContext": request_context, "pathParameters": {"mediaId": MEDIA_ID}}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_missing_media_id(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "pathParameters": {},
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    @pytest.mark.parametrize("path_parameters", [None, {"mediaId": ""}], ids=["path_parameters_null", "media_id_empty"])
    def test_missing_or_empty_media_id(self, dynamodb_table, path_parameters):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "pathParameters": path_parameters,
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    @pytest.mark.parametrize(
        "path_parameters",
        [None, "media-001", {}, {"mediaId": None}, {"mediaId": ""}, {"mediaId": 123}],
        ids=["null", "not_object", "no_media_id", "media_id_null", "media_id_empty", "media_id_not_string"],
    )
    def test_invalid_path_parameters_return_missing_media_id(self, dynamodb_table, path_parameters):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "pathParameters": path_parameters,
        }

        resp = handler(event, None)

        assert resp["statusCode"] == 400
        assert json.loads(resp["body"]) == {"message": "Missing mediaId"}

    @pytest.mark.parametrize("media_id", ["   ", f" {MEDIA_ID} "], ids=["whitespace_only", "surrounding_whitespace"])
    def test_media_id_with_whitespace_does_not_match_the_stripped_record(self, dynamodb_table, media_id):
        _seed_record(dynamodb_table)

        resp = handler(_make_event(media_id=media_id), None)

        assert resp["statusCode"] == 404
        item = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "mediaId": {"S": MEDIA_ID}},
        )["Item"]
        assert "isDeleted" not in item

    def test_other_users_record_is_not_deleted(self, dynamodb_table):
        _seed_record(dynamodb_table, identity_id="ap-northeast-1:other-user-id")

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 404
        item = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": "ap-northeast-1:other-user-id"}, "mediaId": {"S": MEDIA_ID}},
        )["Item"]
        assert "isDeleted" not in item

    def test_dynamodb_failure_returns_500_without_internal_details(self, dynamodb_table, caplog):
        dynamodb_table.delete_table(TableName=os.environ["TABLE_NAME"])

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        assert json.loads(resp["body"]) == {"message": "Internal server error"}
        assert "Failed to logically delete item" in caplog.text
        assert IDENTITY_ID not in caplog.text

    def test_unexpected_error_is_not_turned_into_500(self, dynamodb_table, monkeypatch):
        # Only AWS call failures become 500. A configuration error propagates as a Lambda error,
        # which API Gateway returns as 502.
        monkeypatch.delenv("TABLE_NAME")
        db.get_table_name.cache_clear()

        with pytest.raises(KeyError, match="TABLE_NAME"):
            handler(_make_event(), None)
