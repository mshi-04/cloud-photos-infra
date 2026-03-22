# ==========================================
# DynamoDB Table: device_tokens
# ==========================================
resource "aws_dynamodb_table" "device_tokens" {
  name         = "${var.project_name}-device-tokens-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "deviceToken"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "deviceToken"
    type = "S"
  }

  deletion_protection_enabled = var.deletion_protection_enabled

  point_in_time_recovery {
    enabled = true
  }
}
