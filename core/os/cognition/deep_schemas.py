"""
JKAI ZENITH AI OS — DEEP v2.2 CANONICAL SCHEMAS (PHASE 1)
File: core/os/cognition/deep_schemas.py

Defines the canonical, typed, machine-enforced data structures for:
- 5-Layer Truth Separation Architecture (Observation -> Evidence -> Belief -> Decision -> Verification Evidence)
- Resource Reservation & Capability Tokens
- Evidence Quality Vector & Revocation Lineage
- PlanDeltaContract & MissionOutcome
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Set
import hashlib
import json
import time


# ============================================================================
# 1. ENUMS FOR CANONICAL STATE & ADMISSION
# ============================================================================

class CriterionStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    VERIFIED = "VERIFIED"
    FALSIFIED = "FALSIFIED"


class AdmissionStatus(str, Enum):
    ADMIT = "ADMIT"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


class BeliefFreshnessStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    INVALID = "INVALID"
    REVOKED = "REVOKED"


class CognitiveDecisionType(str, Enum):
    PROCEED = "PROCEED"
    PRUNE = "PRUNE"
    REPLAN = "REPLAN"
    BLOCK = "BLOCK"
    ABORT = "ABORT"


class CapabilityType(str, Enum):
    WORKTREE_WRITE = "WORKTREE_WRITE"
    NETWORK_EGRESS = "NETWORK_EGRESS"
    OS_EXEC = "OS_EXEC"
    DATABASE_MUTATION = "DATABASE_MUTATION"


class IdempotencyStatus(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class RecoveryPolicyType(str, Enum):
    RETRY = "RETRY"
    RECONCILE = "RECONCILE"
    ROLLBACK = "ROLLBACK"
    REPLAN = "REPLAN"
    PRUNE = "PRUNE"
    ESCALATE = "ESCALATE"
    WAIT_FOR_EVIDENCE = "WAIT_FOR_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ABORT = "ABORT"


class MissionOutcomeStatus(str, Enum):
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    COMPLETED_WITH_LIMITATIONS = "COMPLETED_WITH_LIMITATIONS"
    BLOCKED = "BLOCKED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    FAILED_EXECUTION = "FAILED_EXECUTION"
    ABORTED_SAFETY = "ABORTED_SAFETY"
    UNRESOLVED = "UNRESOLVED"


# ============================================================================
# 2. EVIDENCE QUALITY VECTOR & OBSERVATION / CLAIM SCHEMAS
# ============================================================================

@dataclass
class EvidenceQualityVector:
    """Multi-dimensional evidence evaluation vector (P0-1 & D9 Refinement)."""
    reliability: float = 0.5        # [0.0, 1.0] Source intrinsic reliability
    provenance_score: float = 0.5   # [0.0, 1.0] Direct primary source vs multi-hop
    independence: float = 1.0       # [0.0, 1.0] Based on causal lineage clustering
    freshness: float = 1.0          # [0.0, 1.0] Decay over wallclock/state shifts
    directness: float = 0.5         # [0.0, 1.0] Direct measurement vs inferred
    reproducibility: float = 0.5    # [0.0, 1.0] Can be deterministically reproduced
    verification_level: float = 0.0 # [0.0, 1.0] 1.0 for deterministic test verified
    contradiction_level: float = 0.0# [0.0, 1.0] Conflict penalty with existing ledger

    @property
    def composite_strength(self) -> float:
        """Calculates weighted strength score bounded in [0.0, 1.0]."""
        base = (
            self.reliability * 0.25 +
            self.provenance_score * 0.20 +
            self.independence * 0.20 +
            self.freshness * 0.15 +
            self.verification_level * 0.20
        )
        penalty = self.contradiction_level * 0.30
        return max(0.0, min(1.0, base - penalty))


@dataclass
class ToolExecutionRecord:
    """Structured record of tool execution before Observation ingestion (P1-1)."""
    execution_id: str
    mission_id: str
    trace_id: str
    node_id: str
    tool_id: str
    tool_version: str
    capability_token: str
    input_hash: str
    output_hash: str
    stdout_hash: str
    stderr_hash: str
    exit_code: int
    context_hash: str
    mutation_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    ended_at: float = field(default_factory=time.time)


@dataclass
class Observation:
    """Raw agent or tool observation. Belongs strictly to DATA PLANE."""
    observation_id: str
    source_id: str
    agent_id: str
    raw_content: str
    tool_execution: Optional[ToolExecutionRecord] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Claim:
    """Specific factual or causal assertion extracted from an Observation."""
    claim_id: str
    extracted_from_observation_id: str
    assertion: str
    bound_criterion_id: Optional[str] = None
    is_falsified: bool = False
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvidenceRecord:
    """Admitted evidence item in the append-only Evidence Ledger (D3, D13, D20, D25)."""
    evidence_id: str
    claim_id: str
    source_id: str
    provenance_lineage: List[str]   # Full chain of ancestors e.g. ["doc_v1", "agent_A", "agent_B"]
    independence_cluster: str       # Group ID for collapsing shared lineage
    quality: EvidenceQualityVector
    admission_status: AdmissionStatus
    revoked: bool = False
    invalidated_by: Optional[str] = None
    admission_reason: str = "VALID_PROVENANCE"
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 3. BELIEF STATE & REVISION (EVENT SOURCING & CAS)
# ============================================================================

@dataclass
class BeliefRevision:
    """Event-sourced record of a state change in BeliefState (D22, D28, P1-4)."""
    event_id: str
    mission_id: str
    version: int
    prev_version: int
    trigger_evidence_ids: List[str]
    supporting_evidence_ids: List[str]
    contradicting_evidence_ids: List[str]
    changed_hypotheses: Dict[str, float]
    freshness_status: BeliefFreshnessStatus = BeliefFreshnessStatus.FRESH
    revision_reason: str = "NEW_EVIDENCE_ADMITTED"
    timestamp: float = field(default_factory=time.time)


@dataclass
class BeliefState:
    """Versioned epistemic state of the cognitive runtime (D14, D26)."""
    mission_id: str
    version: int = 1
    cas_token: str = ""
    hypotheses: Dict[str, float] = field(default_factory=dict) # hypothesis_id -> confidence
    criterion_coverage: Dict[str, CriterionStatus] = field(default_factory=dict)
    staleness_map: Dict[str, BeliefFreshnessStatus] = field(default_factory=dict)
    last_revision_event_id: Optional[str] = None

    def __post_init__(self):
        if not self.cas_token:
            self.cas_token = hashlib.sha256(f"{self.mission_id}:{self.version}".encode()).hexdigest()[:16]


# ============================================================================
# 4. DECISION, CAPABILITY & GOVERNANCE SCHEMAS
# ============================================================================

@dataclass
class CognitiveDecision:
    """Strategic decision produced by ReasoningJudge without mutating BeliefState."""
    decision_id: str
    decision_type: CognitiveDecisionType
    supporting_claims: List[str]
    supporting_evidence: List[str]
    justification: str
    pruned_waves: List[int] = field(default_factory=list)
    replan_required: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class ActionIntent:
    """Intent emitted by agent to request tool execution (D7, D18)."""
    intent_id: str
    mission_id: str
    node_id: str
    operation: str
    target_resource: str
    required_capabilities: List[CapabilityType]
    risk_level: str = "LOW" # LOW, MEDIUM, HIGH, CRITICAL
    idempotency_key: Optional[str] = None


@dataclass
class CapabilityGrant:
    """Scoped, time-bound capability token granted by PolicyGovernor (D18)."""
    grant_id: str
    token: str
    mission_id: str
    node_id: str
    granted_capabilities: List[CapabilityType]
    resource_scope: str
    expires_at: float
    single_use: bool = True
    consumed: bool = False


# ============================================================================
# 5. PLAN DELTA, VERIFICATION CONTEXT & OUTCOME CONTRACTS
# ============================================================================

@dataclass
class PlanDelta:
    """Structural delta between two planning attempts (D6, C4, P0-4)."""
    changed_assumptions: List[str] = field(default_factory=list)
    changed_dependencies: List[str] = field(default_factory=list)
    added_requirements: List[str] = field(default_factory=list)
    removed_steps: List[str] = field(default_factory=list)
    altered_strategy: bool = False
    semantic_similarity: float = 0.0

    @property
    def is_valid_structural_delta(self) -> bool:
        """Enforces that replan is not a fake replan."""
        has_structural_change = bool(
            self.changed_assumptions or
            self.changed_dependencies or
            self.added_requirements or
            self.removed_steps or
            self.altered_strategy
        )
        return has_structural_change or (self.semantic_similarity < 0.85)


@dataclass
class VerificationContextHash:
    """Deterministic hash of the full execution environment for freshness (D19, D31, P0-3)."""
    git_head: str
    changed_files_hash: str
    lockfile_hash: str
    env_hash: str
    config_hash: str
    tool_versions_hash: str
    verifier_version: str

    @property
    def composite_hash(self) -> str:
        payload = f"{self.git_head}:{self.changed_files_hash}:{self.lockfile_hash}:{self.env_hash}:{self.config_hash}:{self.tool_versions_hash}:{self.verifier_version}"
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class MissionCriterion:
    """Immutable success criterion of a mission (D1, D21)."""
    criterion_id: str
    description: str
    status: CriterionStatus = CriterionStatus.UNVERIFIED
    supporting_evidence_ids: List[str] = field(default_factory=list)
    verification_hash: Optional[str] = None


@dataclass
class MissionOutcome:
    """Canonical completion record produced by MissionCompletionGate (P1-5)."""
    mission_id: str
    status: MissionOutcomeStatus
    success_criteria_total: int
    success_criteria_verified: int
    success_criteria_unresolved: int
    verification_context_hash: str
    evidence_count: int
    total_tokens_consumed: int
    total_vram_peak_mb: int
    total_wallclock_ms: int
    timestamp: float = field(default_factory=time.time)
