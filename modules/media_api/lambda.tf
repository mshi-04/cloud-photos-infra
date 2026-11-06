# ==========================================
# CloudWatch Log Groups
# ==========================================
resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambda_functions
  name              = "/aws/lambda/${local.function_prefix}-${each.value.name}"
  retention_in_days = var.log_retention_in_days
}

# ==========================================
# Lambda Functions
# ==========================================
resource "aws_lambda_code_signing_config" "delete_user" {
  count = var.enable_code_signing ? 1 : 0

  allowed_publishers {
    signing_profile_version_arns = var.code_signing_profile_version_arns
  }

  policies {
    untrusted_artifact_on_deployment = "Enforce"
  }
}

resource "aws_lambda_function" "api" {
  for_each = local.lambda_functions

  function_name           = "${local.function_prefix}-${each.value.name}"
  role                    = aws_iam_role.lambda[each.key].arn
  handler                 = each.value.handler
  runtime                 = local.lambda_runtime
  memory_size             = var.lambda_memory_size
  timeout                 = each.value.timeout
  filename                = local.lambda_packages[each.value.package]
  source_code_hash        = filebase64sha256(local.lambda_packages[each.value.package])
  layers                  = each.value.layers
  code_signing_config_arn = each.value.code_signing_config_arn

  environment {
    variables = each.value.environment
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}
