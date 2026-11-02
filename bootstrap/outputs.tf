output "state_bucket_name" {
  description = "Terraform state を置く S3 バケット名"
  value       = aws_s3_bucket.terraform_state.bucket
}
