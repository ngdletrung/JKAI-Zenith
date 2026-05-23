from dataclasses import dataclass
from typing import Optional
import time
import json

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

class InternalEventBus:
    """Event Bus nội bộ, dọn đường cho distributed systems."""
    def __init__(self):
        self.subscribers = {}

    def publish(self, event: CognitiveEvent):
        # TODO: Đẩy vào Queue nội bộ hoặc log lại
        # Nếu lên Phase 4, hàm này sẽ đẩy vào NATS/Redis Streams
        pass
        
    def subscribe(self, event_type: str, handler):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
