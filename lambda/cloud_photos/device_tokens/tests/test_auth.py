import pytest

from cloud_photos.device_tokens.auth import get_identity_id, mask_identity


class TestGetIdentityId:
    def test_returns_identity_id(self):
        event = {"requestContext": {"identity": {"cognitoIdentityId": "ap-northeast-1:abc123"}}}
        assert get_identity_id(event) == "ap-northeast-1:abc123"

    def test_returns_none_when_missing(self):
        assert get_identity_id({}) is None

    def test_returns_none_when_no_cognito_identity_id(self):
        event = {"requestContext": {"identity": {}}}
        assert get_identity_id(event) is None


class TestMaskIdentity:
    def test_masks_long_identity(self):
        result = mask_identity("ap-northeast-1:abcdefghij")
        assert result.startswith("ap-n")
        assert result.endswith("ghij")
        assert "***" in result

    def test_masks_short_identity(self):
        assert mask_identity("short") == "***"

    def test_masks_empty_string(self):
        assert mask_identity("") == "***"


UNAUTHENTICATED_EVENTS = [
    pytest.param({"requestContext": None}, id="request_context_null"),
    pytest.param({"requestContext": "not-an-object"}, id="request_context_not_object"),
    pytest.param({"requestContext": {"identity": None}}, id="identity_null"),
    pytest.param({"requestContext": {"identity": []}}, id="identity_not_object"),
    pytest.param({"requestContext": {"identity": {"cognitoIdentityId": None}}}, id="identity_id_null"),
    pytest.param({"requestContext": {"identity": {"cognitoIdentityId": ""}}}, id="identity_id_empty"),
    pytest.param({"requestContext": {"identity": {"cognitoIdentityId": 123}}}, id="identity_id_not_string"),
]


@pytest.mark.parametrize("event", UNAUTHENTICATED_EVENTS)
def test_returns_none_for_missing_or_null_identity(event):
    assert get_identity_id(event) is None
