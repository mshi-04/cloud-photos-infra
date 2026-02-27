variable "env" {
  description = "環境名 (dev, prod など)"
  type        = string
}

variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
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
}

variable "deletion_protection" {
  description = "リソースの削除保護を有効にするか。本番環境はACTIVE推奨"
  type        = string
  default     = "INACTIVE"
}
