data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  function_prefix = "${var.project_name}-${var.env}"
  lambda_functions = {
    get_upload_records      = "get-upload-records"
    create_upload_record    = "create-upload-record"
    delete_upload_record    = "delete-upload-record"
    register_device_token   = "register-device-token"
    unregister_device_token = "unregister-device-token"
    notify_upload_complete  = "notify-upload-complete"
    delete_user             = "delete-user"
  }
}
