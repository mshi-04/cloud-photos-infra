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
  value = [
    local.api_execution_arns.get_uploads,
    local.api_execution_arns.post_uploads,
    local.api_execution_arns.delete_upload,
    local.api_execution_arns.put_devices_token,
    local.api_execution_arns.delete_devices_token,
    local.api_execution_arns.post_uploads_complete,
    local.api_execution_arns.delete_user,
  ]
}

output "lambda_role_arns" {
  description = "Lambda 実行ロール ARN リスト"
  value = [
    aws_iam_role.get_upload_records.arn,
    aws_iam_role.create_upload_record.arn,
    aws_iam_role.delete_upload_record.arn,
    aws_iam_role.register_device_token.arn,
    aws_iam_role.unregister_device_token.arn,
    aws_iam_role.notify_upload_complete.arn,
    aws_iam_role.delete_user.arn
  ]
}

output "lambda_role_names" {
  description = "Lambda 実行ロール名 リスト"
  value = [
    aws_iam_role.get_upload_records.name,
    aws_iam_role.create_upload_record.name,
    aws_iam_role.delete_upload_record.name,
    aws_iam_role.register_device_token.name,
    aws_iam_role.unregister_device_token.name,
    aws_iam_role.notify_upload_complete.name,
    aws_iam_role.delete_user.name
  ]
}
