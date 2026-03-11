data "aws_region" "current" {}

# ==========================================
# Cognito Identity Pool
# ==========================================
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.project_name}-identity-pool-${var.env}"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = var.user_pool_client_id
    provider_name           = "cognito-idp.${data.aws_region.current.id}.amazonaws.com/${var.user_pool_id}"
    server_side_token_check = true
  }
}

# ==========================================
# IAM Role for Authenticated Users
# ==========================================
resource "aws_iam_role" "authenticated" {
  name = "${var.project_name}-cognito-authenticated-${var.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = "cognito-identity.amazonaws.com"
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
        }
        "ForAnyValue:StringLike" = {
          "cognito-identity.amazonaws.com:amr" = "authenticated"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "authenticated_s3" {
  name = "media-storage-access"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPrivateReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${var.media_bucket_arn}/private/$${cognito-identity.amazonaws.com:sub}/*"
      },
      {
        Sid      = "AllowPrivateList"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = var.media_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = "private/$${cognito-identity.amazonaws.com:sub}/*"
          }
        }
      }
    ]
  })
}

# ==========================================
# Role Attachment
# ==========================================
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    "authenticated" = aws_iam_role.authenticated.arn
  }
}
