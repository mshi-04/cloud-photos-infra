data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  function_prefix = "${var.project_name}-${var.env}"
  lambda_functions = {
    get_upload_records      = "get-upload-records"
    create_upload_record    = "create-upload-record"
    delete_upload_record    = "delete-upload-record"
    register_device_token   = "register-device-token"
    unregister_device_token = "unregister-device-token"
    notify_upload_complete  = "notify-upload-complete"
    delete_user             = "delete-user"
  }
}

# ==========================================
# Lambda Source Archives
# ==========================================
data "archive_file" "media_uploads" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/media_uploads"
  output_path = "${path.module}/../../.build/media_uploads.zip"
}

# Explicit source lists for Lambda ZIPs that bundle files from multiple directories
# (function-specific files + shared lambda/common/). To add or remove a file,
# update the relevant local below; the dynamic source blocks will reflect the change
# automatically. Introduced to share common/ alongside function files (see Issue #41).
locals {
  device_tokens_sources = [
    { path = "lambda/device_tokens/auth.py", filename = "auth.py" },
    { path = "lambda/device_tokens/constants.py", filename = "constants.py" },
    { path = "lambda/device_tokens/db.py", filename = "db.py" },
    { path = "lambda/device_tokens/register_device_token.py", filename = "register_device_token.py" },
    { path = "lambda/device_tokens/request_utils.py", filename = "request_utils.py" },
    { path = "lambda/device_tokens/response.py", filename = "response.py" },
    { path = "lambda/device_tokens/unregister_device_token.py", filename = "unregister_device_token.py" },
    { path = "lambda/common/__init__.py", filename = "common/__init__.py" },
    { path = "lambda/common/auth.py", filename = "common/auth.py" },
  ]
  push_notification_sources = [
    { path = "lambda/push_notification/auth.py", filename = "auth.py" },
    { path = "lambda/push_notification/constants.py", filename = "constants.py" },
    { path = "lambda/push_notification/notify_upload_complete.py", filename = "notify_upload_complete.py" },
    { path = "lambda/push_notification/response.py", filename = "response.py" },
    { path = "lambda/common/__init__.py", filename = "common/__init__.py" },
    { path = "lambda/common/auth.py", filename = "common/auth.py" },
  ]
}

data "archive_file" "device_tokens" {
  type        = "zip"
  output_path = "${path.module}/../../.build/device_tokens.zip"

  dynamic "source" {
    for_each = local.device_tokens_sources
    content {
      content  = file("${path.module}/../../${source.value.path}")
      filename = source.value.filename
    }
  }
}

data "archive_file" "push_notification" {
  type        = "zip"
  output_path = "${path.module}/../../.build/push_notification.zip"

  dynamic "source" {
    for_each = local.push_notification_sources
    content {
      content  = file("${path.module}/../../${source.value.path}")
      filename = source.value.filename
    }
  }
}

data "archive_file" "users" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/users"
  output_path = "${path.module}/../../.build/users.zip"
  excludes    = ["tests/*", "tests/**"]
}

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

# ==========================================
# CloudWatch Log Groups
# ==========================================
resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambda_functions
  name              = "/aws/lambda/${local.function_prefix}-${each.value}"
  retention_in_days = var.log_retention_in_days
}

# ==========================================
# Lambda Functions
# ==========================================
resource "aws_lambda_function" "get_upload_records" {
  function_name    = "${local.function_prefix}-get-upload-records"
  role             = aws_iam_role.get_upload_records.arn
  handler          = "get_upload_records.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.media_uploads.output_path
  source_code_hash = data.archive_file.media_uploads.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["get_upload_records"]]
}

resource "aws_lambda_function" "create_upload_record" {
  function_name    = "${local.function_prefix}-create-upload-record"
  role             = aws_iam_role.create_upload_record.arn
  handler          = "create_upload_record.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.media_uploads.output_path
  source_code_hash = data.archive_file.media_uploads.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["create_upload_record"]]
}

resource "aws_lambda_function" "delete_upload_record" {
  function_name    = "${local.function_prefix}-delete-upload-record"
  role             = aws_iam_role.delete_upload_record.arn
  handler          = "delete_upload_record.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.media_uploads.output_path
  source_code_hash = data.archive_file.media_uploads.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["delete_upload_record"]]
}

resource "aws_lambda_function" "register_device_token" {
  function_name    = "${local.function_prefix}-register-device-token"
  role             = aws_iam_role.register_device_token.arn
  handler          = "register_device_token.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.device_tokens.output_path
  source_code_hash = data.archive_file.device_tokens.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.device_tokens_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["register_device_token"]]
}

resource "aws_lambda_function" "unregister_device_token" {
  function_name    = "${local.function_prefix}-unregister-device-token"
  role             = aws_iam_role.unregister_device_token.arn
  handler          = "unregister_device_token.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.device_tokens.output_path
  source_code_hash = data.archive_file.device_tokens.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.device_tokens_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["unregister_device_token"]]
}

resource "aws_lambda_function" "notify_upload_complete" {
  function_name    = "${local.function_prefix}-notify-upload-complete"
  role             = aws_iam_role.notify_upload_complete.arn
  handler          = "notify_upload_complete.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = 30
  filename         = data.archive_file.push_notification.output_path
  source_code_hash = data.archive_file.push_notification.output_base64sha256
  layers           = [var.firebase_layer_arn]

  environment {
    variables = {
      TABLE_NAME                      = var.device_tokens_table_name
      FIREBASE_CREDENTIALS_SECRET_ARN = var.firebase_credentials_secret_arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["notify_upload_complete"]]
}

resource "aws_lambda_code_signing_config" "delete_user" {
  count = var.enable_code_signing ? 1 : 0

  allowed_publishers {
    signing_profile_version_arns = var.code_signing_profile_version_arns
  }

  policies {
    untrusted_artifact_on_deployment = "Enforce"
  }
}

resource "aws_lambda_function" "delete_user" {
  function_name           = "${local.function_prefix}-delete-user"
  role                    = aws_iam_role.delete_user.arn
  handler                 = "delete_user.handler"
  runtime                 = "python3.12"
  memory_size             = var.lambda_memory_size
  timeout                 = 30
  filename                = data.archive_file.users.output_path
  source_code_hash        = data.archive_file.users.output_base64sha256
  code_signing_config_arn = var.enable_code_signing ? aws_lambda_code_signing_config.delete_user[0].arn : null

  environment {
    variables = {
      S3_BUCKET_NAME            = var.s3_bucket_name
      UPLOAD_RECORDS_TABLE_NAME = var.dynamodb_table_name
      DEVICE_TOKENS_TABLE_NAME  = var.device_tokens_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["delete_user"]]
}

# ==========================================
# API Gateway REST API
# ==========================================
resource "aws_api_gateway_rest_api" "media" {
  name = "${var.project_name}-media-api-${var.env}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# /media
resource "aws_api_gateway_resource" "media" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_rest_api.media.root_resource_id
  path_part   = "media"
}

# /media/uploads
resource "aws_api_gateway_resource" "uploads" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_resource.media.id
  path_part   = "uploads"
}

# /media/uploads/{mediaId}
resource "aws_api_gateway_resource" "upload_item" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_resource.uploads.id
  path_part   = "{mediaId}"
}

# /media/uploads/complete
resource "aws_api_gateway_resource" "uploads_complete" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_resource.uploads.id
  path_part   = "complete"
}

# /devices
resource "aws_api_gateway_resource" "devices" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_rest_api.media.root_resource_id
  path_part   = "devices"
}

# /devices/token
resource "aws_api_gateway_resource" "devices_token" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_resource.devices.id
  path_part   = "token"
}

# /users
resource "aws_api_gateway_resource" "users" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  parent_id   = aws_api_gateway_rest_api.media.root_resource_id
  path_part   = "users"
}

# ==========================================
# GET /media/uploads
# ==========================================
resource "aws_api_gateway_method" "get_uploads" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads.id
  http_method   = "GET"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "get_uploads" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.uploads.id
  http_method             = aws_api_gateway_method.get_uploads.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_upload_records.invoke_arn
}

resource "aws_lambda_permission" "get_uploads" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_upload_records.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/GET/media/uploads"
}

# ==========================================
# POST /media/uploads
# ==========================================
resource "aws_api_gateway_method" "post_uploads" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "post_uploads" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.uploads.id
  http_method             = aws_api_gateway_method.post_uploads.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.create_upload_record.invoke_arn
}

resource "aws_lambda_permission" "post_uploads" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_upload_record.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/POST/media/uploads"
}

# ==========================================
# DELETE /media/uploads/{mediaId}
# ==========================================
resource "aws_api_gateway_method" "delete_upload" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.upload_item.id
  http_method   = "DELETE"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "delete_upload" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.upload_item.id
  http_method             = aws_api_gateway_method.delete_upload.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.delete_upload_record.invoke_arn
}

resource "aws_lambda_permission" "delete_upload" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_upload_record.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/DELETE/media/uploads/*"
}

# ==========================================
# CORS Preflight for /media/uploads
# ==========================================
resource "aws_api_gateway_method" "options_uploads" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_uploads" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads.id
  http_method = aws_api_gateway_method.options_uploads.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_uploads" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads.id
  http_method = aws_api_gateway_method.options_uploads.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_uploads" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads.id
  http_method = aws_api_gateway_method.options_uploads.http_method
  status_code = aws_api_gateway_method_response.options_uploads.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

# ==========================================
# CORS Preflight for /media/uploads/{mediaId}
# ==========================================
resource "aws_api_gateway_method" "options_upload_item" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.upload_item.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_upload_item" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.upload_item.id
  http_method = aws_api_gateway_method.options_upload_item.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_upload_item" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.upload_item.id
  http_method = aws_api_gateway_method.options_upload_item.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_upload_item" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.upload_item.id
  http_method = aws_api_gateway_method.options_upload_item.http_method
  status_code = aws_api_gateway_method_response.options_upload_item.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

# ==========================================
# POST /media/uploads/complete
# ==========================================
resource "aws_api_gateway_method" "post_uploads_complete" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads_complete.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "post_uploads_complete" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.uploads_complete.id
  http_method             = aws_api_gateway_method.post_uploads_complete.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.notify_upload_complete.invoke_arn
}

resource "aws_lambda_permission" "post_uploads_complete" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_upload_complete.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/POST/media/uploads/complete"
}

# ==========================================
# CORS Preflight for /media/uploads/complete
# ==========================================
resource "aws_api_gateway_method" "options_uploads_complete" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads_complete.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_uploads_complete" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads_complete.id
  http_method = aws_api_gateway_method.options_uploads_complete.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_uploads_complete" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads_complete.id
  http_method = aws_api_gateway_method.options_uploads_complete.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_uploads_complete" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.uploads_complete.id
  http_method = aws_api_gateway_method.options_uploads_complete.http_method
  status_code = aws_api_gateway_method_response.options_uploads_complete.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

# ==========================================
# PUT /devices/token
# ==========================================
resource "aws_api_gateway_method" "put_devices_token" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.devices_token.id
  http_method   = "PUT"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "put_devices_token" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.devices_token.id
  http_method             = aws_api_gateway_method.put_devices_token.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.register_device_token.invoke_arn
}

resource "aws_lambda_permission" "put_devices_token" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.register_device_token.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/PUT/devices/token"
}

# ==========================================
# DELETE /devices/token
# ==========================================
resource "aws_api_gateway_method" "delete_devices_token" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.devices_token.id
  http_method   = "DELETE"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "delete_devices_token" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.devices_token.id
  http_method             = aws_api_gateway_method.delete_devices_token.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.unregister_device_token.invoke_arn
}

resource "aws_lambda_permission" "delete_devices_token" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.unregister_device_token.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/DELETE/devices/token"
}

# ==========================================
# CORS Preflight for /devices/token
# ==========================================
resource "aws_api_gateway_method" "options_devices_token" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.devices_token.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_devices_token" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.devices_token.id
  http_method = aws_api_gateway_method.options_devices_token.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_devices_token" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.devices_token.id
  http_method = aws_api_gateway_method.options_devices_token.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_devices_token" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.devices_token.id
  http_method = aws_api_gateway_method.options_devices_token.http_method
  status_code = aws_api_gateway_method_response.options_devices_token.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
    "method.response.header.Access-Control-Allow-Methods" = "'PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

# ==========================================
# DELETE /users
# ==========================================
resource "aws_api_gateway_method" "delete_user" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.users.id
  http_method   = "DELETE"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "delete_user" {
  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = aws_api_gateway_resource.users.id
  http_method             = aws_api_gateway_method.delete_user.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.delete_user.invoke_arn
}

resource "aws_lambda_permission" "delete_user" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_user.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.media.execution_arn}/*/DELETE/users"
}

# ==========================================
# CORS Preflight for /users
# ==========================================
resource "aws_api_gateway_method" "options_users" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.users.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_users" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.options_users.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_users" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.options_users.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_users" {
  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.options_users.http_method
  status_code = aws_api_gateway_method_response.options_users.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }
}

# ==========================================
# Gateway Responses for CORS
# ==========================================
resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
  }
}

# ==========================================
# Deployment & Stage
# ==========================================
resource "aws_api_gateway_deployment" "media" {
  rest_api_id = aws_api_gateway_rest_api.media.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_method.get_uploads.id,
      aws_api_gateway_integration.get_uploads.id,
      aws_api_gateway_method.post_uploads.id,
      aws_api_gateway_integration.post_uploads.id,
      aws_api_gateway_method.delete_upload.id,
      aws_api_gateway_integration.delete_upload.id,
      aws_api_gateway_method.options_uploads.id,
      aws_api_gateway_integration.options_uploads.id,
      aws_api_gateway_method_response.options_uploads.id,
      aws_api_gateway_integration_response.options_uploads.id,
      aws_api_gateway_method.options_upload_item.id,
      aws_api_gateway_integration.options_upload_item.id,
      aws_api_gateway_method_response.options_upload_item.id,
      aws_api_gateway_integration_response.options_upload_item.id,
      aws_api_gateway_method.post_uploads_complete.id,
      aws_api_gateway_integration.post_uploads_complete.id,
      aws_api_gateway_method.options_uploads_complete.id,
      aws_api_gateway_integration.options_uploads_complete.id,
      aws_api_gateway_method_response.options_uploads_complete.id,
      aws_api_gateway_integration_response.options_uploads_complete.id,
      aws_api_gateway_method.put_devices_token.id,
      aws_api_gateway_integration.put_devices_token.id,
      aws_api_gateway_method.delete_devices_token.id,
      aws_api_gateway_integration.delete_devices_token.id,
      aws_api_gateway_method.options_devices_token.id,
      aws_api_gateway_integration.options_devices_token.id,
      aws_api_gateway_method_response.options_devices_token.id,
      aws_api_gateway_integration_response.options_devices_token.id,
      aws_api_gateway_method.delete_user.id,
      aws_api_gateway_integration.delete_user.id,
      aws_api_gateway_method.options_users.id,
      aws_api_gateway_integration.options_users.id,
      aws_api_gateway_method_response.options_users.id,
      aws_api_gateway_integration_response.options_users.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "media" {
  deployment_id = aws_api_gateway_deployment.media.id
  rest_api_id   = aws_api_gateway_rest_api.media.id
  stage_name    = var.env
}
