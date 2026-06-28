terraform {
  required_version = "1.15.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.32.1"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"

  default_tags {
    tags = {
      Project     = "cloud-photos"
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}

module "cognito" {
  source = "../../modules/cognito"

  env          = "dev"
  project_name = "cloud-photos"
}

module "media_storage" {
  source = "../../modules/media_storage"

  env                                = "dev"
  project_name                       = "cloud-photos"
  force_destroy                      = true
  noncurrent_version_expiration_days = 30
}

module "identity_pool" {
  source = "../../modules/identity_pool"

  env                 = "dev"
  project_name        = "cloud-photos"
  user_pool_id        = module.cognito.user_pool_id
  user_pool_client_id = module.cognito.user_pool_client_id
  media_bucket_arn    = module.media_storage.bucket_arn
  api_execution_arns  = module.media_api.api_execution_arns
}

module "media_db" {
  source = "../../modules/media_db"

  env                         = "dev"
  project_name                = "cloud-photos"
  deletion_protection_enabled = false
}

module "media_api" {
  source = "../../modules/media_api"

  env                             = "dev"
  project_name                    = "cloud-photos"
  dynamodb_table_name             = module.media_db.table_name
  dynamodb_table_arn              = module.media_db.table_arn
  device_tokens_table_name        = module.device_token_db.table_name
  device_tokens_table_arn         = module.device_token_db.table_arn
  firebase_credentials_secret_arn = module.push_notification.firebase_credentials_secret_arn
  firebase_layer_arn              = module.push_notification.firebase_layer_arn
  log_retention_in_days           = 14
  s3_bucket_name                  = module.media_storage.bucket_name
  s3_bucket_arn                   = module.media_storage.bucket_arn
  enable_code_signing             = false
  cors_allow_origin               = "*"
}

module "device_token_db" {
  source = "../../modules/device_token_db"

  env                         = "dev"
  project_name                = "cloud-photos"
  deletion_protection_enabled = false
}

module "push_notification" {
  source = "../../modules/push_notification"

  env          = "dev"
  project_name = "cloud-photos"
}