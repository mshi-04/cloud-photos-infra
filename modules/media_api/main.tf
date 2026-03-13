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
# Lambda Source Archive
# ==========================================
data "archive_file" "media_uploads" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/media_uploads"
  output_path = "${path.module}/../../.build/media_uploads.zip"
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
      Action   = ["dynamodb:DeleteItem"]
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
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
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
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# ==========================================
# Gateway Responses for CORS
# ==========================================
resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
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
      aws_api_gateway_method.get_uploads,
      aws_api_gateway_integration.get_uploads,
      aws_api_gateway_method.post_uploads,
      aws_api_gateway_integration.post_uploads,
      aws_api_gateway_method.delete_upload,
      aws_api_gateway_integration.delete_upload,
      aws_api_gateway_method.options_uploads,
      aws_api_gateway_integration.options_uploads,
      aws_api_gateway_method_response.options_uploads,
      aws_api_gateway_integration_response.options_uploads,
      aws_api_gateway_method.options_upload_item,
      aws_api_gateway_integration.options_upload_item,
      aws_api_gateway_method_response.options_upload_item,
      aws_api_gateway_integration_response.options_upload_item,
      aws_api_gateway_gateway_response.default_4xx,
      aws_api_gateway_gateway_response.default_5xx,
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
