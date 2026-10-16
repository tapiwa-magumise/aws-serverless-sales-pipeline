# Runbook

## Alert: "ssp-file-in-dead-letter-queue"

A file failed processing three times and was moved to the dead-letter queue.

1. Find the error in the logs:
   ```bash
   aws logs tail /aws/lambda/ssp-validator --since 1h --filter-pattern ERROR
   ```
2. Look at the stuck message to see which file it was:
   ```bash
   aws sqs receive-message --queue-url "$(terraform -chdir=terraform output -raw dead_letter_queue_url)"
   ```
3. Fix the cause (code bug, permissions, a corrupt file).
4. Send the messages back for processing:
   ```bash
   aws sqs start-message-move-task --source-arn <dlq arn>
   ```
   Files are idempotent, so reprocessing never double-counts.

## Alert: "ssp-validator-errors"

The Lambda raised an exception. Follow steps 1 and 3 above. If the error repeats three times for one file, the dead-letter queue alarm will follow.

## A branch says their file "did nothing"

1. Check the audit record:
   ```bash
   aws dynamodb scan --table-name ssp-load-audit \
     --filter-expression "contains(#s, :f)" \
     --expression-attribute-names '{"#s":"source"}' \
     --expression-attribute-values '{":f":{"S":"<file name>"}}'
   ```
2. Read the status:
   - `LOADED`: all rows loaded.
   - `LOADED_WITH_REJECTS`: run the `rejection-reasons` query in Athena and send the branch the rejected rows.
   - `FAILED`: the file was structurally wrong. `file_error` says why, for example a missing column.
   - No record: the file was not under `incoming/`, or did not end in `.csv`.

## Re-sending a corrected file

Upload it under a new name, or overwrite the old one. Overwriting changes the ETag, so it is treated as a new file.

## Budget alert

Any spend triggers it. Check the Billing console's cost breakdown by service. The usual causes are Athena queries over a lot of data or a forgotten resource outside this stack.

## Adding a branch

Add the code to `branches` in `terraform/variables.tf` and merge. The pipeline redeploys the Lambda with the new list.
