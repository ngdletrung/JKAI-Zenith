# -*- coding: utf-8 -*-
"""
📊 STRUCTURED JSON LOGGER & AUDIT EMITTER
File: core/observability/structured_logger.py
Role: Zero-blocking structured JSON telemetry adhering to OpenTelemetry GenAI semantics
Version: SDS v26.4 (Reliability-First Slice A)

Principles (Turn 25 Consensus):
1. ZERO FREE-TEXT LOGS: All telemetry emits structured JSON adhering to a single schema.
2. ZERO BLOCKING: Log formatting is in-process, synchronous fast-path (<50µs), safe serialization.
3. CONTEXT PROPAGATION: Tracks trace_id, span_id, tool_name, authority_decision, duration_ms, error_code.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("JKAI.StructuredLogger")


@dataclass
class StructuredLogEntry:
    """Standardized structured JSON log schema."""
    trace_id: str
    span_id: str
    timestamp: str
    tool_name: str
    duration_ms: float
    error_code: Optional[str]
    authority_decision: str
    message: str
    service: str = "ai-brain"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StructuredLogger:
    """
    High-performance, in-process structured JSON logger.
    Emits single-line JSON entries suitable for OpenTelemetry collectors or file sinks.
    """

    def __init__(self, service_name: str = "ai-brain"):
        self.service_name = service_name

    def format_entry(
        self,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        tool_name: str = "unknown",
        duration_ms: float = 0.0,
        error_code: Optional[str] = None,
        authority_decision: str = "N/A",
        extra: Optional[Dict[str, Any]] = None,
    ) -> StructuredLogEntry:
        now_iso = datetime.now(timezone.utc).isoformat()
        return StructuredLogEntry(
            trace_id=trace_id or f"tr_{uuid.uuid4().hex[:8]}",
            span_id=span_id or f"sp_{uuid.uuid4().hex[:8]}",
            timestamp=now_iso,
            tool_name=tool_name,
            duration_ms=round(duration_ms, 3),
            error_code=error_code,
            authority_decision=authority_decision,
            message=message,
            service=self.service_name,
            extra=extra or {},
        )

    def emit(
        self,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        tool_name: str = "unknown",
        duration_ms: float = 0.0,
        error_code: Optional[str] = None,
        authority_decision: str = "N/A",
        extra: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO,
    ) -> str:
        """Formats and logs a single structured JSON line."""
        entry = self.format_entry(
            message=message,
            trace_id=trace_id,
            span_id=span_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            error_code=error_code,
            authority_decision=authority_decision,
            extra=extra,
        )
        json_str = entry.to_json()
        logger.log(level, json_str)
        return json_str


# Global singleton
_structured_logger = StructuredLogger()

def get_structured_logger() -> StructuredLogger:
    return _structured_logger

def log_structured_event(
    message: str,
    tool_name: str = "system",
    authority_decision: str = "ALLOW",
    duration_ms: float = 0.0,
    error_code: Optional[str] = None,
    trace_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience helper for emitting structured events across the codebase."""
    return _structured_logger.emit(
        message=message,
        trace_id=trace_id,
        tool_name=tool_name,
        duration_ms=duration_ms,
        error_code=error_code,
        authority_decision=authority_decision,
        extra=extra,
    )
