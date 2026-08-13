"""
core/os/cognition/adaptive_solver/models.py
Adaptive Task Solver (ATS) & Execution Truth Layer — Governed Canonical Data Models.

Key Invariants:
1. Mission Immutability: Mission & Requirements are immutable; Strategy & Granularity are adaptive.
2. SituationModel: Ground truth world state with Beliefs, Causal Graph, Expected vs Actual, and Uncertainty Budget.
3. Dynamic Bidirectional Granularity: MICRO_PROBE <-> PROBE <-> TARGETED <-> PRECISION <-> BATCH <-> PARALLEL_BATCH.
4. Recovery Taxonomy: RETRY | REPAIR | ROLLBACK | REPLAN | ESCALATE | ABANDON | SAFE_STOP.
5. 3-Tier Truth: ToolOutcome != ArtifactOutcome != MissionOutcome.
6. Ownership: ATS is the cognitive governor; FAST/DEEP are execution primitives.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ActionGranularity(str, Enum):
    MICRO_PROBE = "MICRO_PROBE"         # Minimal read/check of a specific line or AST node
    PROBE = "PROBE"                     # Small, low-cost probe (e.g. read 1-2 files, run 1 dry command)
    TARGETED = "TARGETED"               # Focused operation on a single identified file/entity
    PRECISION = "PRECISION"             # Surgical edit or single-target operation
    BATCH = "BATCH"                     # High-confidence mass transformation of homogenous items
    PARALLEL_BATCH = "PARALLEL_BATCH"   # Concurrent multi-worker execution across verified clusters
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
    COMPLETED = "COMPLETED"                                 # 100% criteria proven with genuine physical evidence
    RECOVERY = "RECOVERY"                                   # Replanning / targeted repair active
    LOW_CONFIDENCE_CONCLUSION = "LOW_CONFIDENCE_CONCLUSION" # Insufficient evidence; safely halted with transparent diagnostic
    SAFE_STOP = "SAFE_STOP"                                 # Stopped due to security, policy, or hard invariant bounds


class RecoveryAction(str, Enum):
    RETRY = "RETRY"         # Transient tool timeout or temporary network blip
    REPAIR = "REPAIR"       # Specific unsatisfied requirement or corrupted artifact patch
    ROLLBACK = "ROLLBACK"   # Partial mutation failure needing atomic snapshot restore
    REPLAN = "REPLAN"       # Refuted assumption needing new action topology
    ESCALATE = "ESCALATE"   # High complexity needing mode switch from FAST to DEEP
    ABANDON = "ABANDON"     # Exhausted budget with transparent low-confidence report
    SAFE_STOP = "SAFE_STOP" # Security or permission boundary halt


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
class StrategyConfidenceTracker:
    """Tracks continuous confidence in the active strategy and triggers decay on anomalies."""
    initial_confidence: float = 0.95
    current_confidence: float = 0.95
    invalidation_threshold: float = 0.40
    decay_events: List[Dict[str, Any]] = field(default_factory=list)

    def record_anomaly(self, reason: str, penalty: float = 0.25) -> float:
        self.current_confidence = max(0.0, self.current_confidence - penalty)
        self.decay_events.append({
            "reason": reason,
            "penalty": penalty,
            "new_confidence": self.current_confidence,
            "timestamp": time.time()
        })
        return self.current_confidence

    @property
    def is_invalidated(self) -> bool:
        return self.current_confidence < self.invalidation_threshold


@dataclass
class UncertaintyBudget:
    """Tracks uncertainty levels to gate risky mass mutations."""
    total_unknowns: int = 0
    critical_unknowns: int = 0
    evidence_confidence: float = 0.50
    mutation_threshold: float = 0.60

    @property
    def is_mutation_permitted(self) -> bool:
        """Mass mutation only allowed if critical unknowns are 0 and confidence exceeds threshold."""
        return self.critical_unknowns == 0 and self.evidence_confidence >= self.mutation_threshold


@dataclass
class SituationModel:
    """Rich situational intelligence model maintaining JKAI's real-time ground truth world state."""
    mission_id: str
    initial_hypothesis: str
    immutable_mission_hash: str
    discovered_files: List[str] = field(default_factory=list)
    homogenous_groups: Dict[str, List[str]] = field(default_factory=dict)
    anomalous_items: List[str] = field(default_factory=list)
    known_facts: Dict[str, Any] = field(default_factory=dict)
    unknowns: List[str] = field(default_factory=list)
    assumptions: List[Dict[str, Any]] = field(default_factory=list)
    expected_vs_actual: List[ExpectedVsActual] = field(default_factory=list)
    current_granularity: ActionGranularity = ActionGranularity.PROBE
    strategy_confidence: StrategyConfidenceTracker = field(default_factory=StrategyConfidenceTracker)
    uncertainty_budget: UncertaintyBudget = field(default_factory=UncertaintyBudget)
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
    recovery_action: RecoveryAction = RecoveryAction.REPLAN
    next_action_target: Optional[str] = None
    replan_instructions: Optional[str] = None
    escalate_to_deep: bool = False
    safe_stop_reason: Optional[str] = None
    provenance_trace: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
