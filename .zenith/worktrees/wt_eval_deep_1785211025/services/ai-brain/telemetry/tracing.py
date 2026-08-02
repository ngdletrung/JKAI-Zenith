from dataclasses import dataclass
from typing import Optional
import time

@dataclass(frozen=True)
class W3CTraceContext:
    """
    🔗 Mắt Thần W3C OpenTelemetry
    Sẵn sàng cắm vào Grafana, Jaeger.
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    causation_id: Optional[str]
    correlation_id: str
    timestamp: float = time.time()

class Tracer:
    def __init__(self):
        pass

    def start_span(self, trace_id: str, name: str, parent_span_id: Optional[str] = None) -> W3CTraceContext:
        import uuid
        span_id = uuid.uuid4().hex[:16]
        return W3CTraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            causation_id=parent_span_id,
            correlation_id=trace_id
        )
