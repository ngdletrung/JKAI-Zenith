from enum import Enum
from dataclasses import dataclass
import time

class MemoryZone(Enum):
    """
    🗄️ Physical Memory Zones (Chống Context Bleed & Poisoning)
    """
    WORKING = "WORKING"       # Ephemeral, TTL=30m, Task-scoped
    EPISODIC = "EPISODIC"     # Persistent, Session-scoped
    LONG_TERM = "LONG_TERM"   # Persistent, Semantic indexed
    SECURITY = "SECURITY"     # Physically isolated, Audit-only
    SYSTEM = "SYSTEM"         # Read-only policy and configuration

@dataclass(frozen=True)
class WorkingMemoryBlock:
    trace_id: str
    content: dict
    created_at: float
    ttl_seconds: int = 1800 # 30 mins
    
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)
