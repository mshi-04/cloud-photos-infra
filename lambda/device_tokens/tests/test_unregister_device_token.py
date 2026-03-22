import json
import os

from moto import mock_aws

from unregister_device_token import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
DEVICE_TOKEN = "test-device-token-abc123"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }


def _seed_token(client):
    client.put_item(
        TableName=os.environ["TABLE_NAME"],
        Item={
            "userId": {"S": IDENTITY_ID},
            "deviceToken": {"S": DEVICE_TOKEN},
            "platform": {"S": "ios"},
            "registeredAt": {"N": "1700000000000"},
            "updatedAt": {"N": "1700000000000"},
        },
    )


@mock_aws
class TestUnregisterDeviceToken:
    def test_unregister_success(self, dynamodb_table):
        _seed_token(dynamodb_table)
        resp = handler(_make_event({"deviceToken": DEVICE_TOKEN}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["message"] == "unregistered"

    def test_item_removed_from_table(self, dynamodb_table):
        _seed_token(dynamodb_table)
        handler(_make_event({"deviceToken": DEVICE_TOKEN}), None)
        result = dynamodb_table.get_item(
            TableName=os.environ["TABLE_NAME"],
            Key={"userId": {"S": IDENTITY_ID}, "deviceToken": {"S": DEVICE_TOKEN}},
        )
        assert "Item" not in result

    def test_unregister_nonexistent_returns_200(self, dynamodb_table):
        resp = handler(_make_event({"deviceToken": "nonexistent-token"}), None)
        assert resp["statusCode"] == 200

    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "body": json.dumps({"deviceToken": DEVICE_TOKEN})}
        resp = handler(event, None)
        assert resp["statusCode"] == 403

    def test_missing_device_token(self, dynamodb_table):
        resp = handler(_make_event({}), None)
        assert resp["statusCode"] == 400

    def test_invalid_json_body(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "body": "not-json",
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400
