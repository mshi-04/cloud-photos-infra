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
    condition     = var.password_minimum_length >= 8 && var.password_minimum_length <= 99
    error_message = "password_minimum_length は 8 から 99 までの値を指定してください。"
  }
  validation {
    condition     = var.password_minimum_length == floor(var.password_minimum_length)
    error_message = "password_minimum_length は整数を指定してください。"
  }
}

variable "temporary_password_validity_days" {
  description = "一時パスワードの有効期間（日数）"
  type        = number
  default     = 7
  validation {
    condition     = var.temporary_password_validity_days >= 1 && var.temporary_password_validity_days <= 365
    error_message = "temporary_password_validity_days は 1 から 365 までの値を指定してください。"
  }
  validation {
    condition     = var.temporary_password_validity_days == floor(var.temporary_password_validity_days)
    error_message = "temporary_password_validity_days は整数を指定してください。"
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
