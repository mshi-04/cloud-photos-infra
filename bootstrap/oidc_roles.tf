# ==========================================
# GitHub OIDC Provider
# ==========================================
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["1c58a3a8518e8759bf075b76b750d4f2df264fcd", "6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# ローカル変数としてリポジトリ情報を定義
locals {
  github_repo  = "mshi-04/cloud-photos-infra"
  project_name = "cloud-photos"

  cognito_read_policy = {
    Sid    = "AllowCognitoRead"
    Effect = "Allow"
    Action = [
      "cognito-idp:DescribeUserPool",
      "cognito-idp:DescribeUserPoolClient",
      "cognito-idp:ListUserPoolClients",
      "cognito-idp:GetUserPoolMfaConfig",
      "cognito-idp:ListTagsForResource"
    ]
    Resource = "arn:aws:cognito-idp:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:userpool/*"
  }

  identity_pool_read_policy = {
    Sid    = "AllowIdentityPoolRead"
    Effect = "Allow"
    Action = [
      "cognito-identity:DescribeIdentityPool",
      "cognito-identity:GetIdentityPoolRoles",
      "cognito-identity:ListTagsForResource"
    ]
    Resource = "arn:aws:cognito-identity:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:identitypool/*"
  }

  media_bucket_arn_dev  = "arn:aws:s3:::${data.aws_caller_identity.current.account_id}-${local.project_name}-media-dev"
  media_bucket_arn_prod = "arn:aws:s3:::${data.aws_caller_identity.current.account_id}-${local.project_name}-media-prod"

  cognito_authenticated_role_arn_dev  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.project_name}-cognito-authenticated-dev"
  cognito_authenticated_role_arn_prod = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.project_name}-cognito-authenticated-prod"
}

# ==========================================
# 1. Plan-Dev Role
# ==========================================
resource "aws_iam_role" "plan_dev" {
  name = "gh-terraform-plan-dev"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            "repo:${local.github_repo}:pull_request",
            "repo:${local.github_repo}:ref:refs/heads/develop",
            "repo:${local.github_repo}:ref:refs/heads/main"
          ]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "plan_dev" {
  name = "terraform-plan-dev-policy"
  role = aws_iam_role.plan_dev.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/dev/terraform.tfstate"
        ]
      },
      {
        Sid    = "AllowStateLock"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.terraform_state.arn}/dev/terraform.tfstate.tflock"
        ]
      },
      {
        Sid      = "AllowKMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      local.cognito_read_policy,
      local.identity_pool_read_policy,
      {
        Sid    = "AllowMediaBucketRead"
        Effect = "Allow"
        Action = [
          "s3:Get*",
          "s3:ListBucket"
        ]
        Resource = local.media_bucket_arn_dev
      },
      {
        Sid    = "AllowIAMReadForPlan"
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies"
        ]
        Resource = local.cognito_authenticated_role_arn_dev
      }
    ]
  })
}

# ==========================================
# 2. Apply-Dev Role
# ==========================================
resource "aws_iam_role" "apply_dev" {
  name = "gh-terraform-apply-dev"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${local.github_repo}:environment:development"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "apply_dev" {
  name = "terraform-apply-dev-policy"
  role = aws_iam_role.apply_dev.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateReadWrite"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/dev/terraform.tfstate",
          "${aws_s3_bucket.terraform_state.arn}/dev/terraform.tfstate.tflock"
        ]
      },
      {
        Sid      = "AllowKMSEncryptDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid    = "AllowCognitoCreateUserPool"
        Effect = "Allow"
        Action = [
          "cognito-idp:CreateUserPool"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCognitoManagementUserPool"
        Effect = "Allow"
        Action = [
          "cognito-idp:UpdateUserPool",
          "cognito-idp:DeleteUserPool",
          "cognito-idp:DescribeUserPool",
          "cognito-idp:CreateUserPoolClient",
          "cognito-idp:UpdateUserPoolClient",
          "cognito-idp:DeleteUserPoolClient",
          "cognito-idp:DescribeUserPoolClient",
          "cognito-idp:ListUserPoolClients",
          "cognito-idp:SetUserPoolMfaConfig",
          "cognito-idp:GetUserPoolMfaConfig",
          "cognito-idp:TagResource",
          "cognito-idp:UntagResource",
          "cognito-idp:ListTagsForResource"
        ]
        Resource = "arn:aws:cognito-idp:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:userpool/*"
      },
      {
        Sid    = "AllowIdentityPoolCreate"
        Effect = "Allow"
        Action = [
          "cognito-identity:CreateIdentityPool"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowIdentityPoolManagement"
        Effect = "Allow"
        Action = [
          "cognito-identity:DescribeIdentityPool",
          "cognito-identity:UpdateIdentityPool",
          "cognito-identity:DeleteIdentityPool",
          "cognito-identity:SetIdentityPoolRoles",
          "cognito-identity:GetIdentityPoolRoles",
          "cognito-identity:TagResource",
          "cognito-identity:UntagResource",
          "cognito-identity:ListTagsForResource"
        ]
        Resource = "arn:aws:cognito-identity:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:identitypool/*"
      },
      {
        Sid    = "AllowMediaBucketManagement"
        Effect = "Allow"
        Action = [
          "s3:Get*",
          "s3:Put*",
          "s3:List*",
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:DeleteBucketPolicy"
        ]
        Resource = local.media_bucket_arn_dev
      },
      {
        Sid    = "AllowMediaBucketObjectManagement"
        Effect = "Allow"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "${local.media_bucket_arn_dev}/*"
      },
      {
        Sid    = "AllowIAMForAuthenticatedRole"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListInstanceProfilesForRole",
          "iam:UpdateAssumeRolePolicy"
        ]
        Resource = local.cognito_authenticated_role_arn_dev
      },
      {
        Sid    = "AllowPassRoleToCognitoIdentity"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = local.cognito_authenticated_role_arn_dev
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "cognito-identity.amazonaws.com"
          }
        }
      }
    ]
  })
}

# ==========================================
# 3. Plan-Prod Role
# ==========================================
resource "aws_iam_role" "plan_prod" {
  name = "gh-terraform-plan-prod"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            "repo:${local.github_repo}:pull_request",
            "repo:${local.github_repo}:ref:refs/heads/main"
          ]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "plan_prod" {
  name = "terraform-plan-prod-policy"
  role = aws_iam_role.plan_prod.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/prod/terraform.tfstate"
        ]
      },
      {
        Sid    = "AllowStateLock"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.terraform_state.arn}/prod/terraform.tfstate.tflock"
        ]
      },
      {
        Sid      = "AllowKMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      local.cognito_read_policy,
      local.identity_pool_read_policy,
      {
        Sid    = "AllowMediaBucketRead"
        Effect = "Allow"
        Action = [
          "s3:Get*",
          "s3:ListBucket"
        ]
        Resource = local.media_bucket_arn_prod
      },
      {
        Sid    = "AllowIAMReadForPlan"
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies"
        ]
        Resource = local.cognito_authenticated_role_arn_prod
      }
    ]
  })
}

# ==========================================
# 4. Apply-Prod Role (Environment: production)
# ==========================================
resource "aws_iam_role" "apply_prod" {
  name = "gh-terraform-apply-prod"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${local.github_repo}:environment:production"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "apply_prod" {
  name = "terraform-apply-prod-policy"
  role = aws_iam_role.apply_prod.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateReadWrite"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/prod/terraform.tfstate",
          "${aws_s3_bucket.terraform_state.arn}/prod/terraform.tfstate.tflock"
        ]
      },
      {
        Sid      = "AllowKMSEncryptDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid    = "AllowCognitoCreateUserPool"
        Effect = "Allow"
        Action = [
          "cognito-idp:CreateUserPool"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCognitoManagementUserPool"
        Effect = "Allow"
        Action = [
          "cognito-idp:UpdateUserPool",
          "cognito-idp:DeleteUserPool",
          "cognito-idp:DescribeUserPool",
          "cognito-idp:CreateUserPoolClient",
          "cognito-idp:UpdateUserPoolClient",
          "cognito-idp:DeleteUserPoolClient",
          "cognito-idp:DescribeUserPoolClient",
          "cognito-idp:ListUserPoolClients",
          "cognito-idp:SetUserPoolMfaConfig",
          "cognito-idp:GetUserPoolMfaConfig",
          "cognito-idp:TagResource",
          "cognito-idp:UntagResource",
          "cognito-idp:ListTagsForResource"
        ]
        Resource = "arn:aws:cognito-idp:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:userpool/*"
      },
      {
        Sid    = "AllowIdentityPoolCreate"
        Effect = "Allow"
        Action = [
          "cognito-identity:CreateIdentityPool"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowIdentityPoolManagement"
        Effect = "Allow"
        Action = [
          "cognito-identity:DescribeIdentityPool",
          "cognito-identity:UpdateIdentityPool",
          "cognito-identity:DeleteIdentityPool",
          "cognito-identity:SetIdentityPoolRoles",
          "cognito-identity:GetIdentityPoolRoles",
          "cognito-identity:TagResource",
          "cognito-identity:UntagResource",
          "cognito-identity:ListTagsForResource"
        ]
        Resource = "arn:aws:cognito-identity:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:identitypool/*"
      },
      {
        Sid    = "AllowMediaBucketManagement"
        Effect = "Allow"
        Action = [
          "s3:Get*",
          "s3:Put*",
          "s3:List*",
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:DeleteBucketPolicy"
        ]
        Resource = local.media_bucket_arn_prod
      },
      {
        Sid    = "AllowMediaBucketObjectManagement"
        Effect = "Allow"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "${local.media_bucket_arn_prod}/*"
      },
      {
        Sid    = "AllowIAMForAuthenticatedRole"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListInstanceProfilesForRole",
          "iam:UpdateAssumeRolePolicy"
        ]
        Resource = local.cognito_authenticated_role_arn_prod
      },
      {
        Sid    = "AllowPassRoleToCognitoIdentity"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = local.cognito_authenticated_role_arn_prod
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "cognito-identity.amazonaws.com"
          }
        }
      }
    ]
  })
}
