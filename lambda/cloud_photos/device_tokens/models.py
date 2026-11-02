from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from cloud_photos.common.device_token import DeviceToken
from cloud_photos.common.errors import ValidationError
from cloud_photos.device_tokens.constants import FIELD_DEVICE_TOKEN, FIELD_PLATFORM


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
