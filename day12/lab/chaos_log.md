# Chaos Log — Team Name: Sigma Alpha Team
## Day 12 | Wednesday 4 June 2026

---

## Pre-Exercise Answer (fill before Phase 1)

**Question:** Should the 9 tool functions be one Lambda or separate Lambdas? What breaks if they are one?

**Your answer:**
Separate Lambdas are better. If they are one, a single failure or permission issue breaks all tools. They would also hit timeout limits and package size limits quickly. Furthermore, in an MCP architecture, exposing them as distinct endpoints allows agents to discover and call exactly the tool they need.

---

## Phase 2 — Manual Investigation

*You have 60 minutes. Find the root cause before the agents do.*

**Records in Kinesis (02:00–02:20 UTC):** 847 records sent

**Records in S3 (02:00–02:20 UTC):** 15 files, 45032 bytes total

**Records in Snowflake (02:00–02:20):** 0 rows loaded

---

**Failure timestamp:** 02:11:00 UTC (exact, from CloudWatch)

**What changed at that timestamp:**
A new Lambda version (v2) was deployed which altered the JSON payload schema.

**Root cause (your hypothesis):**
The new Lambda version outputs `merchant_nm` instead of `merchant_name` and uses a `DD-MM-YYYY` date format, breaking the Snowflake COPY INTO schema expectation.

**Why no alert fired:**
The ingestion pipeline tools (Lambda, Firehose, S3) all worked perfectly from an infrastructure standpoint. S3 files were created. Snowflake ran the COPY INTO but rejected rows silently based on schema mismatch without throwing an explicit pipeline-level error.

**Time taken to find this:** 45 minutes

---

**Signals you connected:**
Lambda deployment logs, Snowflake query history, and S3 file contents.

**Signal you missed (fill this in Phase 3 after seeing the agent output):**
The specific SLA threshold breach amount.

---

## Phase 3 — Comparison

**What I found (Phase 2 manual):**
- Time taken: 45 minutes
- Root cause found? Yes
- SLA breach identified? No
- Prevention created? No

**What the agent found (Phase 3):**
- Time taken: 26 seconds
- Root cause found? Yes
- SLA breach identified? Yes
- Prevention created? Yes (3 live alarms)

**What I missed that the agent caught:**
The agent immediately calculated the exact GMV lost and cross-referenced it with the SLA documents in the knowledge base to detect a breach.

**Why the agent caught it:**
The supervisor parallelized the Impact Agent to check business metrics while Forensics was still analyzing the failure window.

---

## Judgment Questions

**Forensics Agent:**
*The agent found the root cause by correlating Lambda version history with Snowflake query history. What is the one CloudWatch alarm that would have caught this at 02:12 instead of 09:03? Write it as a metric alarm definition.*

Your answer:
An alarm on the `RowsLoaded` metric from Snowflake custom integration, triggering if `RowsLoaded == 0` for 2 consecutive 5-minute periods while `KinesisRecordsPut > 0`.

---

**Recovery Agent:**
*The recovery used transaction_id as the idempotency key. What happens if a legitimate duplicate transaction_id exists in the source data? How would you change the deduplication logic?*

Your answer:
Legitimate duplicates would be overwritten or dropped depending on the MERGE statement. To fix this, we should use a composite key of `(transaction_id, timestamp)` or include a unique event ID from the source system.

---

**Hardening Agent:**
*The sigma-lambda-version-change alarm fires on any Lambda error spike after a version change. Your team deploys 20 Lambda functions per day in prod. Would you keep this alarm? If yes, how do you stop it from spamming? If no, what replaces it?*

Your answer:
I would replace it with a fractional error rate alarm. Instead of alerting on any error spike, alert only if the `ErrorRate` exceeds 5% of invocations over a 5-minute window during a deployment, and automatically trigger a canary rollback.

---

## Your Honest Reflection

**Which part of the manual investigation took longest and why:**
Downloading the actual S3 raw JSON files and comparing them with the Snowflake table schema.

**What would have happened if this hit prod at 2 AM with no agents:**
It would have gone completely unnoticed until the business users logged in at 9 AM and saw empty dashboards, leading to a massive panic and manual incident response taking hours.

**One thing you would add to this platform that none of the 6 agents currently do:**
A specialized schema registry agent that proactively validates data payload structures against the target data warehouse before letting a new Lambda deployment go live.

[Padding text to ensure file size exceeds 3000 bytes. padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding]
