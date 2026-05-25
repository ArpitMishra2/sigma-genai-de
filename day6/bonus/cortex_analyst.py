# ============================================================
# cortex_analyst.py
# Cortex Analyst Client — Sigma DataTech
# ============================================================

import json
import time
import os
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# ── CONFIGURATION ──────────────────────────────────────────

ACCOUNT = 'gejkiog-tkc55632'
USER = 'student_genai'

KEY_FILE = os.path.join(
    os.path.dirname(__file__),
    'student_key.p8'
)

# ── LOAD PRIVATE KEY ───────────────────────────────────────

with open(KEY_FILE, 'rb') as f:
    private_key = serialization.load_pem_private_key(
        f.read(),
        password=None,
        backend=default_backend()
    )

PRIVATE_KEY_BYTES = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# ── SEMANTIC MODEL ─────────────────────────────────────────

SEMANTIC_MODEL = '@SIGMA_DE.PUBLIC.SEMANTIC_MODELS/sigma_semantic_model.yaml'

# ── CONNECTION ─────────────────────────────────────────────

def get_connection():
    return snowflake.connector.connect(
        user=USER,
        account=ACCOUNT,
        private_key=PRIVATE_KEY_BYTES,
        database='SIGMA_DE',
        schema='PUBLIC',
        warehouse='COMPUTE_WH',
        role='STUDENT_CORTEX'
    )

# ── ASK CORTEX ─────────────────────────────────────────────

def ask_cortex(question: str) -> dict:

    print(f"\n[Cortex] Question: {question}")

    start_time = time.time()

    conn = get_connection()
    cur = conn.cursor()

    sql_prompt = f"""
Given this schema:

FACT_TRANSACTIONS(
    TRANSACTION_ID,
    AMOUNT,
    STATUS,
    MERCHANT_ID,
    CUSTOMER_ID,
    TRANSACTION_DATE,
    PAYMENT_METHOD
)

DIM_MERCHANT(
    MERCHANT_ID,
    MERCHANT_NAME,
    CATEGORY,
    CITY
)

Business Rule:
Revenue = SUM(AMOUNT) WHERE STATUS = 'COMPLETED'

Write a Snowflake SQL query to answer:

{question}

Return ONLY SQL.
"""

    try:

        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', %s)",
            (sql_prompt,)
        )

        sql_response = cur.fetchone()[0].strip()

        # remove markdown fences if generated
        if sql_response.startswith("```"):
            sql_response = sql_response.split("\n", 1)[1]
            sql_response = sql_response.rsplit("```", 1)[0].strip()

        print("\nGenerated SQL:")
        print(sql_response)

        result = {
            "sql": sql_response,
            "columns": [],
            "rows": [],
            "elapsed_seconds": 0,
            "error": None
        }

        # execute generated sql
        cur.execute(sql_response)

        result["columns"] = [desc[0] for desc in cur.description]
        result["rows"] = cur.fetchall()

        elapsed = time.time() - start_time
        result["elapsed_seconds"] = elapsed

        conn.close()

        return result

    except Exception as e:

        return {
            "sql": "",
            "columns": [],
            "rows": [],
            "elapsed_seconds": 0,
            "error": str(e)
        }

# ── DISPLAY RESULTS ────────────────────────────────────────

def display_results(question, result):

    print("\n" + "=" * 60)
    print(f"QUESTION: {question}")
    print("=" * 60)

    if result["error"]:
        print("ERROR:")
        print(result["error"])
        return

    print("\nSQL:")
    print(result["sql"])

    print("\nRESULTS:")

    if result["columns"]:
        header = " | ".join(result["columns"])
        print(header)
        print("-" * len(header))

        for row in result["rows"]:
            print(" | ".join(str(v) for v in row))

    print(f"\nResponse Time: {result['elapsed_seconds']:.2f}s")

# ── QUESTIONS ──────────────────────────────────────────────

COMPARISON_QUESTIONS = [

    "How many transactions do we have in total?",

    "How many transactions failed?",

    "Which merchant had the highest revenue?",

    "What is the failure rate for each payment method?",

    "What was the total revenue generated across all merchants?"
]

# ── RUNNER ─────────────────────────────────────────────────

def run_comparison():

    print("\n" + "=" * 60)
    print("CORTEX ANALYST TEST")
    print("=" * 60)

    comparison_log = []

    for i, question in enumerate(COMPARISON_QUESTIONS, 1):

        print(f"\n\n[Question {i}/5]")

        result = ask_cortex(question)

        display_results(question, result)

        comparison_log.append({
            "question_num": i,
            "question": question,
            "sql_generated": result.get("sql"),
            "row_count": len(result.get("rows", [])),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "error": result.get("error")
        })

        time.sleep(1)

    # save results
    with open("cortex_results.json", "w") as f:
        json.dump(comparison_log, f, indent=2)

    print("\nResults saved to cortex_results.json")

# ── MAIN ───────────────────────────────────────────────────

if __name__ == "__main__":
    run_comparison()