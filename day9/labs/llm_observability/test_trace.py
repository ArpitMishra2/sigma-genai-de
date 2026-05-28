from phoenix.otel import register
from opentelemetry import trace
import time

tracer_provider = register()
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("demo_llm_call"):
    print("Generating telemetry...")
    time.sleep(2)

print("Done")