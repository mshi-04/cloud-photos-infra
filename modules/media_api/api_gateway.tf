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
    cors_allow_origin = var.cors_allow_origin
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
