terraform {
  backend "s3" {
    bucket         = "894261761443-mshi-04-cloud-photos-tfstate"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
