# ==========================================
# GitHub OIDC Provider
# ==========================================
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["1c58a3a8518e8759bf075b76b750d4f2df264fcd", "6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  github_repo  = "mshi-04/cloud-photos-infra"
  project_name = "cloud-photos"
  account_id   = data.aws_caller_identity.current.account_id
  region       = data.aws_region.current.id

  environments = {
    dev = {
      plan_subjects = ["pull_request", "ref:refs/heads/develop", "ref:refs/heads/main"]
      apply_subject = "environment:development"
    }
    prod = {
      plan_subjects = ["pull_request", "ref:refs/heads/main"]
      apply_subject = "environment:production"
    }
  }

  # The order goes into the policy JSON, so reordering changes the policies.
  # scripts/check_lambda_role_names.py compares these names with modules/media_api.
  lambda_function_names = [
    "get-upload-records",
    "create-upload-record",
    "delete-upload-record",
    "register-device-token",
    "unregister-device-token",
    "notify-upload-complete",
    "delete-user",
  ]

  environment_arns = {
    for env in keys(local.environments) : env => {
      media_bucket               = "arn:aws:s3:::${local.account_id}-${local.project_name}-media-${env}"
      cognito_authenticated_role = "arn:aws:iam::${local.account_id}:role/${local.project_name}-cognito-authenticated-${env}"
      dynamodb_tables = [
        "arn:aws:dynamodb:${local.region}:${local.account_id}:table/${local.project_name}-upload-records-${env}",
        "arn:aws:dynamodb:${local.region}:${local.account_id}:table/${local.project_name}-device-tokens-${env}",
      ]
      firebase_secret      = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:${local.project_name}-firebase-credentials-${env}-*"
      lambda_layer         = "arn:aws:lambda:${local.region}:${local.account_id}:layer:${local.project_name}-*-${env}"
      lambda_layer_version = "arn:aws:lambda:${local.region}:${local.account_id}:layer:${local.project_name}-*-${env}:*"
      lambda_function      = "arn:aws:lambda:${local.region}:${local.account_id}:function:${local.project_name}-${env}-*"
      lambda_roles         = [for name in local.lambda_function_names : "arn:aws:iam::${local.account_id}:role/${local.project_name}-${env}-${name}-role"]
      log_group            = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${local.project_name}-${env}-*"
    }
  }

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
    Resource = "arn:aws:cognito-idp:${local.region}:${local.account_id}:userpool/*"
  }

  identity_pool_read_policy = {
    Sid    = "AllowIdentityPoolRead"
    Effect = "Allow"
    Action = [
      "cognito-identity:DescribeIdentityPool",
      "cognito-identity:GetIdentityPoolRoles",
      "cognito-identity:ListTagsForResource"
    ]
    Resource = "arn:aws:cognito-identity:${local.region}:${local.account_id}:identitypool/*"
  }
}

# ==========================================
# Plan Roles
# ==========================================
resource "aws_iam_role" "plan" {
  for_each = local.environments

  name = "gh-terraform-plan-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [for subject in each.value.plan_subjects : "repo:${local.github_repo}:${subject}"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "plan" {
  for_each = local.environments

  name = "terraform-plan-${each.key}-policy"
  role = aws_iam_role.plan[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/${each.key}/terraform.tfstate"
        ]
      },
      {
        Sid    = "AllowStateLock"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.terraform_state.arn}/${each.key}/terraform.tfstate.tflock"
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
        Resource = local.environment_arns[each.key].media_bucket
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
        Resource = concat([local.environment_arns[each.key].cognito_authenticated_role], local.environment_arns[each.key].lambda_roles)
      },
      {
        Sid    = "AllowDynamoDBRead"
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:DescribeContinuousBackups",
          "dynamodb:DescribeTimeToLive",
          "dynamodb:ListTagsOfResource"
        ]
        Resource = local.environment_arns[each.key].dynamodb_tables
      },
      {
        Sid    = "AllowLambdaReadForPlan"
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:GetFunctionCodeSigningConfig",
          "lambda:ListVersionsByFunction",
          "lambda:GetPolicy"
        ]
        Resource = local.environment_arns[each.key].lambda_function
      },
      {
        Sid    = "AllowAPIGatewayReadForPlan"
        Effect = "Allow"
        Action = [
          "apigateway:GET"
        ]
        Resource = "arn:aws:apigateway:${local.region}::/*"
      },
      {
        Sid    = "AllowCloudWatchLogsDescribeAll"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchLogsReadForPlan"
        Effect = "Allow"
        Action = [
          "logs:ListTagsForResource"
        ]
        Resource = local.environment_arns[each.key].log_group
      },
      {
        Sid    = "AllowSecretsManagerReadForPlan"
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetResourcePolicy"
        ]
        Resource = local.environment_arns[each.key].firebase_secret
      },
      {
        Sid    = "AllowLambdaLayerReadForPlan"
        Effect = "Allow"
        Action = [
          "lambda:GetLayerVersion"
        ]
        Resource = local.environment_arns[each.key].lambda_layer_version
      }
    ]
  })
}

# ==========================================
# Apply Roles
# ==========================================
resource "aws_iam_role" "apply" {
  for_each = local.environments

  name = "gh-terraform-apply-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${local.github_repo}:${each.value.apply_subject}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "apply" {
  for_each = local.environments

  name = "terraform-apply-${each.key}-policy"
  role = aws_iam_role.apply[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStateReadWrite"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/${each.key}/terraform.tfstate",
          "${aws_s3_bucket.terraform_state.arn}/${each.key}/terraform.tfstate.tflock"
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
        Resource = "arn:aws:cognito-idp:${local.region}:${local.account_id}:userpool/*"
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
        Resource = "arn:aws:cognito-identity:${local.region}:${local.account_id}:identitypool/*"
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
        Resource = local.environment_arns[each.key].media_bucket
      },
      {
        Sid    = "AllowMediaBucketObjectManagement"
        Effect = "Allow"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "${local.environment_arns[each.key].media_bucket}/*"
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
        Resource = concat([local.environment_arns[each.key].cognito_authenticated_role], local.environment_arns[each.key].lambda_roles)
      },
      {
        Sid      = "AllowPassRoleLambda"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = local.environment_arns[each.key].lambda_roles
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "lambda.amazonaws.com"
          }
        }
      },
      {
        # Cognito's SetIdentityPoolRoles does not pass the iam:PassedToService context, so a Condition
        # would implicitly deny it. The Resource is limited to this role instead.
        Sid      = "AllowPassRoleCognito"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [local.environment_arns[each.key].cognito_authenticated_role]
      },
      {
        Sid    = "AllowDynamoDBManagement"
        Effect = "Allow"
        Action = [
          "dynamodb:CreateTable",
          "dynamodb:DeleteTable",
          "dynamodb:UpdateTable",
          "dynamodb:DescribeTable",
          "dynamodb:DescribeContinuousBackups",
          "dynamodb:UpdateContinuousBackups",
          "dynamodb:DescribeTimeToLive",
          "dynamodb:TagResource",
          "dynamodb:UntagResource",
          "dynamodb:ListTagsOfResource"
        ]
        Resource = local.environment_arns[each.key].dynamodb_tables
      },
      {
        Sid    = "AllowLambdaManagement"
        Effect = "Allow"
        Action = [
          "lambda:CreateFunction",
          "lambda:DeleteFunction",
          "lambda:GetFunction",
          "lambda:GetFunctionCodeSigningConfig",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:ListVersionsByFunction",
          "lambda:GetPolicy",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:TagResource",
          "lambda:UntagResource"
        ]
        Resource = local.environment_arns[each.key].lambda_function
      },
      {
        Sid    = "AllowLambdaLayerPublish"
        Effect = "Allow"
        Action = [
          "lambda:PublishLayerVersion"
        ]
        Resource = local.environment_arns[each.key].lambda_layer
      },
      {
        Sid    = "AllowLambdaLayerVersionManagement"
        Effect = "Allow"
        Action = [
          "lambda:GetLayerVersion",
          "lambda:DeleteLayerVersion"
        ]
        Resource = local.environment_arns[each.key].lambda_layer_version
      },
      {
        Sid    = "AllowAPIGatewayManagement"
        Effect = "Allow"
        Action = [
          "apigateway:GET",
          "apigateway:POST",
          "apigateway:PUT",
          "apigateway:DELETE",
          "apigateway:PATCH"
        ]
        Resource = "arn:aws:apigateway:${local.region}::/*"
      },
      {
        Sid    = "AllowSecretsManagerManagement"
        Effect = "Allow"
        Action = [
          "secretsmanager:CreateSecret",
          "secretsmanager:DeleteSecret",
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetResourcePolicy",
          "secretsmanager:TagResource",
          "secretsmanager:UntagResource"
        ]
        Resource = local.environment_arns[each.key].firebase_secret
      },
      {
        Sid    = "AllowCloudWatchLogsDescribeAll"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchLogsManagement"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:PutRetentionPolicy",
          "logs:TagResource",
          "logs:UntagResource",
          "logs:ListTagsForResource"
        ]
        Resource = local.environment_arns[each.key].log_group
      }
    ]
  })
}
