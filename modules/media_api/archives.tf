# ==========================================
# Lambda Packages
# ==========================================
# ZIPs are built by scripts/build_lambda.py into .build/ before terraform validate and plan.
locals {
  lambda_package_dir = "${path.module}/../../.build"
  lambda_packages = {
    media_uploads     = "${local.lambda_package_dir}/media_uploads.zip"
    device_tokens     = "${local.lambda_package_dir}/device_tokens.zip"
    push_notification = "${local.lambda_package_dir}/push_notification.zip"
    users             = "${local.lambda_package_dir}/users.zip"
  }
}
