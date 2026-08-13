"""
core/os/cognition/adaptive_solver/models.py
Adaptive Task Solver (ATS) & Execution Truth Layer — Governed Canonical Data Models.

Key Invariants:
1. Mission Immutability: Mission & Requirements are immutable; Strategy & Granularity are adaptive.
2. SituationModel: Centered on Expected vs Actual, Risk, Complexity, Progress, and Facts.
3. 3-Tier Truth: ToolOutcome != ArtifactOutcome != MissionOutcome.
4. Termination States: COMPLETED | RECOVERY | LOW_CONFIDENCE_CONCLUSION | SAFE_STOP.
5. Ownership: ATS is the cognitive governor; FAST/DEEP are execution primitives.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ActionGranularity(str, Enum):
    PROBE = "PROBE"                     # Small, low-cost probe (e.g. read 1-2 files, run 1 dry command)
    PRECISION = "PRECISION"             # Surgical edit or single-target operation
    BATCH = "BATCH"                     # High-confidence mass transformation of homogenous items
    TARGETED_REPAIR = "TARGETED_REPAIR" # Surgical correction of a specific unsatisfied requirement
    VERIFY = "VERIFY"                   # Semantic and functional outcome audit


class ToolOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PARTIAL = "PARTIAL"


class ArtifactOutcome(str, Enum):
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    CORRUPTED = "CORRUPTED"
    UNCHANGED = "UNCHANGED"
    NONE = "NONE"


class RequirementStatus(str, Enum):
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MissionOutcome(str, Enum):
    COMPLETED = "COMPLETED"                               # 100% criteria proven with genuine physical evidence
    RECOVERY = "RECOVERY"                                 # Replanning / targeted repair active
    LOW_CONFIDENCE_CONCLUSION = "LOW_CONFIDENCE_CONCLUSION" # Insufficient evidence; safely halted with transparent diagnostic
    SAFE_STOP = "SAFE_STOP"                               # Stopped due to security, policy, or hard invariant bounds


class StrategyDecision(str, Enum):
    CONTINUE_CURRENT_STRATEGY = "CONTINUE_CURRENT_STRATEGY"
    REFINE_GRANULARITY = "REFINE_GRANULARITY"
    STRATEGY_INVALIDATED = "STRATEGY_INVALIDATED"
    PIVOT_STRATEGY = "PIVOT_STRATEGY"
    DEEPEN_REASONING = "DEEPEN_REASONING"
    TARGETED_REPAIR = "TARGETED_REPAIR"
    TERMINATE_WITH_PROOF = "TERMINATE_WITH_PROOF"
    SAFE_STOP = "SAFE_STOP"


class MissionImmutabilityViolationError(Exception):
    """Raised when ATS or any subsystem attempts to mutate or drop immutable Mission requirements."""
    pass


@dataclass
class ExpectedVsActual:
    """Explicit expectation vs observation reality comparison."""
    expected_state: str
    observed_reality: str
    is_divergent: bool = False
    divergence_reason: Optional[str] = None


@dataclass
class SituationModel:
    """Rich situational intelligence model maintaining JKAI's real-time ground truth."""
    mission_id: str
    initial_hypothesis: str
    immutable_mission_hash: str
    discovered_files: List[str] = field(default_factory=list)
    homogenous_groups: Dict[str, List[str]] = field(default_factory=dict)
    anomalous_items: List[str] = field(default_factory=list)
    known_facts: Dict[str, Any] = field(default_factory=dict)
    unknowns: List[str] = field(default_factory=list)
    expected_vs_actual: List[ExpectedVsActual] = field(default_factory=list)
    current_granularity: ActionGranularity = ActionGranularity.PROBE
    complexity_score: float = 0.5   # 0.0 (trivial) to 1.0 (extreme deep DAG)
    risk_score: float = 0.1         # 0.0 (safe read-only) to 1.0 (irreversible mutation)
    confidence_score: float = 0.5   # 0.0 (unsupported) to 1.0 (fully proven)
    progress_percent: float = 0.0   # 0.0 to 100.0%
    updated_at: float = field(default_factory=time.time)


@dataclass
class ExecutionTruth:
    """3-Tier Ground Truth: ToolOutcome -> ArtifactOutcome -> MissionOutcome."""
    invocation_id: str
    tool_name: str
    arguments: Dict[str, Any]
    tool_outcome: ToolOutcome
    artifact_outcome: ArtifactOutcome
    mission_outcome: MissionOutcome = MissionOutcome.RECOVERY
    artifact_path: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    requirement_verdicts: Dict[str, RequirementStatus] = field(default_factory=dict)
    is_genuine_success: bool = False
    diagnostic_details: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class StrategyAdaptation:
    """Governed adaptive decision produced by ATS with full causal provenance."""
    decision: StrategyDecision
    recommended_granularity: ActionGranularity
    rationale: str
    reason_codes: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    invalidated_assumptions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    expected_outcome: str = ""
    budget_cost: float = 0.0
    authority_scope: str = "AUTONOMOUS"
    next_action_target: Optional[str] = None
    replan_instructions: Optional[str] = None
    escalate_to_deep: bool = False
    safe_stop_reason: Optional[str] = None
    provenance_trace: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
