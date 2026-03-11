output "bucket_name" {
  description = "Media storage bucket name"
  value       = aws_s3_bucket.media.bucket
}

output "bucket_arn" {
  description = "Media storage bucket ARN"
  value       = aws_s3_bucket.media.arn
}
