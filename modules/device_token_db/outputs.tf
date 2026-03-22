output "table_name" {
  description = "DynamoDB テーブル名"
  value       = aws_dynamodb_table.device_tokens.name
}

output "table_arn" {
  description = "DynamoDB テーブル ARN"
  value       = aws_dynamodb_table.device_tokens.arn
}
