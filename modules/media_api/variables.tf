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
