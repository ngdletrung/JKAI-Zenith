"""
JKAI ZENITH — CONTRACT KERNEL: MISSION
File: core/contracts/mission.py

Contracts for Mission State and Context.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time
import uuid


class MissionState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


@dataclass
class MissionContext:
    """Single Source of Truth for a running Mission."""
    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    state: MissionState = MissionState.IDLE
    current_step: int = 0
    max_steps: int = 25
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
