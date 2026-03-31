variable "env" {
  description = "環境名"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env は dev または prod を指定してください。"
  }
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "cloud-photos"
}

variable "dynamodb_table_name" {
  description = "DynamoDB テーブル名"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB テーブル ARN"
  type        = string
}

variable "lambda_memory_size" {
  description = "Lambda 関数のメモリサイズ (MB)"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Lambda 関数のタイムアウト (秒)"
  type        = number
  default     = 10
}

variable "log_retention_in_days" {
  description = "CloudWatch Logs の保持期間 (日)"
  type        = number
}

variable "device_tokens_table_name" {
  description = "デバイストークン DynamoDB テーブル名"
  type        = string
}

variable "device_tokens_table_arn" {
  description = "デバイストークン DynamoDB テーブル ARN"
  type        = string
}

variable "firebase_credentials_secret_arn" {
  description = "Firebase クレデンシャル Secrets Manager ARN"
  type        = string
}

variable "firebase_layer_arn" {
  description = "Firebase Admin SDK Lambda Layer ARN"
  type        = string
}

variable "s3_bucket_name" {
  description = "メディア S3 バケット名"
  type        = string
}

variable "s3_bucket_arn" {
  description = "メディア S3 バケット ARN"
  type        = string
}

variable "cors_allow_origin" {
  description = "Value for the Access-Control-Allow-Origin CORS header. Use '*' for development; restrict to a specific origin (e.g. 'https://example.com') in production."
  type        = string

  validation {
    condition     = can(regex("^(\\*|https?://[a-zA-Z0-9][a-zA-Z0-9\\-\\.]*[a-zA-Z0-9](:[0-9]{1,5})?)$", var.cors_allow_origin))
    error_message = "cors_allow_origin must be '*' or a well-formed origin (e.g. 'https://example.com' or 'http://localhost:3000')."
  }
}

variable "enable_code_signing" {
  description = "Enable Lambda code signing enforcement for the delete_user function"
  type        = bool
}

variable "code_signing_profile_version_arns" {
  description = "List of AWS Signer signing profile version ARNs allowed to sign the delete_user Lambda. Required when enable_code_signing is true."
  type        = list(string)
  default     = []

  validation {
    condition     = !var.enable_code_signing || length(var.code_signing_profile_version_arns) > 0
    error_message = "code_signing_profile_version_arns must not be empty when enable_code_signing is true."
  }
}
