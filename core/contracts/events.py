"""
JKAI ZENITH — CONTRACT KERNEL: EVENTS
File: core/contracts/events.py

Domain event contract definitions for EventBus Pub/Sub messaging.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import uuid


@dataclass
class DomainEvent:
    """Base domain event."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = "domain_event"
    task_id: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionCompletedEvent(DomainEvent):
    """Fired when an execution completes in Runtime Adapter."""
    event_type: str = "execution.completed"
    result_content: str = ""
    model_used: str = ""
    latency_ms: float = 0.0


@dataclass
class FallbackActivatedEvent(DomainEvent):
    """Fired when a fallback protocol is triggered in Governance."""
    event_type: str = "governance.fallback_activated"
    role: str = ""
    requested_model: str = ""
    fallback_model: str = ""
    reason: str = ""
