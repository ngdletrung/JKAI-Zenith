from dataclasses import dataclass
from typing import Optional, Dict, List, Callable
import time
import json
import logging

logger = logging.getLogger("InternalEventBus")

@dataclass(frozen=True)
class CognitiveEvent:
    """
    📡 Giao thức Dữ liệu Phân Tán (Internal Async Event Contract)
    Bảo đảm Deterministic Tracing khi scale up lên Kafka/Redis Streams.
    """
    event_id: str
    trace_id: str
    correlation_id: str
    causation_id: Optional[str]
    event_type: str
    payload: dict
    timestamp: float
    event_schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id or "",
            "event_type": self.event_type,
            "payload": json.dumps(self.payload),
            "timestamp": str(self.timestamp),
            "event_schema_version": self.event_schema_version,
        }

class InternalEventBus:
    """Event Bus nội bộ phân tán (Redis Streams + In-Process Dispatcher)."""
    def __init__(self, redis_client=None):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.redis = redis_client

    def _get_redis(self):
        if not self.redis:
            try:
                from core.utils.engine import engine
                self.redis = engine._get_redis()
            except Exception:
                pass
        return self.redis

    def publish(self, event: CognitiveEvent):
        """🚀 [EVENT-STREAM-PUBLISH]: Đẩy sự kiện vào Redis Streams & In-process handlers."""
        # 1. In-process local subscriber dispatch
        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as sub_err:
                    logger.error(f"[EVENT-BUS-HANDLER-ERR] {sub_err}")

        # 2. Redis Streams XADD for distributed cross-service consumption
        r = self._get_redis()
        if r:
            try:
                stream_key = f"stream:events:{event.event_type}"
                r.xadd(stream_key, event.to_dict(), maxlen=5000)
            except Exception as redis_err:
                logger.warning("[EVENT-STREAM-ERR] XADD failed: %s", redis_err)

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
