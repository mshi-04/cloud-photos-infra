import pytest

from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.errors import ValidationError

DEVICE_TOKEN = "test-device-token-abc123"


class TestDeviceToken:
    def test_parse_returns_token(self):
        assert DeviceToken.parse(DEVICE_TOKEN).value == DEVICE_TOKEN

    @pytest.mark.parametrize("raw", [None, 123, ["token"], ""])
    def test_parse_rejects_non_string_or_empty(self, raw):
        with pytest.raises(ValidationError, match=r"^deviceToken is required$"):
            DeviceToken.parse(raw)

    def test_direct_construction_is_validated(self):
        with pytest.raises(ValidationError, match=r"^deviceToken is required$"):
            DeviceToken("")

    def test_text_shows_only_last_4_characters(self):
        token = DeviceToken(DEVICE_TOKEN)
        assert str(token) == "***c123"
        assert repr(token) == "DeviceToken(***c123)"
        assert DEVICE_TOKEN not in f"{token} {token!r}"

    @pytest.mark.parametrize("value", ["short", "12345678"])
    def test_short_token_is_masked_entirely(self, value):
        assert str(DeviceToken(value)) == "***"
        assert repr(DeviceToken(value)) == "DeviceToken(***)"
