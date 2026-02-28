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
  github_repo = "mshi-04/cloud-photos-infra"
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
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:${local.github_repo}:pull_request" }
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
        Sid      = "AllowKMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid      = "AllowDynamoDBLock"
        Effect   = "Allow"
        Action   = ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.terraform_state_lock.arn
      },
      {
        Sid      = "AllowCognitoListPools"
        Effect   = "Allow"
        Action   = ["cognito-idp:ListUserPools"]
        Resource = "*"
      },
      {
        Sid      = "AllowCognitoReadOnly"
        Effect   = "Allow"
        Action   = ["cognito-idp:Describe*", "cognito-idp:Get*", "cognito-idp:ListUsers", "cognito-idp:ListUsersInGroup", "cognito-idp:ListUserPoolClients", "cognito-idp:ListGroups", "cognito-idp:ListIdentityProviders", "cognito-idp:ListResourceServers", "cognito-idp:ListTagsForResource", "cognito-idp:ListUserImportJobs"]
        Resource = "arn:aws:cognito-idp:ap-northeast-1:${data.aws_caller_identity.current.account_id}:userpool/*"
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
          "${aws_s3_bucket.terraform_state.arn}/dev/terraform.tfstate"
        ]
      },
      {
        Sid      = "AllowKMSEncryptDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid      = "AllowDynamoDBLockReadWrite"
        Effect   = "Allow"
        Action   = ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.terraform_state_lock.arn
      },
      {
        Sid      = "AllowCognitoListPools"
        Effect   = "Allow"
        Action   = ["cognito-idp:ListUserPools"]
        Resource = "*"
      },
      {
        Sid      = "AllowCognitoManage"
        Effect   = "Allow"
        Action   = ["cognito-idp:Describe*", "cognito-idp:Get*", "cognito-idp:ListUsers", "cognito-idp:ListUsersInGroup", "cognito-idp:ListUserPoolClients", "cognito-idp:ListGroups", "cognito-idp:ListIdentityProviders", "cognito-idp:ListResourceServers", "cognito-idp:ListTagsForResource", "cognito-idp:ListUserImportJobs", "cognito-idp:CreateUserPool", "cognito-idp:UpdateUserPool", "cognito-idp:DeleteUserPool", "cognito-idp:CreateUserPoolClient", "cognito-idp:UpdateUserPoolClient", "cognito-idp:DeleteUserPoolClient"]
        Resource = "arn:aws:cognito-idp:ap-northeast-1:${data.aws_caller_identity.current.account_id}:userpool/*"
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
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:${local.github_repo}:pull_request" }
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
        Sid      = "AllowKMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid      = "AllowDynamoDBLock"
        Effect   = "Allow"
        Action   = ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.terraform_state_lock.arn
      },
      {
        Sid      = "AllowCognitoListPools"
        Effect   = "Allow"
        Action   = ["cognito-idp:ListUserPools"]
        Resource = "*"
      },
      {
        Sid      = "AllowCognitoReadOnly"
        Effect   = "Allow"
        Action   = ["cognito-idp:Describe*", "cognito-idp:Get*", "cognito-idp:ListUsers", "cognito-idp:ListUsersInGroup", "cognito-idp:ListUserPoolClients", "cognito-idp:ListGroups", "cognito-idp:ListIdentityProviders", "cognito-idp:ListResourceServers", "cognito-idp:ListTagsForResource", "cognito-idp:ListUserImportJobs"]
        Resource = "arn:aws:cognito-idp:ap-northeast-1:${data.aws_caller_identity.current.account_id}:userpool/*"
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
          "${aws_s3_bucket.terraform_state.arn}/prod/terraform.tfstate"
        ]
      },
      {
        Sid      = "AllowKMSEncryptDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.terraform_state.arn
      },
      {
        Sid      = "AllowDynamoDBLockReadWrite"
        Effect   = "Allow"
        Action   = ["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.terraform_state_lock.arn
      },
      {
        Sid      = "AllowCognitoListPools"
        Effect   = "Allow"
        Action   = ["cognito-idp:ListUserPools"]
        Resource = "*"
      },
      {
        Sid      = "AllowCognitoManage"
        Effect   = "Allow"
        Action   = ["cognito-idp:Describe*", "cognito-idp:Get*", "cognito-idp:ListUsers", "cognito-idp:ListUsersInGroup", "cognito-idp:ListUserPoolClients", "cognito-idp:ListGroups", "cognito-idp:ListIdentityProviders", "cognito-idp:ListResourceServers", "cognito-idp:ListTagsForResource", "cognito-idp:ListUserImportJobs", "cognito-idp:CreateUserPool", "cognito-idp:UpdateUserPool", "cognito-idp:DeleteUserPool", "cognito-idp:CreateUserPoolClient", "cognito-idp:UpdateUserPoolClient", "cognito-idp:DeleteUserPoolClient"]
        Resource = "arn:aws:cognito-idp:ap-northeast-1:${data.aws_caller_identity.current.account_id}:userpool/*"
      }
    ]
  })
}
