import json
import os

import pytest
from moto import mock_aws

from cloud_photos.device_tokens import db
from cloud_photos.device_tokens.register_device_token import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
DEVICE_TOKEN = "test-device-token-abc123"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }


@mock_aws
class TestRegisterDeviceToken:
    def test_register_success_ios(self, dynamodb_table):
        resp = handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "ios"}), None)
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["message"] == "registered"

    def test_register_success_android(self, dynamodb_table):
        resp = handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "android"}), None)
        assert resp["statusCode"] == 201

    def test_upsert_preserves_registered_at(self, dynamodb_table):
        handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "ios"}), None)
        item1 = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "deviceToken": {"S": DEVICE_TOKEN}},
        )["Item"]
        registered_at1 = item1["registeredAt"]["N"]

        handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "android"}), None)
        item2 = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "deviceToken": {"S": DEVICE_TOKEN}},
        )["Item"]
        assert item2["registeredAt"]["N"] == registered_at1
        assert item2["platform"]["S"] == "android"

    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "body": json.dumps({"deviceToken": DEVICE_TOKEN, "platform": "ios"})}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    @pytest.mark.parametrize("request_context", [None, {"identity": None}], ids=["request_context_null", "identity_null"])
    def test_unauthorized_null_identity(self, dynamodb_table, request_context):
        event = {"requestContext": request_context, "body": json.dumps({"deviceToken": DEVICE_TOKEN, "platform": "ios"})}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_missing_device_token(self, dynamodb_table):
        resp = handler(_make_event({"platform": "ios"}), None)
        assert resp["statusCode"] == 400

    def test_invalid_platform(self, dynamodb_table):
        resp = handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "windows"}), None)
        assert resp["statusCode"] == 400

    def test_invalid_json_body(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "body": "not-json",
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_dynamodb_failure_returns_500_without_internal_details(self, dynamodb_table, caplog):
        dynamodb_table.delete_table(TableName=os.environ["TABLE_NAME"])

        resp = handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "ios"}), None)

        assert resp["statusCode"] == 500
        assert json.loads(resp["body"]) == {"message": "Internal server error"}
        assert "Failed to register device token" in caplog.text
        assert IDENTITY_ID not in caplog.text
        assert DEVICE_TOKEN not in caplog.text

    def test_unexpected_error_is_not_turned_into_500(self, dynamodb_table, monkeypatch):
        # Only AWS call failures become 500. A configuration error propagates as a Lambda error,
        # which API Gateway returns as 502.
        monkeypatch.delenv("TABLE_NAME")
        db.get_table_name.cache_clear()

        with pytest.raises(KeyError, match="TABLE_NAME"):
            handler(_make_event({"deviceToken": DEVICE_TOKEN, "platform": "ios"}), None)
