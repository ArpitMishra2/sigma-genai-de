# NL2SQL vs Cortex Analyst — Sigma DataTech Evaluation

## 5-Question Head-to-Head Results

| # | Question | Module 2 SQL Correct? | Cortex SQL Correct? | Module 2 Time | Cortex Time |
|---|---|---|---|---|---|
| 1 | Total transaction count | YES | YES | ~2s | ~2s |
| 2 | Failed transaction count | YES | YES | ~2s | ~2s |
| 3 | Highest revenue merchant | YES | YES | ~2s | ~2s |
| 4 | Failure rate by payment method | YES | YES | ~2s | ~2s |
| 5 | Total revenue | YES | YES | ~2s | ~2s |

## Observations

### Where Module 2 NL2SQL was better:
- More customizable
- Full control over prompting

### Where Cortex Analyst was better:
- Easier setup
- Less maintenance
- Better enterprise integration

## Business Rule Accuracy

Both systems correctly used:
STATUS = 'COMPLETED'
for revenue calculations.

## Recommendation

Recommendation: Cortex Analyst

Reason:
Cortex Analyst is easier to maintain, keeps data inside Snowflake,
requires less prompt engineering, and scales better for production analytics.