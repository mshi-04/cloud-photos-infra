data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  function_prefix = "${var.project_name}-${var.env}"
  lambda_functions = {
    get_upload_records   = "get-upload-records"
    create_upload_record = "create-upload-record"
    delete_upload_record = "delete-upload-record"
  }
}

# ==========================================
# Lambda Source Archives
# ==========================================
data "archive_file" "get_upload_records" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/media_uploads/get_upload_records.py"
  output_path = "${path.module}/../../.build/get_upload_records.zip"
}

data "archive_file" "create_upload_record" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/media_uploads/create_upload_record.py"
  output_path = "${path.module}/../../.build/create_upload_record.zip"
}

data "archive_file" "delete_upload_record" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/media_uploads/delete_upload_record.py"
  output_path = "${path.module}/../../.build/delete_upload_record.zip"
}

# ==========================================
# IAM Role for Lambda
# ==========================================
resource "aws_iam_role" "lambda" {
  name = "${local.function_prefix}-media-api-lambda"

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

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "dynamodb-access"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowDynamoDBAccess"
      Effect = "Allow"
      Action = [
        "dynamodb:Query",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchLogsWrite"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [for k, _ in local.lambda_functions : "${aws_cloudwatch_log_group.lambda[k].arn}:*"]
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
  role             = aws_iam_role.lambda.arn
  handler          = "get_upload_records.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.get_upload_records.output_path
  source_code_hash = data.archive_file.get_upload_records.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["get_upload_records"]]
}

resource "aws_lambda_function" "create_upload_record" {
  function_name    = "${local.function_prefix}-create-upload-record"
  role             = aws_iam_role.lambda.arn
  handler          = "create_upload_record.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.create_upload_record.output_path
  source_code_hash = data.archive_file.create_upload_record.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["create_upload_record"]]
}

resource "aws_lambda_function" "delete_upload_record" {
  function_name    = "${local.function_prefix}-delete-upload-record"
  role             = aws_iam_role.lambda.arn
  handler          = "delete_upload_record.handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  filename         = data.archive_file.delete_upload_record.output_path
  source_code_hash = data.archive_file.delete_upload_record.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.dynamodb_table_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda["delete_upload_record"]]
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
# Deployment & Stage
# ==========================================
resource "aws_api_gateway_deployment" "media" {
  rest_api_id = aws_api_gateway_rest_api.media.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_method.get_uploads,
      aws_api_gateway_integration.get_uploads,
      aws_api_gateway_method.post_uploads,
      aws_api_gateway_integration.post_uploads,
      aws_api_gateway_method.delete_upload,
      aws_api_gateway_integration.delete_upload,
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
