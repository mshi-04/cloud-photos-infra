# ==========================================
# IAM Role for Lambda
# ==========================================
locals {
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role" "lambda" {
  for_each = local.lambda_functions

  name               = "${local.function_prefix}-${each.value.name}-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "logs" {
  for_each = local.lambda_functions

  name = "cloudwatch-logs"
  role = aws_iam_role.lambda[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda[each.key].arn}:*"
      }
    ]
  })
}

# ==========================================
# Data Access Policies
# ==========================================
resource "aws_iam_role_policy" "get_upload_records_dynamodb" {
  name = "dynamodb-query"
  role = aws_iam_role.lambda["get_upload_records"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:Query"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "create_upload_record_dynamodb" {
  name = "dynamodb-put"
  role = aws_iam_role.lambda["create_upload_record"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "delete_upload_record_dynamodb" {
  name = "dynamodb-delete"
  role = aws_iam_role.lambda["delete_upload_record"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "register_device_token_dynamodb" {
  name = "dynamodb-update"
  role = aws_iam_role.lambda["register_device_token"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = var.device_tokens_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "unregister_device_token_dynamodb" {
  name = "dynamodb-delete"
  role = aws_iam_role.lambda["unregister_device_token"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:DeleteItem"]
      Resource = var.device_tokens_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "notify_upload_complete_dynamodb" {
  name = "dynamodb-query-delete"
  role = aws_iam_role.lambda["notify_upload_complete"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query"]
        Resource = var.device_tokens_table_arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:DeleteItem"]
        Resource = var.device_tokens_table_arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "notify_upload_complete_secrets" {
  name = "secretsmanager-get"
  role = aws_iam_role.lambda["notify_upload_complete"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.firebase_credentials_secret_arn
    }]
  })
}

resource "aws_iam_role_policy" "delete_user_s3" {
  name = "s3-delete"
  role = aws_iam_role.lambda["delete_user"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucketVersions"]
        Resource = var.s3_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["private/*"]
          }
        }
      },
      {
        Effect   = "Allow"
        Action   = ["s3:DeleteObjectVersion", "s3:DeleteObject"]
        Resource = "${var.s3_bucket_arn}/private/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "delete_user_dynamodb" {
  name = "dynamodb-query-delete"
  role = aws_iam_role.lambda["delete_user"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:BatchWriteItem"]
        Resource = var.dynamodb_table_arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:BatchWriteItem"]
        Resource = var.device_tokens_table_arn
      }
    ]
  })
}
