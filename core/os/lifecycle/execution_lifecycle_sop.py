"""
JKAI ZENITH AI OS — UNIFIED EXECUTION LIFECYCLE SOP (v2)
File: core/os/lifecycle/execution_lifecycle_sop.py

Defines the 5-Stage Unified Execution Lifecycle:
STAGE 1: ADMIT     -> Ingress, Mission ID, Initial Constraints, Authority Scope.
STAGE 2: RESOLVE   -> Capability Mapping, Skill Discovery, Tool Intent, Strategy Topology.
STAGE 3: AUTHORIZE -> Scope Validation, Risk Check, Mutation Guard, Policy Gate.
STAGE 4: EXECUTE   -> Prompt Contract, Skill Invocation, Tool Execution, Observation Capture.
STAGE 5: VERIFY    -> Empirical Evidence, Physical Verification, Outcome State, Trace Hash.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class LifecycleStage(str, Enum):
    ADMIT = "ADMIT"
    RESOLVE = "RESOLVE"
    AUTHORIZE = "AUTHORIZE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"


@dataclass
class LifecycleContext:
    mission_id: str
    task_id: str
    current_stage: LifecycleStage = LifecycleStage.ADMIT
    goal: str = ""
    topology: str = "SINGLE_AGENT"  # SINGLE_AGENT (FAST) vs MULTI_AGENT (DEEP)
    capability_requirements: List[str] = field(default_factory=list)
    authorized_scope: Dict[str, Any] = field(default_factory=dict)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    evidence_records: List[Dict[str, Any]] = field(default_factory=list)
    verified: bool = False

    def advance_to(self, next_stage: LifecycleStage) -> None:
        """Transitions context to the next stage in the 5-stage lifecycle."""
        self.current_stage = next_stage


def initialize_lifecycle(mission_id: str, task_id: str, goal: str) -> LifecycleContext:
    """Initializes a new LifecycleContext at STAGE 1: ADMIT."""
    return LifecycleContext(
        mission_id=mission_id,
        task_id=task_id,
        current_stage=LifecycleStage.ADMIT,
        goal=goal
    )
