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
  common_sources = [
    { path = "lambda/common/__init__.py", filename = "common/__init__.py" },
    { path = "lambda/common/auth.py", filename = "common/auth.py" },
  ]
  device_tokens_sources = concat(local.common_sources, [
    { path = "lambda/device_tokens/auth.py", filename = "auth.py" },
    { path = "lambda/device_tokens/constants.py", filename = "constants.py" },
    { path = "lambda/device_tokens/db.py", filename = "db.py" },
    { path = "lambda/device_tokens/register_device_token.py", filename = "register_device_token.py" },
    { path = "lambda/device_tokens/request_utils.py", filename = "request_utils.py" },
    { path = "lambda/device_tokens/response.py", filename = "response.py" },
    { path = "lambda/device_tokens/unregister_device_token.py", filename = "unregister_device_token.py" },
  ])
  push_notification_sources = concat(local.common_sources, [
    { path = "lambda/push_notification/auth.py", filename = "auth.py" },
    { path = "lambda/push_notification/constants.py", filename = "constants.py" },
    { path = "lambda/push_notification/notify_upload_complete.py", filename = "notify_upload_complete.py" },
    { path = "lambda/push_notification/response.py", filename = "response.py" },
  ])
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
