import pytest

from cloud_photos.common.errors import ValidationError
from cloud_photos.users.auth import IdentityId

IDENTITY_ID = "ap-northeast-1:abcdefghij"


class TestIdentityIdFromEvent:
    def test_returns_identity_id(self):
        event = {"requestContext": {"identity": {"cognitoIdentityId": IDENTITY_ID}}}
        assert IdentityId.from_event(event) == IdentityId(IDENTITY_ID)

    @pytest.mark.parametrize(
        "event",
        [
            pytest.param({}, id="missing"),
            pytest.param({"requestContext": {"identity": {}}}, id="identity_id_missing"),
            pytest.param({"requestContext": None}, id="request_context_null"),
            pytest.param({"requestContext": "not-an-object"}, id="request_context_not_object"),
            pytest.param({"requestContext": {"identity": None}}, id="identity_null"),
            pytest.param({"requestContext": {"identity": []}}, id="identity_not_object"),
            pytest.param({"requestContext": {"identity": {"cognitoIdentityId": None}}}, id="identity_id_null"),
            pytest.param({"requestContext": {"identity": {"cognitoIdentityId": ""}}}, id="identity_id_empty"),
            pytest.param({"requestContext": {"identity": {"cognitoIdentityId": 123}}}, id="identity_id_not_string"),
        ],
    )
    def test_returns_none_for_missing_or_null_identity(self, event):
        assert IdentityId.from_event(event) is None


class TestIdentityId:
    @pytest.mark.parametrize("value", ["", None, 123])
    def test_rejects_invalid_value(self, value):
        with pytest.raises(ValidationError):
            IdentityId(value)

    def test_masks_long_identity_in_text(self):
        identity_id = IdentityId(IDENTITY_ID)
        assert str(identity_id) == "ap-n***ghij"
        assert repr(identity_id) == "IdentityId(ap-n***ghij)"

    @pytest.mark.parametrize("value", ["short", "12345678"])
    def test_masks_short_identity_entirely(self, value):
        assert str(IdentityId(value)) == "***"
        assert value not in repr(IdentityId(value))
