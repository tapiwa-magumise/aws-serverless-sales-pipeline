data "aws_caller_identity" "me" {}

locals {
  suffix = "${data.aws_caller_identity.me.account_id}-${var.region}"
  buckets = {
    raw     = "${var.name}-raw-${local.suffix}"     # files land here
    curated = "${var.name}-curated-${local.suffix}" # validated output, queried by Athena
    results = "${var.name}-athena-${local.suffix}"  # Athena query results
  }
}

resource "aws_s3_bucket" "this" {
  for_each      = local.buckets
  bucket        = each.value
  force_destroy = true # demo stack: lets `terraform destroy` remove data too
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each                = aws_s3_bucket.this
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  rule {
    # SSE-S3 rather than a customer-managed KMS key: no monthly key charge.
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# Refuse any request that is not over TLS.
data "aws_iam_policy_document" "tls_only" {
  for_each = aws_s3_bucket.this
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      each.value.arn,
      "${each.value.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  for_each   = aws_s3_bucket.this
  bucket     = each.value.id
  policy     = data.aws_iam_policy_document.tls_only[each.key].json
  depends_on = [aws_s3_bucket_public_access_block.this]
}

# Keep storage near zero: raw files and query results expire.
resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.this["raw"].id
  rule {
    id     = "expire-raw-files"
    status = "Enabled"
    filter { prefix = "incoming/" }
    expiration { days = 30 }
  }
  rule {
    id     = "abort-failed-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "curated" {
  bucket = aws_s3_bucket.this["curated"].id
  rule {
    id     = "abort-failed-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "results" {
  bucket = aws_s3_bucket.this["results"].id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

# ---------- Load audit ----------
# One item per file: status, rows loaded, rows rejected, timings.
# The conditional write on file_id also makes processing idempotent.
resource "aws_dynamodb_table" "audit" {
  name         = "${var.name}-load-audit"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  point_in_time_recovery { enabled = false } # PITR is billed; audit can be rebuilt from S3
}
