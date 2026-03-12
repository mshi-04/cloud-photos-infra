output "table_name" {
  description = "DynamoDB テーブル名"
  value       = aws_dynamodb_table.upload_records.name
}

output "table_arn" {
  description = "DynamoDB テーブル ARN"
  value       = aws_dynamodb_table.upload_records.arn
}
