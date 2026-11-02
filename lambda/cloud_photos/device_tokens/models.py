from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, Self

from cloud_photos.common.auth import FULLY_MASKED_MAX_LENGTH, MASK
from cloud_photos.common.errors import ValidationError
from cloud_photos.device_tokens.constants import FIELD_DEVICE_TOKEN, FIELD_PLATFORM

DEVICE_TOKEN_REQUIRED: Final = "deviceToken is required"


class Platform(StrEnum):
    ANDROID = "android"
    IOS = "ios"

    @classmethod
    def parse(cls, raw: object) -> Self:
        if not isinstance(raw, str):
            raise ValidationError(_platform_message())
        try:
            return cls(raw)
        except ValueError:
            raise ValidationError(_platform_message()) from None


def _platform_message() -> str:
    return f"platform must be one of: {', '.join(Platform)}"


@dataclass(frozen=True, slots=True)
class DeviceToken:
    """An FCM device token. It masks itself when converted to text, so it is safe to log."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValidationError(DEVICE_TOKEN_REQUIRED)

    @classmethod
    def parse(cls, raw: object) -> Self:
        if not isinstance(raw, str):
            raise ValidationError(DEVICE_TOKEN_REQUIRED)
        return cls(raw)

    def __str__(self) -> str:
        if len(self.value) <= FULLY_MASKED_MAX_LENGTH:
            return MASK
        return f"{MASK}{self.value[-4:]}"

    def __repr__(self) -> str:
        return f"DeviceToken({self})"


@dataclass(frozen=True, slots=True)
class RegisterDeviceTokenRequest:
    device_token: DeviceToken
    platform: Platform

    @classmethod
    def parse(cls, body: Mapping[str, Any]) -> Self:
        device_token = DeviceToken.parse(body.get(FIELD_DEVICE_TOKEN))
        return cls(device_token=device_token, platform=Platform.parse(body.get(FIELD_PLATFORM)))


@dataclass(frozen=True, slots=True)
class UnregisterDeviceTokenRequest:
    device_token: DeviceToken

    @classmethod
    def parse(cls, body: Mapping[str, Any]) -> Self:
        return cls(device_token=DeviceToken.parse(body.get(FIELD_DEVICE_TOKEN)))
