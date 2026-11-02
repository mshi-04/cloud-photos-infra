from dataclasses import dataclass
from typing import Final, Self

from cloud_photos.common.auth import FULLY_MASKED_MAX_LENGTH, MASK
from cloud_photos.common.errors import ValidationError

DEVICE_TOKEN_REQUIRED: Final = "deviceToken is required"


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
