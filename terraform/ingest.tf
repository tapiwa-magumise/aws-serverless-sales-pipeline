# S3 (incoming/*.csv) -> SQS -> Lambda validator -> S3 curated + DynamoDB audit
# SQS sits between S3 and Lambda so bursts are buffered, failures retry,
# and files that keep failing land in a dead-letter queue instead of vanishing.

# ---------- Queues ----------
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-files-dlq"
  message_retention_seconds = 1209600 # 14 days to investigate
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "files" {
  name                       = "${var.name}-files"
  visibility_timeout_seconds = 360 # 6x the Lambda timeout, as AWS recommends
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

data "aws_iam_policy_document" "s3_to_sqs" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.files.arn]
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.this["raw"].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

resource "aws_sqs_queue_policy" "files" {
  queue_url = aws_sqs_queue.files.id
  policy    = data.aws_iam_policy_document.s3_to_sqs.json
}

resource "aws_s3_bucket_notification" "raw" {
  bucket = aws_s3_bucket.this["raw"].id
  queue {
    queue_arn     = aws_sqs_queue.files.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "incoming/"
    filter_suffix = ".csv"
  }
  depends_on = [aws_sqs_queue_policy.files]
}

# ---------- Lambda ----------
data "archive_file" "validator" {
  type        = "zip"
  source_dir  = "${path.module}/../src/validator"
  output_path = "${path.module}/.build/validator.zip"
  excludes    = ["__pycache__"]
}

resource "aws_cloudwatch_log_group" "validator" {
  name              = "/aws/lambda/${var.name}-validator"
  retention_in_days = 14
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Least privilege: read raw, write curated, use its own queue, table and log group.
data "aws_iam_policy_document" "validator" {
  statement {
    sid       = "ReadRaw"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this["raw"].arn}/incoming/*"]
  }
  statement {
    sid       = "WriteCurated"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this["curated"].arn}/*"]
  }
  statement {
    sid       = "AuditTable"
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.audit.arn]
  }
  statement {
    sid       = "ConsumeQueue"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.files.arn]
  }
  statement {
    sid       = "Tracing"
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
    resources = ["*"] # X-Ray does not support resource-level permissions
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.validator.arn}:*"]
  }
}

resource "aws_iam_role" "validator" {
  name               = "${var.name}-validator"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy" "validator" {
  name   = "validator"
  role   = aws_iam_role.validator.id
  policy = data.aws_iam_policy_document.validator.json
}

resource "aws_lambda_function" "validator" {
  function_name    = "${var.name}-validator"
  role             = aws_iam_role.validator.arn
  runtime          = "python3.13"
  architectures    = ["arm64"] # Graviton: cheaper per GB-second than x86
  handler          = "handler.handler"
  filename         = data.archive_file.validator.output_path
  source_code_hash = data.archive_file.validator.output_base64sha256
  memory_size      = 256
  timeout          = 60

  tracing_config { mode = "Active" } # X-Ray traces each run

  environment {
    variables = {
      CURATED_BUCKET = aws_s3_bucket.this["curated"].id
      AUDIT_TABLE    = aws_dynamodb_table.audit.name
      BRANCHES       = join(",", var.branches)
    }
  }

  depends_on = [aws_cloudwatch_log_group.validator]
}

resource "aws_lambda_event_source_mapping" "files" {
  event_source_arn        = aws_sqs_queue.files.arn
  function_name           = aws_lambda_function.validator.arn
  batch_size              = 5
  function_response_types = ["ReportBatchItemFailures"] # retry only the failed files

  # Cap how many copies run at once, so a flood of files cannot exhaust account concurrency.
  scaling_config { maximum_concurrency = 2 }
}
