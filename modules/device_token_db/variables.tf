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

variable "deletion_protection_enabled" {
  description = "テーブルの削除保護。各環境で明示的に指定すること（dev: false, prod: true）"
  type        = bool
}
