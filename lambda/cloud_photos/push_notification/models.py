from dataclasses import dataclass
from typing import Final, Self

from cloud_photos.common.errors import ValidationError

SUCCESS_COUNT_INVALID: Final = "successCount must be a non-negative integer"


@dataclass(frozen=True, slots=True)
class SuccessCount:
    """The number of media files the client uploaded successfully."""

    value: int

    def __post_init__(self) -> None:
        # bool is a subclass of int, so reject it explicitly.
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 0:
            raise ValidationError(SUCCESS_COUNT_INVALID)

    @classmethod
    def parse(cls, raw: object) -> Self:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ValidationError(SUCCESS_COUNT_INVALID)
        return cls(raw)

    @property
    def is_zero(self) -> bool:
        return self.value == 0
