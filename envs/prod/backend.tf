terraform {
  backend "s3" {
    bucket         = "mshi-04-cloud-photos-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
