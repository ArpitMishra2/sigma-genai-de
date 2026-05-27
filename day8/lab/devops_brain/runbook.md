# Pipeline Overview

This pipeline ingests transaction data, transforms it, and loads it into bronze, silver, and gold tables. It runs to ensure data is available for downstream analytics and reporting. If it stops, critical business metrics and reports will be unavailable.

## Pipeline Steps

1. Connect to the DuckDB database using `get_connection()`.
2. Set up necessary tables using `setup_tables(con)`.
3. Load merchant data into the `merchants` table using `load_merchants(con)`.
4. Load transactions into the `bronze_transactions` table using `load_bronze(con, transactions)`.
5. Transform bronze transactions to silver using `transform_bronze_to_silver(transactions, merchants)`.
6. Load transformed data into the `silver_transactions` table using `load_silver(con, silver_rows)`.
7. Compute merchant performance metrics using `compute_merchant_performance(silver_rows)`.
8. Compute daily summary metrics using `compute_daily_summary(silver_rows)`.
9. Load merchant performance and daily summary into gold tables using `load_gold(con, merchant_perf, daily_summary)`.

## Schedule / Trigger

This pipeline runs every night at 2 AM UTC via a cron job.

## Failure Modes

1. **DuckDB Connection Failure**
   - **Root Cause:** Database is down or unreachable.
   - **Symptom:** `get_connection()` fails.
2. **Table Creation Error**
   - **Root Cause:** SQL syntax error or permission issue.
   - **Symptom:** `setup_tables(con)` throws an exception.
3. **Merchant Data Load Failure**
   - **Root Cause:** Corrupt or missing merchant data.
   - **Symptom:** `load_merchants(con)` fails.
4. **Bronze Table Load Failure**
   - **Root Cause:** Invalid transaction data.
   - **Symptom:** `load_bronze(con, transactions)` fails.
5. **Silver Table Transformation Failure**
   - **Root Cause:** Logic error in `transform_bronze_to_silver()`.
   - **Symptom:** `load_silver(con, silver_rows)` fails.

## Recovery Actions

1. **DuckDB Connection Failure**
   - Check database server status.
   - Restart the database if necessary.
   - Retry the pipeline.
2. **Table Creation Error**
   - Review SQL statements for errors.
   - Fix syntax or permission issues.
   - Rerun `setup_tables(con)`.
3. **Merchant Data Load Failure**
   - Verify merchant data integrity.
   - Correct or replace corrupt data.
   - Retry `load_merchants(con)`.
4. **Bronze Table Load Failure**
   - Inspect transaction data for issues.
   - Clean or correct invalid data.
   - Retry `load_bronze(con, transactions)`.
5. **Silver Table Transformation Failure**
   - Debug `transform_bronze_to_silver()` logic.
   - Fix any identified issues.
   - Retry transformation and load.

## Known Bugs

- Hardcoded AWS credentials in the code.
- Lack of null handling in `transform_bronze_to_silver()`.

## Escalation Contacts

- **Severity 1:** Priya Nair (+91-98400-11111)
- **Severity 2:** Arjun Mehta (arjun.mehta@sigmadatatech.in)
- **Severity 3:** Kavya Reddy (kavya.reddy@sigmadatatech.in)

## Data Quality Checks

- Verify the count of records in `bronze_transactions`, `silver_transactions`, `gold_merchant_performance`, and `gold_daily_summary`.
- Ensure `quality_flag` is correctly set in `silver_transactions`.
- Check for any NULL values in critical fields.
- Confirm merchant performance and daily summary metrics align with expectations.