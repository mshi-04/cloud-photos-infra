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
# Routes
# ==========================================
locals {
  cors_allow_headers = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"

  api_routes = {
    get_uploads           = { method = "GET", path = "media/uploads", resource = "uploads", function = "get_upload_records" }
    post_uploads          = { method = "POST", path = "media/uploads", resource = "uploads", function = "create_upload_record" }
    delete_upload         = { method = "DELETE", path = "media/uploads/*", resource = "upload_item", function = "delete_upload_record" }
    post_uploads_complete = { method = "POST", path = "media/uploads/complete", resource = "uploads_complete", function = "notify_upload_complete" }
    put_devices_token     = { method = "PUT", path = "devices/token", resource = "devices_token", function = "register_device_token" }
    delete_devices_token  = { method = "DELETE", path = "devices/token", resource = "devices_token", function = "unregister_device_token" }
    delete_user           = { method = "DELETE", path = "users", resource = "users", function = "delete_user" }
  }

  cors_preflights = {
    options_uploads          = { resource = "uploads", allow_methods = "GET,POST,OPTIONS" }
    options_upload_item      = { resource = "upload_item", allow_methods = "DELETE,OPTIONS" }
    options_uploads_complete = { resource = "uploads_complete", allow_methods = "POST,OPTIONS" }
    options_devices_token    = { resource = "devices_token", allow_methods = "PUT,DELETE,OPTIONS" }
    options_users            = { resource = "users", allow_methods = "DELETE,OPTIONS" }
  }

  api_resource_ids = {
    uploads          = aws_api_gateway_resource.uploads.id
    upload_item      = aws_api_gateway_resource.upload_item.id
    uploads_complete = aws_api_gateway_resource.uploads_complete.id
    devices_token    = aws_api_gateway_resource.devices_token.id
    users            = aws_api_gateway_resource.users.id
  }

  api_execution_arns = {
    for name, route in local.api_routes :
    name => "${aws_api_gateway_rest_api.media.execution_arn}/*/${route.method}/${route.path}"
  }
}

resource "aws_api_gateway_method" "route" {
  for_each = local.api_routes

  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = local.api_resource_ids[each.value.resource]
  http_method   = each.value.method
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "route" {
  for_each = local.api_routes

  rest_api_id             = aws_api_gateway_rest_api.media.id
  resource_id             = local.api_resource_ids[each.value.resource]
  http_method             = aws_api_gateway_method.route[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api[each.value.function].invoke_arn
}

resource "aws_lambda_permission" "route" {
  for_each = local.api_routes

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[each.value.function].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = local.api_execution_arns[each.key]
}

# ==========================================
# CORS Preflight
# ==========================================
resource "aws_api_gateway_method" "cors_preflight" {
  for_each = local.cors_preflights

  rest_api_id   = aws_api_gateway_rest_api.media.id
  resource_id   = local.api_resource_ids[each.value.resource]
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cors_preflight" {
  for_each = local.cors_preflights

  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = local.api_resource_ids[each.value.resource]
  http_method = aws_api_gateway_method.cors_preflight[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "cors_preflight" {
  for_each = local.cors_preflights

  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = local.api_resource_ids[each.value.resource]
  http_method = aws_api_gateway_method.cors_preflight[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "cors_preflight" {
  for_each = local.cors_preflights

  rest_api_id = aws_api_gateway_rest_api.media.id
  resource_id = local.api_resource_ids[each.value.resource]
  http_method = aws_api_gateway_method.cors_preflight[each.key].http_method
  status_code = aws_api_gateway_method_response.cors_preflight[each.key].status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = local.cors_allow_headers
    "method.response.header.Access-Control-Allow-Methods" = "'${each.value.allow_methods}'"
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
    "gatewayresponse.header.Access-Control-Allow-Headers" = local.cors_allow_headers
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.media.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = local.cors_allow_headers
  }
}

# ==========================================
# Deployment & Stage
# ==========================================
locals {
  # The resources whose settings change how the published API behaves. A route or CORS preflight added to
  # its table is included automatically; add a new gateway response here, so that changing it redeploys the stage.
  api_methods               = merge(aws_api_gateway_method.route, aws_api_gateway_method.cors_preflight)
  api_integrations          = merge(aws_api_gateway_integration.route, aws_api_gateway_integration.cors_preflight)
  api_method_responses      = aws_api_gateway_method_response.cors_preflight
  api_integration_responses = aws_api_gateway_integration_response.cors_preflight
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

    precondition {
      condition     = length(setintersection(keys(local.api_routes), keys(local.cors_preflights))) == 0
      error_message = "local.api_routes and local.cors_preflights must not share a key: merge() in local.api_methods would silently drop one of them."
    }
  }
}

resource "aws_api_gateway_stage" "media" {
  deployment_id = aws_api_gateway_deployment.media.id
  rest_api_id   = aws_api_gateway_rest_api.media.id
  stage_name    = var.env
}
