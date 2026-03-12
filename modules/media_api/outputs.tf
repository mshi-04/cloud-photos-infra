output "api_endpoint" {
  description = "API Gateway エンドポイント URL"
  value       = aws_api_gateway_stage.media.invoke_url
}

output "api_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.media.id
}

output "api_execution_arn" {
  description = "API Gateway 実行 ARN"
  value       = aws_api_gateway_rest_api.media.execution_arn
}

output "lambda_role_arn" {
  description = "Lambda 実行ロール ARN"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Lambda 実行ロール名"
  value       = aws_iam_role.lambda.name
}
