output "raw_bucket" {
  description = "Upload sales CSVs to s3://<this>/incoming/"
  value       = aws_s3_bucket.this["raw"].id
}

output "curated_bucket" {
  value = aws_s3_bucket.this["curated"].id
}

output "audit_table" {
  value = aws_dynamodb_table.audit.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.sales.name
}

output "dead_letter_queue_url" {
  value = aws_sqs_queue.dlq.url
}
