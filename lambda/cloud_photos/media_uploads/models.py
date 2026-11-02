import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from cloud_photos.common.auth import MASK, IdentityId
from cloud_photos.common.errors import AuthorizationError, ValidationError
from cloud_photos.media_uploads.constants import (
    DEFAULT_LIMIT,
    FIELD_CLOUD_STORAGE_PATH,
    FIELD_CONTENT_TYPE,
    FIELD_FILE_SIZE,
    FIELD_MEDIA_ID,
    FIELD_MEDIA_TYPE,
    FIELD_USER_ID,
    MAX_LIMIT,
    MIN_LIMIT,
    PARAM_LAST_EVALUATED_KEY,
    PARAM_LIMIT,
    PRIVATE_PATH_PREFIX,
)


def _non_empty_message(field: str) -> str:
    return f"{field} must be a non-empty string"


def _required_text(raw: object, field: str) -> str:
    """Return the stripped value of a required text field."""
    if raw is None:
        raise ValidationError(f"Missing required field: {field}")
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(_non_empty_message(field))
    return raw.strip()


@dataclass(frozen=True, slots=True)
class MediaId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValidationError(_non_empty_message(FIELD_MEDIA_ID))

    @classmethod
    def parse(cls, raw: object) -> Self:
        return cls(_required_text(raw, FIELD_MEDIA_ID))


@dataclass(frozen=True, slots=True)
class CloudStoragePath:
    """An S3 object key. It contains the owner's Identity ID, so it is masked when converted to text."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValidationError(_non_empty_message(FIELD_CLOUD_STORAGE_PATH))

    @classmethod
    def parse(cls, raw: object) -> Self:
        return cls(_required_text(raw, FIELD_CLOUD_STORAGE_PATH))

    def belongs_to(self, identity_id: IdentityId) -> bool:
        """Return whether the path is under the caller's private prefix."""
        return self.value.startswith(f"{PRIVATE_PATH_PREFIX}{identity_id.value}/")

    def __str__(self) -> str:
        return MASK

    def __repr__(self) -> str:
        return f"CloudStoragePath({MASK})"


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"

    @classmethod
    def parse(cls, raw: object) -> Self:
        if raw is None:
            raise ValidationError(f"Missing required field: {FIELD_MEDIA_TYPE}")
        if not isinstance(raw, str):
            raise ValidationError(_media_type_message())
        try:
            return cls(raw.strip())
        except ValueError:
            raise ValidationError(_media_type_message()) from None


def _media_type_message() -> str:
    return f"{FIELD_MEDIA_TYPE} must be {' or '.join(MediaType)}"


@dataclass(frozen=True, slots=True)
class FileSize:
    """The size of the uploaded file in bytes."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError(f"{FIELD_FILE_SIZE} must be an integer")
        if self.value < 0:
            raise ValidationError(f"{FIELD_FILE_SIZE} must be non-negative")

    @classmethod
    def parse(cls, raw: object) -> Self:
        # JSON has a single number type, so a whole float such as 100.0 is accepted.
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            raise ValidationError(f"{FIELD_FILE_SIZE} must be a number")
        if isinstance(raw, float) and not raw.is_integer():
            raise ValidationError(f"{FIELD_FILE_SIZE} must be an integer")
        return cls(int(raw))


@dataclass(frozen=True, slots=True)
class PageLimit:
    """The number of records to return in one page."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError("Invalid limit parameter")
        if not MIN_LIMIT <= self.value <= MAX_LIMIT:
            raise ValidationError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}")

    @classmethod
    def parse(cls, raw: object) -> Self:
        """Parse the limit parameter and clamp it to the allowed range."""
        if isinstance(raw, bool) or not isinstance(raw, str | int | float):
            raise ValidationError("Invalid limit parameter")
        try:
            limit = int(raw)
        except (ValueError, OverflowError):
            raise ValidationError("Invalid limit parameter") from None
        return cls(max(MIN_LIMIT, min(limit, MAX_LIMIT)))


@dataclass(frozen=True, slots=True)
class PageCursor:
    """The position to continue a query from. It always belongs to the caller."""

    identity_id: IdentityId
    media_id: MediaId

    @classmethod
    def parse(cls, raw: object, identity_id: IdentityId) -> Self:
        """Parse a lastEvaluatedKey returned earlier, rejecting one that belongs to another user."""
        if not isinstance(raw, str | bytes | bytearray):
            raise ValidationError(f"Invalid {PARAM_LAST_EVALUATED_KEY} parameter")
        try:
            key = json.loads(raw)
        except json.JSONDecodeError:
            raise ValidationError(f"Invalid {PARAM_LAST_EVALUATED_KEY} parameter") from None

        if not isinstance(key, dict):
            raise ValidationError(f"{PARAM_LAST_EVALUATED_KEY} must be an object")
        if key.get(FIELD_USER_ID) != identity_id.value:
            raise AuthorizationError(f"{PARAM_LAST_EVALUATED_KEY} does not match your identity")

        media_id = key.get(FIELD_MEDIA_ID)
        if not isinstance(media_id, str) or not media_id.strip():
            raise ValidationError(_non_empty_message(f"{PARAM_LAST_EVALUATED_KEY}.{FIELD_MEDIA_ID}"))
        return cls(identity_id=identity_id, media_id=MediaId(media_id.strip()))


@dataclass(frozen=True, slots=True)
class CreateUploadRecordRequest:
    media_id: MediaId
    cloud_storage_path: CloudStoragePath
    content_type: str
    media_type: MediaType
    file_size: FileSize | None = None

    @classmethod
    def parse(cls, body: object) -> Self:
        if not isinstance(body, Mapping):
            raise ValidationError("Request body must be an object")

        raw_file_size = body.get(FIELD_FILE_SIZE)
        return cls(
            media_id=MediaId.parse(body.get(FIELD_MEDIA_ID)),
            cloud_storage_path=CloudStoragePath.parse(body.get(FIELD_CLOUD_STORAGE_PATH)),
            content_type=_required_text(body.get(FIELD_CONTENT_TYPE), FIELD_CONTENT_TYPE),
            media_type=MediaType.parse(body.get(FIELD_MEDIA_TYPE)),
            file_size=None if raw_file_size is None else FileSize.parse(raw_file_size),
        )


@dataclass(frozen=True, slots=True)
class GetUploadRecordsRequest:
    limit: PageLimit
    cursor: PageCursor | None = None

    @classmethod
    def parse(cls, params: object, identity_id: IdentityId) -> Self:
        if params is None:
            params = {}
        if not isinstance(params, Mapping):
            raise ValidationError("params must be a dict")

        limit = PageLimit.parse(params.get(PARAM_LIMIT, DEFAULT_LIMIT))
        raw_cursor = params.get(PARAM_LAST_EVALUATED_KEY)
        # A missing or empty lastEvaluatedKey means the first page.
        cursor = PageCursor.parse(raw_cursor, identity_id) if raw_cursor else None
        return cls(limit=limit, cursor=cursor)
