import json

import pytest
from moto import mock_aws
from conftest import TABLE_NAME

from delete_upload_record import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
MEDIA_ID = "media-001"


def _make_event(media_id=MEDIA_ID, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "pathParameters": {"mediaId": media_id},
    }


def _seed_record(client, identity_id=IDENTITY_ID, media_id=MEDIA_ID):
    client.put_item(
        TableName=TABLE_NAME,
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
            TableName=TABLE_NAME,
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

    def test_missing_media_id(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "pathParameters": {},
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400
