moved {
  from = aws_lambda_function.get_upload_records
  to   = aws_lambda_function.api["get_upload_records"]
}

moved {
  from = aws_iam_role.get_upload_records
  to   = aws_iam_role.lambda["get_upload_records"]
}

moved {
  from = aws_iam_role_policy.get_upload_records_logs
  to   = aws_iam_role_policy.logs["get_upload_records"]
}

moved {
  from = aws_lambda_function.create_upload_record
  to   = aws_lambda_function.api["create_upload_record"]
}

moved {
  from = aws_iam_role.create_upload_record
  to   = aws_iam_role.lambda["create_upload_record"]
}

moved {
  from = aws_iam_role_policy.create_upload_record_logs
  to   = aws_iam_role_policy.logs["create_upload_record"]
}

moved {
  from = aws_lambda_function.delete_upload_record
  to   = aws_lambda_function.api["delete_upload_record"]
}

moved {
  from = aws_iam_role.delete_upload_record
  to   = aws_iam_role.lambda["delete_upload_record"]
}

moved {
  from = aws_iam_role_policy.delete_upload_record_logs
  to   = aws_iam_role_policy.logs["delete_upload_record"]
}

moved {
  from = aws_lambda_function.register_device_token
  to   = aws_lambda_function.api["register_device_token"]
}

moved {
  from = aws_iam_role.register_device_token
  to   = aws_iam_role.lambda["register_device_token"]
}

moved {
  from = aws_iam_role_policy.register_device_token_logs
  to   = aws_iam_role_policy.logs["register_device_token"]
}

moved {
  from = aws_lambda_function.unregister_device_token
  to   = aws_lambda_function.api["unregister_device_token"]
}

moved {
  from = aws_iam_role.unregister_device_token
  to   = aws_iam_role.lambda["unregister_device_token"]
}

moved {
  from = aws_iam_role_policy.unregister_device_token_logs
  to   = aws_iam_role_policy.logs["unregister_device_token"]
}

moved {
  from = aws_lambda_function.notify_upload_complete
  to   = aws_lambda_function.api["notify_upload_complete"]
}

moved {
  from = aws_iam_role.notify_upload_complete
  to   = aws_iam_role.lambda["notify_upload_complete"]
}

moved {
  from = aws_iam_role_policy.notify_upload_complete_logs
  to   = aws_iam_role_policy.logs["notify_upload_complete"]
}

moved {
  from = aws_lambda_function.delete_user
  to   = aws_lambda_function.api["delete_user"]
}

moved {
  from = aws_iam_role.delete_user
  to   = aws_iam_role.lambda["delete_user"]
}

moved {
  from = aws_iam_role_policy.delete_user_logs
  to   = aws_iam_role_policy.logs["delete_user"]
}

moved {
  from = aws_api_gateway_method.get_uploads
  to   = aws_api_gateway_method.route["get_uploads"]
}

moved {
  from = aws_api_gateway_integration.get_uploads
  to   = aws_api_gateway_integration.route["get_uploads"]
}

moved {
  from = aws_lambda_permission.get_uploads
  to   = aws_lambda_permission.route["get_uploads"]
}

moved {
  from = aws_api_gateway_method.post_uploads
  to   = aws_api_gateway_method.route["post_uploads"]
}

moved {
  from = aws_api_gateway_integration.post_uploads
  to   = aws_api_gateway_integration.route["post_uploads"]
}

moved {
  from = aws_lambda_permission.post_uploads
  to   = aws_lambda_permission.route["post_uploads"]
}

moved {
  from = aws_api_gateway_method.delete_upload
  to   = aws_api_gateway_method.route["delete_upload"]
}

moved {
  from = aws_api_gateway_integration.delete_upload
  to   = aws_api_gateway_integration.route["delete_upload"]
}

moved {
  from = aws_lambda_permission.delete_upload
  to   = aws_lambda_permission.route["delete_upload"]
}

moved {
  from = aws_api_gateway_method.post_uploads_complete
  to   = aws_api_gateway_method.route["post_uploads_complete"]
}

moved {
  from = aws_api_gateway_integration.post_uploads_complete
  to   = aws_api_gateway_integration.route["post_uploads_complete"]
}

moved {
  from = aws_lambda_permission.post_uploads_complete
  to   = aws_lambda_permission.route["post_uploads_complete"]
}

moved {
  from = aws_api_gateway_method.put_devices_token
  to   = aws_api_gateway_method.route["put_devices_token"]
}

moved {
  from = aws_api_gateway_integration.put_devices_token
  to   = aws_api_gateway_integration.route["put_devices_token"]
}

moved {
  from = aws_lambda_permission.put_devices_token
  to   = aws_lambda_permission.route["put_devices_token"]
}

moved {
  from = aws_api_gateway_method.delete_devices_token
  to   = aws_api_gateway_method.route["delete_devices_token"]
}

moved {
  from = aws_api_gateway_integration.delete_devices_token
  to   = aws_api_gateway_integration.route["delete_devices_token"]
}

moved {
  from = aws_lambda_permission.delete_devices_token
  to   = aws_lambda_permission.route["delete_devices_token"]
}

moved {
  from = aws_api_gateway_method.delete_user
  to   = aws_api_gateway_method.route["delete_user"]
}

moved {
  from = aws_api_gateway_integration.delete_user
  to   = aws_api_gateway_integration.route["delete_user"]
}

moved {
  from = aws_lambda_permission.delete_user
  to   = aws_lambda_permission.route["delete_user"]
}

moved {
  from = aws_api_gateway_method.options_uploads
  to   = aws_api_gateway_method.cors_preflight["options_uploads"]
}

moved {
  from = aws_api_gateway_integration.options_uploads
  to   = aws_api_gateway_integration.cors_preflight["options_uploads"]
}

moved {
  from = aws_api_gateway_method_response.options_uploads
  to   = aws_api_gateway_method_response.cors_preflight["options_uploads"]
}

moved {
  from = aws_api_gateway_integration_response.options_uploads
  to   = aws_api_gateway_integration_response.cors_preflight["options_uploads"]
}

moved {
  from = aws_api_gateway_method.options_upload_item
  to   = aws_api_gateway_method.cors_preflight["options_upload_item"]
}

moved {
  from = aws_api_gateway_integration.options_upload_item
  to   = aws_api_gateway_integration.cors_preflight["options_upload_item"]
}

moved {
  from = aws_api_gateway_method_response.options_upload_item
  to   = aws_api_gateway_method_response.cors_preflight["options_upload_item"]
}

moved {
  from = aws_api_gateway_integration_response.options_upload_item
  to   = aws_api_gateway_integration_response.cors_preflight["options_upload_item"]
}

moved {
  from = aws_api_gateway_method.options_uploads_complete
  to   = aws_api_gateway_method.cors_preflight["options_uploads_complete"]
}

moved {
  from = aws_api_gateway_integration.options_uploads_complete
  to   = aws_api_gateway_integration.cors_preflight["options_uploads_complete"]
}

moved {
  from = aws_api_gateway_method_response.options_uploads_complete
  to   = aws_api_gateway_method_response.cors_preflight["options_uploads_complete"]
}

moved {
  from = aws_api_gateway_integration_response.options_uploads_complete
  to   = aws_api_gateway_integration_response.cors_preflight["options_uploads_complete"]
}

moved {
  from = aws_api_gateway_method.options_devices_token
  to   = aws_api_gateway_method.cors_preflight["options_devices_token"]
}

moved {
  from = aws_api_gateway_integration.options_devices_token
  to   = aws_api_gateway_integration.cors_preflight["options_devices_token"]
}

moved {
  from = aws_api_gateway_method_response.options_devices_token
  to   = aws_api_gateway_method_response.cors_preflight["options_devices_token"]
}

moved {
  from = aws_api_gateway_integration_response.options_devices_token
  to   = aws_api_gateway_integration_response.cors_preflight["options_devices_token"]
}

moved {
  from = aws_api_gateway_method.options_users
  to   = aws_api_gateway_method.cors_preflight["options_users"]
}

moved {
  from = aws_api_gateway_integration.options_users
  to   = aws_api_gateway_integration.cors_preflight["options_users"]
}

moved {
  from = aws_api_gateway_method_response.options_users
  to   = aws_api_gateway_method_response.cors_preflight["options_users"]
}

moved {
  from = aws_api_gateway_integration_response.options_users
  to   = aws_api_gateway_integration_response.cors_preflight["options_users"]
}
