"""
JKAI ZENITH — CONTRACT KERNEL: MISSION CONTRACT & CONSTRAINTS
File: core/contracts/mission.py

Contracts for Mission State, Context, MissionContract, SuccessCriteria, and Budget.
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
class MissionContract:
    """
    Absolute Source of Truth for a Mission.
    Defines Goal, Constraints, SuccessCriteria, FailureCriteria, SafetyPolicy, Authority, and Budget.
    """
    contract_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    constraints: List[str] = field(default_factory=list)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    failure_criteria: List[str] = field(default_factory=list)
    safety_policy: str = "STRICT_DENY_FIRST"
    authority_scope: List[str] = field(default_factory=lambda: ["read", "write_draft"])
    max_steps: int = 25
    budget_seconds: float = 300.0


@dataclass
class MissionContext:
    """Single Source of Truth for a running Mission execution instance."""
    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    contract: MissionContract = field(default_factory=MissionContract)
    goal: str = ""
    success_criteria: Optional[SuccessCriteria] = None
    state: MissionState = MissionState.IDLE
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.goal and not self.contract.goal:
            self.contract.goal = self.goal
        elif self.contract.goal and not self.goal:
            self.goal = self.contract.goal

        if self.success_criteria is not None:
            self.contract.success_criteria = self.success_criteria
        else:
            self.success_criteria = self.contract.success_criteria
