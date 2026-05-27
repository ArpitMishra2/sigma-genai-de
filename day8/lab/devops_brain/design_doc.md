# Pipeline Design Document

## What This Pipeline Does
This pipeline ingests transaction data, enriches it with merchant details, and then transforms it into clean, enriched, and aggregated formats for further analysis.

## Data Flow Diagram

```plaintext
Source (TRANSACTIONS_CLEAN, TRANSACTIONS_DIRTY, MERCHANTS)
    |
    v
Bronze Table: bronze_transactions
    |
    v
Silver Table: silver_transactions
    |
    v
Gold Tables:
    |
    v
Gold Merchant Performance: gold_merchant_performance
    |
    v
Gold Daily Summary: gold_daily_summary
```

## Key Design Decisions

- **Layered Data Processing**: The pipeline uses a three-tier approach (Bronze, Silver, Gold) to ensure data quality and enrichment before aggregation.
- **Data Enrichment**: Merchant details are joined with transaction data in the Silver layer to provide context.
- **Aggregative Metrics**: The Gold layer computes daily summaries and merchant performance metrics for analytical purposes.
- **Data Quality Flags**: Quality flags are added to transactions in the Silver layer to track data cleanliness.

## Known Limitations

- **Single-threaded Processing**: The pipeline processes data sequentially, which may not be optimal for very large datasets.
- **Limited Error Handling**: The pipeline has minimal error handling, which could lead to data loss in case of exceptions.
- **Static Merchant Data**: Merchant data is loaded once and not updated unless the pipeline is rerun.
- **No Data Versioning**: The pipeline does not maintain historical versions of data, which could be useful for auditing.

## Dependencies

- **DuckDB Database**: The pipeline relies on DuckDB for storing and querying data.
- **MERCHANTS Data**: A predefined list of merchant details is required for enriching transaction data.
- **TRANSACTIONS_CLEAN and TRANSACTIONS_DIRTY**: These are the primary data sources for the pipeline.
- **AWS S3 Bucket**: Used for storing and retrieving data, though not directly referenced in the provided code.