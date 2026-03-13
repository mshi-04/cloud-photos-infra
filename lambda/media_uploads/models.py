import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from constants import (
    DEFAULT_LIMIT,
    FIELD_CLOUD_STORAGE_PATH,
    FIELD_CONTENT_TYPE,
    FIELD_FILE_SIZE,
    FIELD_MEDIA_ID,
    FIELD_MEDIA_TYPE,
    FIELD_USER_ID,
    MAX_LIMIT,
    VALID_MEDIA_TYPES,
)


class ValidationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


@dataclass
class CreateUploadRecordRequest:
    media_id: str
    cloud_storage_path: str
    content_type: str
    media_type: str
    file_size: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CreateUploadRecordRequest":
        if not isinstance(data, dict):
            raise ValidationError("Request body must be an object")

        media_id = data.get(FIELD_MEDIA_ID)
        cloud_storage_path = data.get(FIELD_CLOUD_STORAGE_PATH)
        content_type = data.get(FIELD_CONTENT_TYPE)
        media_type = data.get(FIELD_MEDIA_TYPE)
        file_size = data.get(FIELD_FILE_SIZE)

        if media_id is None:
            raise ValidationError(f"Missing required field: {FIELD_MEDIA_ID}")
        if not isinstance(media_id, str) or not media_id.strip():
            raise ValidationError(f"{FIELD_MEDIA_ID} must be a non-empty string")

        if cloud_storage_path is None:
            raise ValidationError(f"Missing required field: {FIELD_CLOUD_STORAGE_PATH}")
        if not isinstance(cloud_storage_path, str) or not cloud_storage_path.strip():
            raise ValidationError(f"{FIELD_CLOUD_STORAGE_PATH} must be a non-empty string")

        if content_type is None:
            raise ValidationError(f"Missing required field: {FIELD_CONTENT_TYPE}")
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValidationError(f"{FIELD_CONTENT_TYPE} must be a non-empty string")

        if media_type is None:
            raise ValidationError(f"Missing required field: {FIELD_MEDIA_TYPE}")
        if media_type not in VALID_MEDIA_TYPES:
            raise ValidationError(f"{FIELD_MEDIA_TYPE} must be IMAGE or VIDEO")

        if file_size is not None:
            if isinstance(file_size, bool) or not isinstance(file_size, (int, float)):
                raise ValidationError(f"{FIELD_FILE_SIZE} must be a number")
            if isinstance(file_size, float) and not file_size.is_integer():
                raise ValidationError(f"{FIELD_FILE_SIZE} must be an integer")
            file_size = int(file_size)
            if file_size < 0:
                raise ValidationError(f"{FIELD_FILE_SIZE} must be non-negative")

        return cls(
            media_id=media_id.strip(),
            cloud_storage_path=cloud_storage_path.strip(),
            content_type=content_type.strip(),
            media_type=media_type,
            file_size=file_size,
        )


@dataclass
class GetUploadRecordsRequest:
    limit: int
    last_evaluated_key_user_id: Optional[str] = None
    last_evaluated_key_media_id: Optional[str] = None

    @classmethod
    def from_dict(cls, params: Dict[str, Any], identity_id: str) -> "GetUploadRecordsRequest":
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValidationError("params must be a dict")
        raw_limit = params.get("limit", DEFAULT_LIMIT)
        if isinstance(raw_limit, bool):
            raise ValidationError("Invalid limit parameter")
        try:
            limit = int(raw_limit)
            limit = max(1, min(limit, MAX_LIMIT))
        except (ValueError, TypeError):
            raise ValidationError("Invalid limit parameter") from None

        last_evaluated_key_user_id = None
        last_evaluated_key_media_id = None

        last_key = params.get("lastEvaluatedKey")
        if last_key:
            try:
                exclusive_start_key = json.loads(last_key)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Invalid lastEvaluatedKey parameter") from None

            if not isinstance(exclusive_start_key, dict):
                raise ValidationError("lastEvaluatedKey must be an object")

            if exclusive_start_key.get(FIELD_USER_ID) != identity_id:
                raise AuthorizationError("lastEvaluatedKey does not match your identity")

            media_id_key = exclusive_start_key.get(FIELD_MEDIA_ID)
            if not isinstance(media_id_key, str) or not media_id_key.strip():
                raise ValidationError("lastEvaluatedKey.mediaId must be a non-empty string")

            last_evaluated_key_user_id = identity_id
            last_evaluated_key_media_id = media_id_key.strip()

        return cls(
            limit=limit,
            last_evaluated_key_user_id=last_evaluated_key_user_id,
            last_evaluated_key_media_id=last_evaluated_key_media_id,
        )
