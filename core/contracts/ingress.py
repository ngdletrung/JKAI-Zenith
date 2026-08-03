"""
JKAI ZENITH — CONTRACT KERNEL: INGRESS
File: core/contracts/ingress.py

Contracts for Domain A (Experience / Ingress).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import uuid


@dataclass
class IngressGoal:
    """Represents a user goal or API trigger entering JKAI OS."""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = ""
    source: str = "user_chat"               # "user_chat" | "api" | "webhook" | "cron"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class IngressEvent:
    """Represents an external trigger event."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = "user_message"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
