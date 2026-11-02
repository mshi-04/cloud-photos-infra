import json
import os

import pytest
from moto import mock_aws

from cloud_photos.media_uploads import db
from cloud_photos.media_uploads.get_upload_records import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"


def _make_event(params=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "queryStringParameters": params or {},
    }


def _seed_records(client, identity_id, count):
    for i in range(count):
        client.put_item(
            TableName=os.environ["TABLE_NAME"],
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
        body1 = json.loads(resp1["body"])
        last_key = json.dumps(body1["lastEvaluatedKey"])
        resp2 = handler(_make_event({"limit": "2", "lastEvaluatedKey": last_key}), None)
        assert resp2["statusCode"] == 200
        body2 = json.loads(resp2["body"])
        assert len(body2["records"]) == 2
        ids1 = {r["mediaId"] for r in body1["records"]}
        ids2 = {r["mediaId"] for r in body2["records"]}
        assert ids1.isdisjoint(ids2), "Page 2 must not overlap with page 1"

    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "queryStringParameters": {}}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    @pytest.mark.parametrize("request_context", [None, {"identity": None}], ids=["request_context_null", "identity_null"])
    def test_unauthorized_null_identity(self, dynamodb_table, request_context):
        event = {"requestContext": request_context, "queryStringParameters": {}}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_invalid_limit(self, dynamodb_table):
        resp = handler(_make_event({"limit": "abc"}), None)
        assert resp["statusCode"] == 400

    def test_last_evaluated_key_wrong_user(self, dynamodb_table):
        key = json.dumps({"userId": "other-user", "mediaId": "media-000"})
        resp = handler(_make_event({"lastEvaluatedKey": key}), None)
        assert resp["statusCode"] == 403

    def test_returns_only_callers_records(self, dynamodb_table):
        _seed_records(dynamodb_table, IDENTITY_ID, 2)
        _seed_records(dynamodb_table, "ap-northeast-1:other-user-id", 3)

        resp = handler(_make_event(), None)

        records = json.loads(resp["body"])["records"]
        assert len(records) == 2
        assert {r["userId"] for r in records} == {IDENTITY_ID}

    def test_returns_numbers_as_plain_json(self, dynamodb_table):
        _seed_records(dynamodb_table, IDENTITY_ID, 1)

        resp = handler(_make_event(), None)

        assert json.loads(resp["body"])["records"][0]["uploadedAt"] == 1700000000000

    @pytest.mark.parametrize("params", [None, {}], ids=["params_null", "params_empty"])
    def test_without_query_parameters(self, dynamodb_table, params):
        event = {"requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}}, "queryStringParameters": params}
        resp = handler(event, None)
        assert resp["statusCode"] == 200

    def test_invalid_last_evaluated_key(self, dynamodb_table):
        resp = handler(_make_event({"lastEvaluatedKey": "not-json"}), None)
        assert resp["statusCode"] == 400

    def test_dynamodb_failure_returns_500_without_internal_details(self, dynamodb_table, caplog):
        dynamodb_table.delete_table(TableName=os.environ["TABLE_NAME"])

        resp = handler(_make_event(), None)

        assert resp["statusCode"] == 500
        assert json.loads(resp["body"]) == {"message": "Internal server error"}
        assert "Failed to query upload records" in caplog.text
        assert IDENTITY_ID not in caplog.text

    def test_unexpected_error_is_not_turned_into_500(self, dynamodb_table, monkeypatch):
        # Only AWS call failures become 500. A configuration error propagates as a Lambda error,
        # which API Gateway returns as 502.
        monkeypatch.delenv("TABLE_NAME")
        db.get_table_name.cache_clear()

        with pytest.raises(KeyError, match="TABLE_NAME"):
            handler(_make_event(), None)
