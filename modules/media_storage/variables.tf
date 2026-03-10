variable "env" {
  description = "環境名 (dev, prod など)"
  type        = string
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "cloud-photos"
}

variable "force_destroy" {
  description = "バケット削除時にオブジェクトも強制削除するか。各環境で明示的に指定すること（dev: true, prod: false）"
  type        = bool
}

variable "noncurrent_version_expiration_days" {
  description = "旧バージョンの有効期限（日数）"
  type        = number
  default     = 30
  validation {
    condition     = var.noncurrent_version_expiration_days >= 1 && var.noncurrent_version_expiration_days <= 365
    error_message = "noncurrent_version_expiration_days は 1 から 365 までの値を指定してください。"
  }
  validation {
    condition     = var.noncurrent_version_expiration_days == floor(var.noncurrent_version_expiration_days)
    error_message = "noncurrent_version_expiration_days は整数を指定してください。"
  }
}
