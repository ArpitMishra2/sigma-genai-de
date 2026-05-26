"""
Sigma DataTech Customer Churn Prediction Pipeline
Fixed Production-Ready Version
Day 7 — Pipeline Brain
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    max,
    sum,
    count,
    broadcast,
    datediff,
    current_date,
    current_timestamp,
    lit,
    when,
    expr
)

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    FloatType,
    TimestampType,
    DecimalType
)

import boto3
import json
import logging
import os
import shutil
import sys


# ============================================================
# CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

BRONZE_PATH = os.getenv("BRONZE_PATH")
SILVER_PATH = os.getenv("SILVER_PATH")
GOLD_PATH = os.getenv("GOLD_PATH")

INPUT_PATH = os.getenv("INPUT_PATH")
MERCHANTS_PATH = os.getenv("MERCHANTS_PATH")

SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")


# ============================================================
# BRONZE LAYER
# ============================================================

def ingest_bronze(spark, input_path, output_path, run_date, run_id):

    logging.info("Starting Bronze ingestion")

    try:

        # Validate input file exists
        s3 = boto3.client("s3")

        # Example validation placeholder
        if input_path is None:
            raise FileNotFoundError("INPUT_PATH environment variable missing")

        bronze_schema = StructType([
            StructField("customer_id", StringType(), True),
            StructField("transaction_id", StringType(), True),
            StructField("transaction_date", StringType(), True),
            StructField("amount", StringType(), True),
            StructField("payment_method", StringType(), True),
            StructField("status", StringType(), True),
            StructField("product_id", StringType(), True),
            StructField("merchant_id", StringType(), True)
        ])

        bronze_df = spark.read.csv(
            input_path,
            schema=bronze_schema,
            header=True
        )
        logging.info(f"Bronze input count: {bronze_df.count()}")
        input_count = bronze_df.count()
        logging.info(f"Bronze input rows: {input_count}")

        # Schema validation
        expected_columns = [
            "customer_id",
            "transaction_id",
            "transaction_date",
            "amount"
        ]

        missing_cols = [
            c for c in expected_columns
            if c not in bronze_df.columns
        ]

        if missing_cols:
            raise Exception(f"Missing columns: {missing_cols}")

        # Metadata columns
        bronze_df = (
            bronze_df
            .withColumn("ingestion_timestamp", current_timestamp())
            .withColumn("source_file_name", lit(input_path))
            .withColumn("pipeline_run_id", lit(run_id))
        )

        partition_path = f"{output_path}/transaction_date={run_date}"

        # Idempotency
        shutil.rmtree(partition_path, ignore_errors=True)

        bronze_df.write \
            .mode("overwrite") \
            .partitionBy("transaction_date") \
            .parquet(output_path)

        logging.info("Bronze ingestion completed")

    except Exception as e:

        logging.error(f"Bronze layer failed: {str(e)}")

        sns = boto3.client("sns")

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Bronze Pipeline Failure",
            Message=str(e)
        )

        raise


# ============================================================
# SILVER LAYER
# ============================================================

def transform_silver(
    spark,
    bronze_path,
    merchants_path,
    output_path,
    run_date
):

    logging.info("Starting Silver transformation")

    try:

        bronze_df = (
            spark.read.parquet(bronze_path)
            .filter(col("transaction_date") == run_date)
        )

        logging.info(f"Silver input rows: {bronze_df.count()}")

        # Type casting
        silver_df = (
            bronze_df
            .withColumn(
                "amount",
                col("amount").cast(DecimalType(18, 2))
            )
            .withColumn(
                "transaction_date",
                col("transaction_date").cast(TimestampType())
            )
        )

        # Filter COMPLETED transactions
        silver_df = silver_df.filter(
            col("status") == "COMPLETED"
        )
        logging.info(
            f"Rows after COMPLETED filter: {silver_df.count()}"
        )

        # NULL checks
        silver_df = silver_df.filter(
            col("customer_id").isNotNull()
        )

        silver_df = silver_df.filter(
            col("transaction_id").isNotNull()
        )

        # Deduplication
        silver_df = silver_df.dropDuplicates(
            ["transaction_id"]
        )

        logging.info(
            f"Rows after deduplication: {silver_df.count()}"
        )

        # Quality threshold
        total_rows = silver_df.count()

        null_customer_rows = silver_df.filter(
            col("customer_id").isNull()
        ).count()

        if total_rows > 0:

            null_pct = null_customer_rows / total_rows

            if null_pct > 0.05:

                metadata = {
                    "run_date": run_date,
                    "status": "FAILED",
                    "reason": "customer_id null percentage exceeded 5%"
                }

                with open(
                    f"run_metadata_{run_date}.json",
                    "w"
                ) as f:
                    json.dump(metadata, f)

                raise Exception(
                    "Quality threshold failed"
                )

        # Broadcast merchants dimension
        merchants_df = spark.read.parquet(
            merchants_path
        )

        merchants_df = broadcast(merchants_df)

        silver_df = silver_df.join(
            merchants_df,
            "merchant_id",
            "left"
        )

        partition_path = f"{output_path}/transaction_date={run_date}"

        # Idempotency
        shutil.rmtree(partition_path, ignore_errors=True)

        silver_df.write \
            .mode("overwrite") \
            .partitionBy("transaction_date") \
            .parquet(output_path)

        logging.info("Silver transformation completed")

    except Exception as e:

        logging.error(f"Silver layer failed: {str(e)}")

        raise


# ============================================================
# GOLD LAYER
# ============================================================

def build_churn_risk(
    spark,
    silver_path,
    output_path,
    run_date
):

    logging.info("Starting Gold aggregation")

    try:

        silver_df = (
            spark.read.parquet(silver_path)
            .filter(
                col("transaction_date") >=
                expr("current_date() - INTERVAL 30 DAYS")
            )
        )

        logging.info(
            f"Gold input rows: {silver_df.count()}"
        )

        churn_df = (
            silver_df.groupBy("customer_id")
            .agg(
                max("transaction_date").alias(
                    "last_transaction_date"
                ),
                count("transaction_id").alias(
                    "transaction_frequency"
                ),
                sum("amount").alias(
                    "total_spent"
                )
            )
            .withColumn(
                "recency_days",
                datediff(
                    current_date(),
                    col("last_transaction_date")
                )
            )
            .withColumn(
                "risk_status",
                when(
                    col("recency_days") > 14,
                    "at_risk"
                ).otherwise("active")
            )
            .withColumn(
                "generated_at",
                current_timestamp()
            )
        )

        logging.info(
            f"Gold output rows: {churn_df.count()}"
        )

        partition_path = f"{output_path}/transaction_date={run_date}"

        # Idempotency
        shutil.rmtree(partition_path, ignore_errors=True)

        churn_df.write \
            .mode("overwrite") \
            .parquet(output_path)

        metadata = {
            "pipeline_name": "CustomerChurnPredictionFeed",
            "run_date": run_date,
            "run_status": "SUCCESS"
        }

        with open(
            f"run_metadata_{run_date}.json",
            "w"
        ) as f:
            json.dump(metadata, f)

        logging.info("Gold aggregation completed")

    except Exception as e:

        logging.error(f"Gold layer failed: {str(e)}")

        raise


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    spark = SparkSession.builder \
        .appName("CustomerChurnPredictionFeed") \
        .getOrCreate()

    run_date = os.getenv("run_date")
    run_id = os.getenv("run_id")

    try:

        ingest_bronze(
            spark,
            INPUT_PATH,
            BRONZE_PATH,
            run_date,
            run_id
        )

        transform_silver(
            spark,
            BRONZE_PATH,
            MERCHANTS_PATH,
            SILVER_PATH,
            run_date
        )

        build_churn_risk(
            spark,
            SILVER_PATH,
            GOLD_PATH,
            run_date
        )

        logging.info("Pipeline completed successfully")

    except Exception as e:

        logging.error(f"Pipeline failed: {str(e)}")

        sys.exit(1)

    finally:

        spark.stop()

expected_columns = [
    "customer_id",
    "transaction_id",
    "transaction_date",
    "amount"
]

if __name__ == "__main__":
    main()