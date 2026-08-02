# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/otlp_tracer.py
# - Role: OpenTelemetry W3C Trace Parent Standard Formatting (Inspired by AutoGen v0.4)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — Pure Python W3C traceparent header generation (< 0.1ms latency).
# 2. Inter-Service Traceability: Propagates W3C compliant traceparent headers across HTTP.
# 3. Observability Standardization: Formats span contexts for OpenTelemetry collectors.
# -----------------------------------------------------------------------------

import re
import uuid
import secrets
import logging
from typing import Tuple, Optional

logger = logging.getLogger("JKAI.OTLPTracer")


def generate_trace_parent(trace_id: Optional[str] = None) -> str:
    """
    Generates a W3C compliant traceparent header.
    Format: 00-{32 hex trace_id}-{16 hex span_id}-01
    """
    if not trace_id or len(trace_id.replace("-", "")) != 32:
        clean_trace = uuid.uuid4().hex
    else:
        clean_trace = trace_id.replace("-", "")

    span_id = secrets.token_hex(8)
    header = f"00-{clean_trace}-{span_id}-01"
    return header


def parse_trace_parent(header: str) -> Tuple[str, str]:
    """
    Parses a W3C traceparent header.

    Returns:
        (trace_id: str, span_id: str)
    """
    if not header:
        return uuid.uuid4().hex, secrets.token_hex(8)

    parts = header.strip().split("-")
    if len(parts) >= 4 and parts[0] == "00":
        return parts[1], parts[2]

    return uuid.uuid4().hex, secrets.token_hex(8)
