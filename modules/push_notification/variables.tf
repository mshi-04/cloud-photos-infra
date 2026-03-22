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

variable "firebase_layer_zip_path" {
  description = "firebase-admin Lambda Layer の ZIP ファイルパス"
  type        = string
}
