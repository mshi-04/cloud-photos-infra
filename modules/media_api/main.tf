locals {
  function_prefix = "${var.project_name}-${var.env}"
  lambda_runtime  = "python3.12"

  lambda_functions = {
    get_upload_records = {
      name                    = "get-upload-records"
      handler                 = "cloud_photos.media_uploads.get_upload_records.handler"
      package                 = "media_uploads"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.dynamodb_table_name })
    }
    create_upload_record = {
      name                    = "create-upload-record"
      handler                 = "cloud_photos.media_uploads.create_upload_record.handler"
      package                 = "media_uploads"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.dynamodb_table_name })
    }
    delete_upload_record = {
      name                    = "delete-upload-record"
      handler                 = "cloud_photos.media_uploads.delete_upload_record.handler"
      package                 = "media_uploads"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.dynamodb_table_name })
    }
    register_device_token = {
      name                    = "register-device-token"
      handler                 = "cloud_photos.device_tokens.register_device_token.handler"
      package                 = "device_tokens"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.device_tokens_table_name })
    }
    unregister_device_token = {
      name                    = "unregister-device-token"
      handler                 = "cloud_photos.device_tokens.unregister_device_token.handler"
      package                 = "device_tokens"
      timeout                 = var.lambda_timeout
      layers                  = null
      code_signing_config_arn = null
      environment             = tomap({ TABLE_NAME = var.device_tokens_table_name })
    }
    notify_upload_complete = {
      name                    = "notify-upload-complete"
      handler                 = "cloud_photos.push_notification.notify_upload_complete.handler"
      package                 = "push_notification"
      timeout                 = 30
      layers                  = [var.firebase_layer_arn]
      code_signing_config_arn = null
      environment = tomap({
        TABLE_NAME                      = var.device_tokens_table_name
        FIREBASE_CREDENTIALS_SECRET_ARN = var.firebase_credentials_secret_arn
      })
    }
    delete_user = {
      name                    = "delete-user"
      handler                 = "cloud_photos.users.delete_user.handler"
      package                 = "users"
      timeout                 = 30
      layers                  = null
      code_signing_config_arn = var.enable_code_signing ? aws_lambda_code_signing_config.delete_user[0].arn : null
      environment = tomap({
        S3_BUCKET_NAME            = var.s3_bucket_name
        UPLOAD_RECORDS_TABLE_NAME = var.dynamodb_table_name
        DEVICE_TOKENS_TABLE_NAME  = var.device_tokens_table_name
      })
    }
  }
}
