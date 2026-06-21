---
type: python_file
file: utils/tracing.py
tags: []
---

# tracing

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentele

## Links to
- [[os]]
- [[opentelemetry]]
- [[opentelemetry.sdk.resources]]
- [[opentelemetry.sdk.trace]]
- [[opentelemetry.sdk.trace.export]]
- [[opentelemetry.exporter.otlp.proto.grpc.trace_exporter]]
- [[opentelemetry.instrumentation.fastapi]]
