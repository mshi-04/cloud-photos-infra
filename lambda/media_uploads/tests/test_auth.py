from auth import get_identity_id, mask_identity


class TestGetIdentityId:
    def test_returns_identity_id(self):
        event = {"requestContext": {"identity": {"cognitoIdentityId": "ap-northeast-1:abc123"}}}
        assert get_identity_id(event) == "ap-northeast-1:abc123"

    def test_returns_none_when_missing(self):
        assert get_identity_id({}) is None

    def test_returns_none_when_no_request_context(self):
        assert get_identity_id({"body": "{}"}) is None

    def test_returns_none_when_no_identity(self):
        event = {"requestContext": {}}
        assert get_identity_id(event) is None

    def test_returns_none_when_no_cognito_identity_id(self):
        event = {"requestContext": {"identity": {}}}
        assert get_identity_id(event) is None


class TestMaskIdentity:
    def test_masks_long_identity(self):
        result = mask_identity("ap-northeast-1:abcdefghij")
        assert result == "ap-n***ghij"

    def test_masks_short_identity(self):
        assert mask_identity("short") == "***"

    def test_masks_exactly_8_chars(self):
        assert mask_identity("12345678") == "***"

    def test_masks_empty_string(self):
        assert mask_identity("") == "***"

    def test_shows_first_4_and_last_4(self):
        result = mask_identity("ABCDEFGHIJKLMNOP")
        assert result.startswith("ABCD")
        assert result.endswith("MNOP")
        assert "***" in result
