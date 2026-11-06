from typing import Final

# Request body and pagination key field names
FIELD_USER_ID: Final = "userId"
FIELD_MEDIA_ID: Final = "mediaId"
FIELD_CLOUD_STORAGE_PATH: Final = "cloudStoragePath"
FIELD_CONTENT_TYPE: Final = "contentType"
FIELD_MEDIA_TYPE: Final = "mediaType"
FIELD_FILE_SIZE: Final = "fileSize"

# DynamoDB field names
FIELD_UPLOADED_AT: Final = "uploadedAt"
FIELD_UPDATED_AT: Final = "updatedAt"
FIELD_IS_DELETED: Final = "isDeleted"

# Query string parameters
PARAM_LIMIT: Final = "limit"
PARAM_LAST_EVALUATED_KEY: Final = "lastEvaluatedKey"

# Pagination
MIN_LIMIT: Final = 1
DEFAULT_LIMIT: Final = 100
MAX_LIMIT: Final = 500

# File size: the largest signed 64-bit integer, well within the DynamoDB number range
MAX_FILE_SIZE: Final = 2**63 - 1
