output "firebase_credentials_secret_arn" {
  description = "Firebase クレデンシャルの Secrets Manager ARN"
  value       = aws_secretsmanager_secret.firebase_credentials.arn
}
