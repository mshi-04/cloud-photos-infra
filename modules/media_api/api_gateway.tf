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
# Business Routes
# ==========================================
locals {
  # Method and path of each business endpoint. The methods, the Lambda permissions and the
  # execution ARNs granted to the Cognito role are all derived from this one definition.
  api_routes = {
    get_uploads           = { method = "GET", path = "media/uploads" }
    post_uploads          = { method = "POST", path = "media/uploads" }
    delete_upload         = { method = "DELETE", path = "media/uploads/*" }
    post_uploads_complete = { method = "POST", path = "media/uploads/complete" }
    put_devices_token     = { method = "PUT", path = "devices/token" }
    delete_devices_token  = { method = "DELETE", path = "devices/token" }
    delete_user           = { method = "DELETE", path = "users" }
  }

  api_execution_arns = {
    for name, route in local.api_routes :
    name => "${aws_api_gateway_rest_api.media.execution_arn}/*/${route.method}/${route.path}"
  }
}

# ==========================================
# GET /media/uploads
# ==========================================
resource "aws_api_gateway_method" "get_uploads" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads.id
  http_method   = local.api_routes.get_uploads.method
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
  source_arn    = local.api_execution_arns.get_uploads
}

# ==========================================
# POST /media/uploads
# ==========================================
resource "aws_api_gateway_method" "post_uploads" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.uploads.id
  http_method   = local.api_routes.post_uploads.method
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
  source_arn    = local.api_execution_arns.post_uploads
}

# ==========================================
# DELETE /media/uploads/{mediaId}
# ==========================================
resource "aws_api_gateway_method" "delete_upload" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.upload_item.id
  http_method   = local.api_routes.delete_upload.method
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
  source_arn    = local.api_execution_arns.delete_upload
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
  http_method   = local.api_routes.post_uploads_complete.method
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
  source_arn    = local.api_execution_arns.post_uploads_complete
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
  http_method   = local.api_routes.put_devices_token.method
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
  source_arn    = local.api_execution_arns.put_devices_token
}

# ==========================================
# DELETE /devices/token
# ==========================================
resource "aws_api_gateway_method" "delete_devices_token" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = aws_api_gateway_resource.devices_token.id
  http_method   = local.api_routes.delete_devices_token.method
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
  source_arn    = local.api_execution_arns.delete_devices_token
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
  http_method   = local.api_routes.delete_user.method
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
  source_arn    = local.api_execution_arns.delete_user
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
locals {
  # The resources whose settings change how the published API behaves. Add a new method, integration,
  # response or gateway response here, so that changing it redeploys the stage.
  api_methods = {
    get_uploads              = aws_api_gateway_method.get_uploads
    post_uploads             = aws_api_gateway_method.post_uploads
    delete_upload            = aws_api_gateway_method.delete_upload
    options_uploads          = aws_api_gateway_method.options_uploads
    options_upload_item      = aws_api_gateway_method.options_upload_item
    post_uploads_complete    = aws_api_gateway_method.post_uploads_complete
    options_uploads_complete = aws_api_gateway_method.options_uploads_complete
    put_devices_token        = aws_api_gateway_method.put_devices_token
    delete_devices_token     = aws_api_gateway_method.delete_devices_token
    options_devices_token    = aws_api_gateway_method.options_devices_token
    delete_user              = aws_api_gateway_method.delete_user
    options_users            = aws_api_gateway_method.options_users
  }
  api_integrations = {
    get_uploads              = aws_api_gateway_integration.get_uploads
    post_uploads             = aws_api_gateway_integration.post_uploads
    delete_upload            = aws_api_gateway_integration.delete_upload
    options_uploads          = aws_api_gateway_integration.options_uploads
    options_upload_item      = aws_api_gateway_integration.options_upload_item
    post_uploads_complete    = aws_api_gateway_integration.post_uploads_complete
    options_uploads_complete = aws_api_gateway_integration.options_uploads_complete
    put_devices_token        = aws_api_gateway_integration.put_devices_token
    delete_devices_token     = aws_api_gateway_integration.delete_devices_token
    options_devices_token    = aws_api_gateway_integration.options_devices_token
    delete_user              = aws_api_gateway_integration.delete_user
    options_users            = aws_api_gateway_integration.options_users
  }
  api_method_responses = {
    options_uploads          = aws_api_gateway_method_response.options_uploads
    options_upload_item      = aws_api_gateway_method_response.options_upload_item
    options_uploads_complete = aws_api_gateway_method_response.options_uploads_complete
    options_devices_token    = aws_api_gateway_method_response.options_devices_token
    options_users            = aws_api_gateway_method_response.options_users
  }
  api_integration_responses = {
    options_uploads          = aws_api_gateway_integration_response.options_uploads
    options_upload_item      = aws_api_gateway_integration_response.options_upload_item
    options_uploads_complete = aws_api_gateway_integration_response.options_uploads_complete
    options_devices_token    = aws_api_gateway_integration_response.options_devices_token
    options_users            = aws_api_gateway_integration_response.options_users
  }
  api_gateway_responses = {
    default_4xx = aws_api_gateway_gateway_response.default_4xx
    default_5xx = aws_api_gateway_gateway_response.default_5xx
  }

  # The deployment is replaced when any of these values changes. The ids alone do not change when an
  # attribute such as authorization or the integration uri changes, so the attributes are included.
  # A newly set attribute that affects the published API must be added here as well.
  api_deployment_inputs = {
    methods = {
      for name, method in local.api_methods : name => {
        id            = method.id
        authorization = method.authorization
      }
    }
    integrations = {
      for name, integration in local.api_integrations : name => {
        id                      = integration.id
        type                    = integration.type
        integration_http_method = integration.integration_http_method
        uri                     = integration.uri
        request_templates       = integration.request_templates
      }
    }
    method_responses = {
      for name, response in local.api_method_responses : name => {
        id                  = response.id
        status_code         = response.status_code
        response_parameters = response.response_parameters
      }
    }
    integration_responses = {
      for name, response in local.api_integration_responses : name => {
        id                  = response.id
        status_code         = response.status_code
        response_parameters = response.response_parameters
      }
    }
    gateway_responses = {
      for name, response in local.api_gateway_responses : name => {
        response_type       = response.response_type
        response_parameters = response.response_parameters
      }
    }
  }
}

resource "aws_api_gateway_deployment" "media" {
  rest_api_id = aws_api_gateway_rest_api.media.id

  triggers = {
    cors_allow_origin = var.cors_allow_origin
    redeployment      = sha1(jsonencode(local.api_deployment_inputs))
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
