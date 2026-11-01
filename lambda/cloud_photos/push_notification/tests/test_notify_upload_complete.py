import json
from unittest.mock import patch

import pytest

from cloud_photos.push_notification import notify_upload_complete
from cloud_photos.push_notification.notify_upload_complete import handler

IDENTITY_ID = "ap-northeast-1:test-user-id"
TOKEN_A = "device-token-aaa"
TOKEN_B = "device-token-bbb"

TABLE_NAME = "test-device-tokens"
KEY_USER_ID = "userId"
KEY_DEVICE_TOKEN = "deviceToken"


def _make_event(body=None, identity_id=IDENTITY_ID):
    return {
        "requestContext": {"identity": {"cognitoIdentityId": identity_id}},
        "body": json.dumps(body) if body is not None else None,
    }


def _seed_token(client, user_id, token):
    client.put_item(
        TableName=TABLE_NAME,
        Item={
            KEY_USER_ID: {"S": user_id},
            KEY_DEVICE_TOKEN: {"S": token},
        },
    )


class TestNotifyUploadComplete:
    def test_unauthorized(self, dynamodb_table):
        event = {"requestContext": {"identity": {}}, "body": json.dumps({"successCount": 1})}
        resp = handler(event, None)
        assert resp["statusCode"] == 401

    def test_invalid_json_body(self, dynamodb_table):
        event = {
            "requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}},
            "body": "not-json",
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_missing_success_count(self, dynamodb_table):
        resp = handler(_make_event({}), None)
        assert resp["statusCode"] == 400

    def test_success_count_string_is_invalid(self, dynamodb_table):
        resp = handler(_make_event({"successCount": "five"}), None)
        assert resp["statusCode"] == 400

    def test_negative_success_count_is_invalid(self, dynamodb_table):
        resp = handler(_make_event({"successCount": -1}), None)
        assert resp["statusCode"] == 400

    def test_zero_success_count_returns_204_without_sending(self, dynamodb_table):
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        with patch("firebase_admin.messaging.send") as mock_send:
            resp = handler(_make_event({"successCount": 0}), None)
        assert resp["statusCode"] == 204
        assert resp["body"] == ""
        mock_send.assert_not_called()

    @pytest.mark.parametrize("raw_body", ["[1, 2]", '"text"', "3", "null"])
    def test_non_object_json_body_is_invalid(self, dynamodb_table, raw_body):
        event = {"requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}}, "body": raw_body}
        with patch("firebase_admin.messaging.send") as mock_send:
            resp = handler(event, None)
        assert resp["statusCode"] == 400
        mock_send.assert_not_called()

    @pytest.mark.parametrize("success_count", [True, False, 1.5, 2.0, None])
    def test_non_integer_success_count_is_invalid(self, dynamodb_table, success_count):
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        with patch("firebase_admin.messaging.send") as mock_send:
            resp = handler(_make_event({"successCount": success_count}), None)
        assert resp["statusCode"] == 400
        mock_send.assert_not_called()

    def test_no_device_tokens_returns_204(self, dynamodb_table):
        resp = handler(_make_event({"successCount": 3}), None)
        assert resp["statusCode"] == 204

    def test_sends_notification_and_returns_sent_count(self, dynamodb_table):
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        with patch("firebase_admin.messaging.send") as mock_send:
            resp = handler(_make_event({"successCount": 2}), None)
        assert resp["statusCode"] == 201
        assert json.loads(resp["body"])["sentCount"] == 1
        mock_send.assert_called_once()

    def test_sends_to_all_registered_tokens(self, dynamodb_table):
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_B)
        with patch("firebase_admin.messaging.send") as mock_send:
            resp = handler(_make_event({"successCount": 5}), None)
        assert resp["statusCode"] == 201
        assert json.loads(resp["body"])["sentCount"] == 2
        assert mock_send.call_count == 2

    def test_unregistered_token_is_deleted(self, dynamodb_table):
        from firebase_admin import messaging

        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        with patch("firebase_admin.messaging.send", side_effect=messaging.UnregisteredError("stale")):
            resp = handler(_make_event({"successCount": 1}), None)

        assert resp["statusCode"] == 201
        assert json.loads(resp["body"])["sentCount"] == 0

        result = dynamodb_table.query(
            TableName=TABLE_NAME,
            KeyConditionExpression="#uid = :uid",
            ExpressionAttributeNames={"#uid": KEY_USER_ID},
            ExpressionAttributeValues={":uid": {"S": IDENTITY_ID}},
        )
        assert len(result["Items"]) == 0

    def test_send_error_does_not_delete_token(self, dynamodb_table):
        _seed_token(dynamodb_table, IDENTITY_ID, TOKEN_A)
        with patch("firebase_admin.messaging.send", side_effect=Exception("network error")):
            resp = handler(_make_event({"successCount": 1}), None)

        assert resp["statusCode"] == 201
        assert json.loads(resp["body"])["sentCount"] == 0

        result = dynamodb_table.query(
            TableName=TABLE_NAME,
            KeyConditionExpression="#uid = :uid",
            ExpressionAttributeNames={"#uid": KEY_USER_ID},
            ExpressionAttributeValues={":uid": {"S": IDENTITY_ID}},
        )
        assert len(result["Items"]) == 1


class _PagedDynamoDB:
    """Returns the given Query pages in order and records the requests."""

    def __init__(self, pages):
        self._pages = list(pages)
        self.requests = []

    def query(self, **params):
        self.requests.append(params)
        return self._pages.pop(0)


class TestQueryDeviceTokens:
    def test_follows_last_evaluated_key_across_pages(self):
        key_1 = {KEY_USER_ID: {"S": IDENTITY_ID}, KEY_DEVICE_TOKEN: {"S": TOKEN_A}}
        key_2 = {KEY_USER_ID: {"S": IDENTITY_ID}, KEY_DEVICE_TOKEN: {"S": "device-token-zzz"}}
        dynamodb = _PagedDynamoDB(
            [
                {"Items": [{KEY_DEVICE_TOKEN: {"S": TOKEN_A}}], "LastEvaluatedKey": key_1},
                {"Items": [], "LastEvaluatedKey": key_2},
                {"Items": [{KEY_DEVICE_TOKEN: {"S": TOKEN_B}}]},
            ]
        )

        tokens = notify_upload_complete._query_device_tokens(dynamodb, TABLE_NAME, IDENTITY_ID)

        assert tokens == [TOKEN_A, TOKEN_B]
        assert [request.get("ExclusiveStartKey") for request in dynamodb.requests] == [None, key_1, key_2]
        for request in dynamodb.requests:
            assert request["ExpressionAttributeValues"] == {":uid": {"S": IDENTITY_ID}}
            assert request["KeyConditionExpression"] == "#uid = :uid"
