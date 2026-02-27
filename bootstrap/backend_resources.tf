terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"
  default_tags {
    tags = {
      Project   = "cloud-photos"
      ManagedBy = "Terraform-Bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}

# ==========================================
# S3 Bucket for Terraform State
# ==========================================
resource "aws_s3_bucket" "terraform_state" {
  # ★TODO: バケット名は世界で一意にする必要があります（アカウント名などを付与推奨）
  bucket = "mshi-04-cloud-photos-tfstate"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3バケットポリシー：Apply用ロールと管理者以外からの書き込み(Put/Delete)を拒否
resource "aws_s3_bucket_policy" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyStateWriteExceptApplyRole"
        Effect    = "Deny"
        Principal = "*"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.terraform_state.arn}/*"
        Condition = {
          StringNotLike = {
            "aws:PrincipalArn" = [
              "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/gh-terraform-apply-dev",
              "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/gh-terraform-apply-prod",
              # ★TODO: 現在このコードを実行しているユーザー/ロールのARNも追加しないと自分も書き込めなくなります
              "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/masato" 
            ]
          }
        }
      }
    ]
  })
}

# ==========================================
# DynamoDB Table for State Lock
# ==========================================
resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

output "state_bucket_name" {
  value = aws_s3_bucket.terraform_state.bucket
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.terraform_state_lock.name
}
