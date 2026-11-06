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
  # The order is listed by hand: it goes into the identity pool role's policy JSON, which values() would reorder.
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
