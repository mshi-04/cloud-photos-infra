# ==========================================
# DynamoDB Table: upload_records
# ==========================================
resource "aws_dynamodb_table" "upload_records" {
  name         = "${var.project_name}-upload-records-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "mediaId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "mediaId"
    type = "S"
  }

  deletion_protection_enabled = var.deletion_protection_enabled

  point_in_time_recovery {
    enabled = true
  }
}
