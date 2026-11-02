from typing import Final

# DynamoDB field names
FIELD_USER_ID: Final = "userId"
FIELD_MEDIA_ID: Final = "mediaId"
FIELD_CLOUD_STORAGE_PATH: Final = "cloudStoragePath"
FIELD_CONTENT_TYPE: Final = "contentType"
FIELD_MEDIA_TYPE: Final = "mediaType"
FIELD_FILE_SIZE: Final = "fileSize"
FIELD_UPLOADED_AT: Final = "uploadedAt"
FIELD_UPDATED_AT: Final = "updatedAt"
FIELD_IS_DELETED: Final = "isDeleted"

# Query string parameters
PARAM_LIMIT: Final = "limit"
PARAM_LAST_EVALUATED_KEY: Final = "lastEvaluatedKey"

# Storage path
PRIVATE_PATH_PREFIX: Final = "private/"

# Pagination
MIN_LIMIT: Final = 1
DEFAULT_LIMIT: Final = 100
MAX_LIMIT: Final = 500
