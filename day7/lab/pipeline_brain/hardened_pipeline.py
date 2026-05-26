import logging
import shutil
import json
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, count, expr, lit, when, current_date
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType, IntegerType
import sys
import boto3

logging.basicConfig(level=logging.INFO)

def ingest_bronze(spark, input_path, output_path, run_date, run_id):
    try:
        s3 = boto3.client('s3')
        s3.head_object(Bucket='your-bucket-name', Key=input_path)
    except:
        logging.error(f"Source file {input_path} not found.")
        raise FileNotFoundError(f"Source file {input_path} not found.")
    
    bronze_schema = StructType([
        StructField("customer_id", StringType(), True),
        StructField("transaction_id", StringType(), True),
        StructField("transaction_date", StringType(), True),
        StructField("amount", StringType(), True),
        StructField("payment_method", StringType(), True),
        StructField("status", StringType(), True),
        StructField("product_id", StringType(), True),
    ])
    bronze_df = spark.read.csv(input_path, schema=bronze_schema, header=True)
    
    bronze_df = bronze_df.withColumn("ingestion_timestamp", current_date()) \
                         .withColumn("source_file_name", input_path) \
                        .withColumn("pipeline_run_id", lit(run_id))
    
    partition_path = f"{output_path}/transaction_date={run_date}"
    shutil.rmtree(partition_path, ignore_errors=True)
    
    bronze_df.write.mode('overwrite').partitionBy("transaction_date").parquet(output_path)
    
    logging.info(f"[Ingest] row_count_logging: {bronze_df.count()}")

def transform_silver(spark, bronze_path, merchants_path, output_path, run_date):
    try:
        bronze_df = spark.read.parquet(bronze_path).where(col("transaction_date") == run_date)
        
        silver_schema = StructType([
            StructField("customer_id", StringType(), True),
            StructField("transaction_id", StringType(), True),
            StructField("transaction_date", TimestampType(), True),
            StructField("amount", FloatType(), True),
            StructField("payment_method", StringType(), True),
            StructField("status", StringType(), True),
            StructField("product_id", StringType(), True),
            StructField("ingestion_timestamp", TimestampType(), True),
            StructField("source_file_name", StringType(), True),
            StructField("pipeline_run_id", StringType(), True)
        ])
        silver_df = bronze_df.select([col(c).cast(silver_schema[c].dataType) for c in silver_schema.fieldNames()])
        
        silver_df = silver_df.filter(col("transaction_id").isNotNull() & (col("amount") >= 0))
        
        logging.info(f"[Silver] after_filter_count: {silver_df.count()}")
        
        silver_df = silver_df.dropDuplicates(["transaction_id"], ["ingestion_timestamp"]).orderBy("ingestion_timestamp", ascending=False)
        
        logging.info(f"[Silver] after_dedup_count: {silver_df.count()}")
        
        merchants_df = spark.read.parquet(merchants_path)
        merchants_df = merchants_df.filter(col("transaction_date") == run_date)
        
        silver_df = silver_df.join(merchants_df, silver_df.merchant_id == merchants_df.merchant_id, "left")
        
        null_customer_id_count = silver_df.filter(col("customer_id").isNull()).count()
        total_rows = silver_df.count()
        quality_halt_threshold = 0.05
        if null_customer_id_count / total_rows > quality_halt_threshold:
            raise Exception("Quality check failed: null customer_id exceeds 5%")
        
        silver_df = silver_df.withColumn("quality_flag", when(col("customer_id").isNotNull(), "CLEAN").otherwise("UNMATCHED"))
        
        partition_path = f"{output_path}/transaction_date={run_date}"
        shutil.rmtree(partition_path, ignore_errors=True)
        
        silver_df.write.mode('overwrite').partitionBy("transaction_date").parquet(output_path)
        
        logging.info(f"[Silver] output_count: {silver_df.count()}")
    
    except Exception as e:
        logging.error(f"[Silver] Error: {str(e)}")
        raise

def main():
    spark = SparkSession.builder.appName("CustomerChurnPredictionFeed").getOrCreate()
    input_path = "s3://your-bucket-name/bronze/input.csv"
    bronze_output_path = "s3://your-bucket-name/bronze/"
    silver_output_path = "s3://your-bucket-name/silver/"
    merchants_path = "s3://your-bucket-name/dimensions/merchants.parquet"
    run_date = "2023-04-01"
    run_id = "run-12345"
    
    metadata = {
        'pipeline_name': 'Sigma DataTech Transaction Analytics Pipeline',
        'run_date': run_date,
        'run_id': run_id,
        'run_status': 'SUCCESS',
       'started_at': datetime.now().isoformat(),
        'completed_at': None,
        'error_message': None
    }
    
    try:
        ingest_bronze(spark, input_path, bronze_output_path, run_date, run_id)
        transform_silver(spark, bronze_output_path, merchants_path, silver_output_path, run_date)
        
        metadata['completed_at'] = datetime.now().isoformat()
        
        with open(f"{silver_output_path}/run_metadata_{run_date}.json", 'w') as f:
            json.dump(metadata, f)
    
    except Exception as e:
        metadata['run_status'] = 'FAILED'
        metadata['error_message'] = str(e)
        metadata['completed_at'] = datetime.now().isoformat()
        
        with open(f"{silver_output_path}/run_metadata_{run_date}.json", 'w') as f:
            json.dump(metadata, f)
        
        logging.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
