output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

output "identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = module.identity_pool.identity_pool_id
}

output "media_bucket_name" {
  description = "Media storage bucket name"
  value       = module.media_storage.bucket_name
}

output "media_api_endpoint" {
  description = "Media API Gateway endpoint URL"
  value       = module.media_api.api_endpoint
}

output "upload_records_table_name" {
  description = "DynamoDB upload_records table name"
  value       = module.media_db.table_name
}
