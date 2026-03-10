output "identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = aws_cognito_identity_pool.main.id
}

output "authenticated_role_arn" {
  description = "IAM role ARN for authenticated users"
  value       = aws_iam_role.authenticated.arn
}
