resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool-${var.env}"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  deletion_protection = var.deletion_protection

  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = var.temporary_password_validity_days
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  mfa_configuration = var.mfa_configuration
  software_token_mfa_configuration {
    enabled = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # TODO: 本番環境のメール送信（SES連携）
  # email_configuration {
  #   email_sending_account = var.env == "prod" ? "DEVELOPER" : "COGNITO_DEFAULT"
  #   source_arn            = var.env == "prod" ? aws_ses_domain_identity.main.arn : null
  # }
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-user-pool-client-${var.env}"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret               = false
  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}
