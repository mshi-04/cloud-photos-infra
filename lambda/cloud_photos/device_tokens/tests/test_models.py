import pytest

from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.errors import ValidationError
from cloud_photos.device_tokens.models import Platform, RegisterDeviceTokenRequest, UnregisterDeviceTokenRequest

DEVICE_TOKEN = "test-device-token-abc123"


class TestPlatform:
    @pytest.mark.parametrize(("raw", "expected"), [("ios", Platform.IOS), ("android", Platform.ANDROID)])
    def test_parse_accepts_known_platforms(self, raw, expected):
        assert Platform.parse(raw) is expected

    @pytest.mark.parametrize("raw", [None, "web", "IOS", 1, ["ios"]])
    def test_parse_rejects_unknown_platforms(self, raw):
        with pytest.raises(ValidationError, match=r"^platform must be one of: android, ios$"):
            Platform.parse(raw)


class TestRegisterDeviceTokenRequest:
    def test_parse(self):
        request = RegisterDeviceTokenRequest.parse({"deviceToken": DEVICE_TOKEN, "platform": "ios"})
        assert request == RegisterDeviceTokenRequest(DeviceToken(DEVICE_TOKEN), Platform.IOS)

    def test_device_token_is_checked_before_platform(self):
        with pytest.raises(ValidationError, match=r"^deviceToken is required$"):
            RegisterDeviceTokenRequest.parse({"platform": "web"})

    def test_rejects_unknown_platform(self):
        with pytest.raises(ValidationError, match=r"^platform must be one of"):
            RegisterDeviceTokenRequest.parse({"deviceToken": DEVICE_TOKEN, "platform": "web"})


class TestUnregisterDeviceTokenRequest:
    def test_parse(self):
        assert UnregisterDeviceTokenRequest.parse({"deviceToken": DEVICE_TOKEN}).device_token == DeviceToken(DEVICE_TOKEN)

    def test_rejects_missing_token(self):
        with pytest.raises(ValidationError, match=r"^deviceToken is required$"):
            UnregisterDeviceTokenRequest.parse({})
