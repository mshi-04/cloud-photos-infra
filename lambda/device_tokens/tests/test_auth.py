from auth import get_identity_id, mask_identity


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
