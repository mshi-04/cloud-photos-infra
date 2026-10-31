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
