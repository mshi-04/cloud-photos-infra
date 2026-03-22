output "firebase_credentials_secret_arn" {
  description = "Firebase クレデンシャルの Secrets Manager ARN"
  value       = aws_secretsmanager_secret.firebase_credentials.arn
}

output "firebase_layer_arn" {
  description = "firebase-admin Lambda Layer ARN"
  value       = aws_lambda_layer_version.firebase_admin.arn
}
