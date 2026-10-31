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

resource "aws_iam_role" "get_upload_records" {
  name               = "${local.function_prefix}-get-upload-records-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "get_upload_records_dynamodb" {
  name = "dynamodb-query"
  role = aws_iam_role.get_upload_records.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:Query"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "get_upload_records_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.get_upload_records.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["get_upload_records"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "create_upload_record" {
  name               = "${local.function_prefix}-create-upload-record-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "create_upload_record_dynamodb" {
  name = "dynamodb-put"
  role = aws_iam_role.create_upload_record.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "create_upload_record_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.create_upload_record.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["create_upload_record"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "delete_upload_record" {
  name               = "${local.function_prefix}-delete-upload-record-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "delete_upload_record_dynamodb" {
  name = "dynamodb-delete"
  role = aws_iam_role.delete_upload_record.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "delete_upload_record_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.delete_upload_record.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["delete_upload_record"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "register_device_token" {
  name               = "${local.function_prefix}-register-device-token-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "register_device_token_dynamodb" {
  name = "dynamodb-update"
  role = aws_iam_role.register_device_token.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = var.device_tokens_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "register_device_token_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.register_device_token.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["register_device_token"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "unregister_device_token" {
  name               = "${local.function_prefix}-unregister-device-token-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "unregister_device_token_dynamodb" {
  name = "dynamodb-delete"
  role = aws_iam_role.unregister_device_token.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:DeleteItem"]
      Resource = var.device_tokens_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "unregister_device_token_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.unregister_device_token.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["unregister_device_token"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "notify_upload_complete" {
  name               = "${local.function_prefix}-notify-upload-complete-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "notify_upload_complete_dynamodb" {
  name = "dynamodb-query-delete"
  role = aws_iam_role.notify_upload_complete.id
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
  role = aws_iam_role.notify_upload_complete.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.firebase_credentials_secret_arn
    }]
  })
}

resource "aws_iam_role_policy" "notify_upload_complete_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.notify_upload_complete.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["notify_upload_complete"].arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "delete_user" {
  name               = "${local.function_prefix}-delete-user-role"
  assume_role_policy = local.assume_role_policy
}

resource "aws_iam_role_policy" "delete_user_s3" {
  name = "s3-delete"
  role = aws_iam_role.delete_user.id
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
  role = aws_iam_role.delete_user.id
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

resource "aws_iam_role_policy" "delete_user_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.delete_user.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda["delete_user"].arn}:*"
      }
    ]
  })
}
