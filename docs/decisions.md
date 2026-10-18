# Design decisions and trade-offs

Each decision lists what was chosen, what was rejected, and why.

## 1. SQS between S3 and Lambda, not a direct S3 trigger

S3 can invoke Lambda directly, and that would be simpler. With a direct trigger, though, failed invocations retry twice and are then lost unless a separate failure destination is set up. With SQS in the middle, every file is a message: failures retry, a file that keeps failing moves to a dead-letter queue that someone is alerted about, and a burst of uploads is smoothed out. The cost is one more component, and it is free at this volume.

## 2. Validation logic separated from AWS code

`rules.py` is pure Python with no AWS imports, so every rule is unit tested on a laptop in milliseconds. `handler.py` only moves data between services. This makes the rules easy to change, review and explain to a business owner.

## 3. Reject rows, not files

One bad row should not block a branch's other 499 sales. Rows are rejected individually with every reason that applies, so a branch fixes everything in one pass. A file is rejected as a whole only when it is structurally wrong, for example a missing column.

## 4. Idempotency with a DynamoDB conditional write

The audit item's key is the S3 key plus the object's ETag, and it is written with `attribute_not_exists`. If S3 or SQS delivers the same event twice, the second write fails and the file is skipped, so sales are never double-counted. If processing crashes, the claim is released so the retry can run. One write gives both the duplicate guard and the audit trail.

## 5. JSON Lines (gzip) rather than Parquet

Parquet is faster and smaller for large analytics workloads, but writing it from Lambda needs the `pyarrow` library, which is around 100 MB and needs a Lambda layer. At weekly branch volumes, gzip JSON Lines is small, readable by Athena, and keeps the function to the standard library plus boto3. **Revisit** if volumes reach millions of rows per day.

## 6. Partition projection rather than Glue crawlers

Crawlers are billed per run and add a delay before new data is visible. Partition projection tells Athena the `dt=` layout up front, so new days are queryable immediately and at no cost.

## 7. Zero-cost guardrails

- **SSE-S3 and AWS-managed keys rather than customer-managed KMS keys.** Each customer-managed key has a monthly charge. Data is still encrypted at rest.
- No VPC for Lambda. The function only talks to AWS public endpoints. Putting it in a VPC would need a NAT gateway or VPC endpoints, which are billed by the hour, for no security gain here.
- **14-day log retention, 30-day raw file expiry, 7-day query result expiry.**
- **Athena per-query scan cap of 10 MB** (the minimum), so a careless query cannot run up a bill.
- **SQS maximum concurrency of 2** on the Lambda trigger, so a flood of files cannot use up the account's concurrency.
- **Budget alert at 1% of a $1 budget**, which in practice means any spend at all.

In a client environment with a real budget, the customer-managed keys, point-in-time recovery and longer log retention would be switched on. The Checkov exceptions in `.checkov.yml` mark exactly where.

## 8. OIDC rather than access keys for CI/CD

GitHub Actions requests a short-lived token, and AWS only accepts it for this repository's `main` branch and pull requests. There is no secret to leak or rotate. The deploy role uses a broad managed policy because this is a single-purpose demo account. In a shared account it would be scoped to the services this stack uses.

## 9. S3-native state locking

Terraform 1.10+ can lock state with a lock file in the S3 bucket itself (`use_lockfile`), so the usual DynamoDB lock table is not needed.

## 10. Build versus buy

AWS Glue jobs or a managed ETL tool could do this. For a handful of files a week, they add cost and moving parts. A ~150-line Lambda function is cheaper, testable and easy to hand over. If transformations grow complex or volumes grow large, Glue (Spark) or Step Functions orchestration would be the next step.
