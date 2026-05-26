from typing import Dict, List, Tuple, Union
from pyspark.sql import DataFrame
from pyspark.sql.types import StringType, FloatType, StructType, StructField

def detect_schema_drift(expected_schema: Dict[str, str], actual_schema: Dict[str, str]) -> Dict[str, Union[Dict[str, str], List[str], str]]:
    new_columns = {k: v for k, v in actual_schema.items() if k not in expected_schema}
    removed_columns = {k: v for k, v in expected_schema.items() if k not in actual_schema}
    type_changes = {k: (expected_schema[k], actual_schema[k]) for k in expected_schema if expected_schema[k]!= actual_schema[k]}
    drift_severity = 'NONE'
    
    if new_columns:
        if any('null' not in v for v in new_columns.values()):
            drift_severity = 'HIGH'
        else:
            drift_severity = 'LOW'
    elif removed_columns:
        drift_severity = 'BREAKING'
    
    return {
        'new_columns': new_columns,
       'removed_columns': list(removed_columns.keys()),
        'type_changes': list(type_changes.items()),
        'drift_severity': drift_severity
    }

def decide_action(drift_report: Dict[str, Union[Dict[str, str], List[str], str]]) -> Dict[str, Dict[str, str]]:
    decisions = {}
    for column, dtype in drift_report['new_columns'].items():
        if dtype.endswith('null'):
            decisions[column] = {'action': 'ADD_TO_SCHEMA','reason': 'Nullable new column', 'risk_level': 'LOW'}
        elif column == 'discount_amount':
            decisions[column] = {'action': 'FLAG_ANOMALY','reason': 'Potential revenue impact', 'risk_level': 'HIGH'}
        else:
            decisions[column] = {'action': 'ADD_TO_SCHEMA','reason': 'New nullable column', 'risk_level': 'LOW'}
    
    for column in drift_report['removed_columns']:
        decisions[column] = {'action': 'HALT','reason': 'Removed column will break downstream queries', 'risk_level': 'BREAKING'}
    
    return decisions

def apply_schema_evolution(spark_df: DataFrame, decisions: Dict[str, Dict[str, str]], updated_schema: Dict[str, str]) -> Tuple[DataFrame, List[str]]:
    migration_notes = []
    for column, decision in decisions.items():
        if decision['action'] == 'DROP_SILENTLY':
            spark_df = spark_df.drop(column)
            migration_notes.append(f"Column '{column}' silently dropped.")
        elif decision['action'] == 'ADD_TO_SCHEMA':
            if column not in spark_df.columns:
                if decision['reason'] == 'Type widening':
                    migration_notes.append(f"Column '{column}' added with type change from int to float.")
                else:
                    migration_notes.append(f"Column '{column}' added.")
        elif decision['action'] == 'FLAG_ANOMALY':
            spark_df = spark_df.withColumn(f"{column}_anomaly", spark_df[column].isNull().cast(StringType()))
            migration_notes.append(f"Column '{column}' flagged for anomaly.")
    
    return spark_df, migration_notes

def handle_drift(expected_schema: Dict[str, str], actual_schema: Dict[str, str], spark_df: DataFrame = None) -> Dict[str, Union[Dict[str, Dict[str, str]], Dict[str, Union[Dict[str, str], List[str], str]], Tuple[DataFrame, List[str]]]]:
    drift_report = detect_schema_drift(expected_schema, actual_schema)
    decisions = decide_action(drift_report)
    if spark_df is not None:
        evolved_df, migration_notes = apply_schema_evolution(spark_df, decisions, actual_schema)
        full_report = {'drift_report': drift_report, 'decisions': decisions,'migration_notes': migration_notes}
    else:
        evolved_df, migration_notes, full_report = None, [], {'drift_report': drift_report, 'decisions': decisions}
    
    print("Drift Report:")
    print(drift_report)
    print("Decisions:")
    print(decisions)
    if migration_notes:
        print("Migration Notes:")
        for note in migration_notes:
            print(note)
    
    return full_report if spark_df is None else {'drift_report': drift_report, 'decisions': decisions,'migration_notes': migration_notes, 'evolved_df': evolved_df}
