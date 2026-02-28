variable "env" {
  description = "環境名 (dev, prod など)"
  type        = string
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "cloud-photos"
}

variable "password_minimum_length" {
  description = "パスワードの最小文字数"
  type        = number
  default     = 8
  validation {
    condition     = var.password_minimum_length >= 8 && var.password_minimum_length == floor(var.password_minimum_length)
    error_message = "password_minimum_length は 8 以上の整数を指定してください。"
  }
}

variable "deletion_protection" {
  description = "リソースの削除保護を有効にするか。本番環境はACTIVE推奨"
  type        = string
  default     = "INACTIVE"
  validation {
    condition     = contains(["ACTIVE", "INACTIVE"], var.deletion_protection)
    error_message = "deletion_protection は ACTIVE または INACTIVE を指定してください。"
  }
}

variable "mfa_configuration" {
  description = "MFA configuration for the user pool"
  type        = string
  default     = "OPTIONAL"
  validation {
    condition     = contains(["ON", "OPTIONAL"], var.mfa_configuration)
    error_message = "mfa_configuration は ON または OPTIONAL を指定してください。"
  }
}