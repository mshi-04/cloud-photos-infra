output "api_endpoint" {
  description = "API Gateway エンドポイント URL"
  value       = aws_api_gateway_stage.media.invoke_url
}

output "api_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.media.id
}

output "api_execution_arns" {
  description = "API Gateway 実行 ARN のリスト"
  value       = [
    "${aws_api_gateway_rest_api.media.execution_arn}/*/GET/media/uploads",
    "${aws_api_gateway_rest_api.media.execution_arn}/*/POST/media/uploads",
    "${aws_api_gateway_rest_api.media.execution_arn}/*/DELETE/media/uploads/*"
  ]
}

output "lambda_role_arns" {
  description = "Lambda 実行ロール ARN リスト"
  value       = [
    aws_iam_role.get_upload_records.arn,
    aws_iam_role.create_upload_record.arn,
    aws_iam_role.delete_upload_record.arn
  ]
}

output "lambda_role_names" {
  description = "Lambda 実行ロール名 リスト"
  value       = [
    aws_iam_role.get_upload_records.name,
    aws_iam_role.create_upload_record.name,
    aws_iam_role.delete_upload_record.name
  ]
}
