from typing import Final

# AWS batch limits
S3_DELETE_BATCH_SIZE: Final = 1000
DYNAMODB_BATCH_WRITE_SIZE: Final = 25

# Retries of DynamoDB UnprocessedItems
MAX_BATCH_WRITE_RETRIES: Final = 5
BATCH_WRITE_BASE_WAIT_SECONDS: Final = 0.1

# Names of the stores reported when their deletion fails
SUBSYSTEM_S3: Final = "S3"
SUBSYSTEM_UPLOAD_RECORDS: Final = "DynamoDB/upload_records"
SUBSYSTEM_DEVICE_TOKENS: Final = "DynamoDB/device_tokens"
