variable "env" {
  description = "環境名 (dev, prod など)"
  type        = string
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "cloud-photos"
}

variable "user_pool_id" {
  description = "Cognito User Pool の ID"
  type        = string
}

variable "user_pool_client_id" {
  description = "Cognito User Pool Client の ID"
  type        = string
}

variable "media_bucket_arn" {
  description = "メディアストレージバケットの ARN"
  type        = string
}

variable "api_execution_arns" {
  description = "API Gateway の実行 ARN リスト（認証済みユーザーに invoke 権限を付与）"
  type        = list(string)
}
