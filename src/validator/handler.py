"""Lambda entry point.

Triggered by SQS, which receives S3 "object created" events for files under incoming/.
For each file: skip it if already processed, validate rows, write loaded and rejected
rows to the curated bucket, and record the outcome in the DynamoDB load audit table.
"""

import gzip
import json
import logging
import os
import urllib.parse
from datetime import date, datetime, timezone

import boto3
from botocore.exceptions import ClientError

from rules import validate

log = logging.getLogger()
log.setLevel(logging.INFO)

s3 = boto3.client("s3")
audit = boto3.resource("dynamodb").Table(os.environ["AUDIT_TABLE"])

CURATED_BUCKET = os.environ["CURATED_BUCKET"]
BRANCHES = set(os.environ["BRANCHES"].split(","))


def _write_jsonl(key: str, rows: list) -> None:
    body = gzip.compress("\n".join(json.dumps(r) for r in rows).encode())
    s3.put_object(Bucket=CURATED_BUCKET, Key=key, Body=body, ContentEncoding="gzip")


def _claim(file_id: str, bucket: str, key: str) -> bool:
    """Record the file as processing. Returns False if it was seen before (idempotency)."""
    try:
        audit.put_item(
            Item={
                "file_id": file_id,
                "source": f"s3://{bucket}/{key}",
                "status": "PROCESSING",
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            ConditionExpression="attribute_not_exists(file_id)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def process_file(bucket: str, key: str, etag: str) -> dict:
    file_id = f"{key}#{etag}"
    if not _claim(file_id, bucket, key):
        log.info(json.dumps({"event": "skipped_duplicate", "file_id": file_id}))
        return {"file_id": file_id, "status": "SKIPPED_DUPLICATE"}

    try:
        return _load(bucket, key, file_id)
    except Exception:
        # Release the claim so the SQS retry can process the file again.
        audit.delete_item(Key={"file_id": file_id})
        raise


def _load(bucket: str, key: str, file_id: str) -> dict:
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8-sig")
    result = validate(body, BRANCHES, date.today())

    name = key.rsplit("/", 1)[-1].removesuffix(".csv")
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if result.file_error:
        status = "FAILED"
    else:
        if result.loaded:
            _write_jsonl(f"sales/dt={dt}/{name}.jsonl.gz", result.loaded)
        if result.rejected:
            _write_jsonl(f"rejected/dt={dt}/{name}.jsonl.gz", result.rejected)
        status = "LOADED_WITH_REJECTS" if result.rejected else "LOADED"

    summary = {
        "file_id": file_id,
        "status": status,
        "rows_loaded": len(result.loaded),
        "rows_rejected": len(result.rejected),
        "file_error": result.file_error,
    }
    audit.update_item(
        Key={"file_id": file_id},
        UpdateExpression="SET #s=:s, rows_loaded=:l, rows_rejected=:r, file_error=:e, finished_at=:f",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": status,
            ":l": summary["rows_loaded"],
            ":r": summary["rows_rejected"],
            ":e": result.file_error,
            ":f": datetime.now(timezone.utc).isoformat(),
        },
    )
    log.info(json.dumps({"event": "file_processed", **summary}))
    return summary


def handler(event, context):
    """Process each SQS message. Failed messages are reported back so only they retry."""
    failures = []
    for message in event["Records"]:
        try:
            s3_event = json.loads(message["body"])
            for record in s3_event.get("Records", []):  # S3 sends a test event with no Records
                bucket = record["s3"]["bucket"]["name"]
                key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
                process_file(bucket, key, record["s3"]["object"]["eTag"])
        except Exception:
            log.exception("failed to process message %s", message["messageId"])
            failures.append({"itemIdentifier": message["messageId"]})
    return {"batchItemFailures": failures}
