# Voiceover script

Read at a relaxed pace, about 2.5 words a second. Each line fits its scene, and the
timestamps are where each scene starts in `out/pipeline-linkedin.mp4`. Short pauses
between scenes are fine: the captions carry the story if the video plays muted.

| Time | Scene | Say |
|---|---|---|
| 0:00 | The problem | "A retailer's branches send in weekly sales as spreadsheets. Someone merges them by hand, and mistakes only show up after the report has gone out." |
| 0:08 | What we built | "So I built a serverless pipeline on AWS that does it automatically. Every piece is defined in Terraform." |
| 0:14 | 1. File lands in S3 | "A branch uploads its sales file to an S3 bucket. That's the only thing they have to do." |
| 0:22 | 2. Queued in SQS | "S3 drops a message on a queue, which absorbs bursts and retries failures. No file gets lost." |
| 0:29 | 3. Lambda checks every row | "A Lambda function checks every row: valid date, known branch, proper product code, sensible numbers, no duplicates. In this file, five rows pass and five fail, and each failure says exactly why." |
| 0:42 | 4. Saved and audited | "Clean rows and rejected rows go to S3, partitioned by day. And every file gets one audit record in DynamoDB." |
| 0:50 | 4. Duplicates ignored | "If the same file arrives twice, it's skipped. Sales are never counted twice." |
| 0:56 | 5. Query with SQL | "Analysts query the clean data with plain SQL in Athena. No database server to run." |
| 1:02 | 6. Failures reach a person | "A file that keeps failing is retried three times, then parked in a dead-letter queue. An alarm emails a person." |
| 1:11 | How it ships | "Every change runs through GitHub Actions: tests, a security scan, then deploy. No stored AWS keys." |
| 1:18 | Close | "It all runs for zero dollars. The code, diagrams and runbook are on my GitHub." |

## Recording tips

- Record in a quiet room with soft furnishings; a phone held 15 to 20 cm away works.
- Record each line as a separate take so a slip only costs one line.
- Drop the takes onto the video in CapCut, iMovie or DaVinci Resolve (all free), lining each one up with its timestamp.
- Export at 1080 x 1350, H.264.
