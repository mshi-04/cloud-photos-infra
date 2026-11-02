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
      Project   = "cloud-photos"
      ManagedBy = "Terraform-Bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
