"""
JKAI ZENITH — CONTRACT KERNEL: MISSION & SUCCESS CRITERIA
File: core/contracts/mission.py

Contracts for Mission State, Context, Success Criteria, and Budget.
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
class SuccessCriteria:
    """Explicit success criteria contract for Mission evaluation."""
    required_elements: List[str] = field(default_factory=list)
    max_hallucination_score: float = 0.10
    requires_citations: bool = False
    format_requirements: Dict[str, Any] = field(default_factory=dict)
    min_quality_score: float = 0.80


@dataclass
class MissionContext:
    """Single Source of Truth for a running Mission."""
    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    state: MissionState = MissionState.IDLE
    current_step: int = 0
    max_steps: int = 25
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
