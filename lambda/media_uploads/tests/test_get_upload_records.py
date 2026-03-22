import json

import boto3
import pytest
from moto import mock_aws
from conftest import TABLE_NAME, REGION

from get_upload_records import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"


def _make_event(params=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "queryStringParameters": params or {},
    }


def _seed_records(client, identity_id, count):
    for i in range(count):
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "userId": {"S": identity_id},
                "mediaId": {"S": f"media-{i:03d}"},
                "cloudStoragePath": {"S": f"private/{identity_id}/media-{i:03d}.jpg"},
                "contentType": {"S": "image/jpeg"},
                "mediaType": {"S": "IMAGE"},
                "uploadedAt": {"N": str(1700000000000 + i)},
            },
        )


@mock_aws
class TestGetUploadRecords:
    def test_returns_empty_list(self, dynamodb_table):
        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["records"] == []
        assert "lastEvaluatedKey" not in body

    def test_returns_records(self, dynamodb_table):
        _seed_records(dynamodb_table, IDENTITY_ID, 3)
        resp = handler(_make_event(), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["records"]) == 3

    def test_pagination_with_limit(self, dynamodb_table):
        _seed_records(dynamodb_table, IDENTITY_ID, 5)
        resp = handler(_make_event({"limit": "2"}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert len(body["records"]) == 2
        assert "lastEvaluatedKey" in body

    def test_pagination_next_page(self, dynamodb_table):
        _seed_records(dynamodb_table, IDENTITY_ID, 5)
        resp1 = handler(_make_event({"limit": "2"}), None)
        last_key = json.dumps(json.loads(resp1["body"])["lastEvaluatedKey"])
        resp2 = handler(_make_event({"limit": "2", "lastEvaluatedKey": last_key}), None)
        assert resp2["statusCode"] == 200
        body2 = json.loads(resp2["body"])
        assert len(body2["records"]) == 2

    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "queryStringParameters": {}}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_invalid_limit(self, dynamodb_table):
        resp = handler(_make_event({"limit": "abc"}), None)
        assert resp["statusCode"] == 400

    def test_last_evaluated_key_wrong_user(self, dynamodb_table):
        key = json.dumps({"userId": "other-user", "mediaId": "media-000"})
        resp = handler(_make_event({"lastEvaluatedKey": key}), None)
        assert resp["statusCode"] == 403
