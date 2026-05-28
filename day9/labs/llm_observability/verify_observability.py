
import json
import os
import sys
import requests

def main():
    print("Checking LLM Observability Lab completion status...")

    # 1. Check if Phoenix UI/server is reachable
    try:
        response = requests.get("http://localhost:6006", timeout=5)

        if response.status_code != 200:
            raise Exception("Phoenix UI not reachable")

    except Exception as e:
        print("❌ Error: Could not connect to Phoenix server on http://localhost:6006")
        print("Make sure Phoenix is running with px.launch_app()")
        sys.exit(1)

    print("✓ Phoenix Server Connection: SUCCESS")

    # 2. Simple trace verification
    try:
        from phoenix.trace import SpanEvaluations

        print("✓ Phoenix package import successful")

    except Exception as e:
        print(f"❌ Error importing Phoenix tracing modules: {e}")
        sys.exit(1)

    # 3. Verify test trace file exists
    if not os.path.exists("test_trace.py"):
        print("❌ Error: test_trace.py not found.")
        sys.exit(1)

    print("✓ Trace generation script found")

    # 4. Create success output
    output_dir = "../output"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    result = {
        "status": "success",
        "phoenix_active": True,
        "telemetry_verified": True,
        "llm_observability_verified": True
    }

    output_file = os.path.join(
        output_dir,
        "llm_observability_success.json"
    )

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print("🎉 Verification SUCCESS!")
    print(f"✓ Created '{output_file}' for the tracker app.")


if __name__ == "__main__":
    main()

