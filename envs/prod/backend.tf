terraform {
  backend "s3" {
    bucket       = "894261761443-mshi-04-cloud-photos-tfstate"
    key          = "prod/terraform.tfstate"
    region       = "ap-northeast-1"
    encrypt      = true
    use_lockfile = true
  }
}
