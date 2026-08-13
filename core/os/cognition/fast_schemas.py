"""
core/os/cognition/fast_schemas.py
FAST v2.2 Canonical Schemas and Epistemic Primitives.

Adheres strictly to the 8 Core Axioms:
1. Mission Invariant (CanonicalGoal is immutable).
2. Ingress Hygiene (CanonicalGoal != SystemContext != SkillDossier).
3. Decision != Authorization (ActionIntent requires Governor CapabilityGrant).
4. Observation != Truth (Tool execution yields ToolExecutionRecord/Observation, not Verified Success).
5. Execution != Completion (Requires Deterministic FastVerificationRecord).
6. Freshness Check (Context Hash & Artifact Hash must match).
"""

from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class IntentCategory(str, Enum):
    ACTION = "ACTION"
    QUERY = "QUERY"
    CHAT = "CHAT"
    META = "META"


class TaskDomain(str, Enum):
    OFFICE = "OFFICE"
    CODE = "CODE"
    SYSTEM = "SYSTEM"
    RESEARCH = "RESEARCH"
    GENERAL = "GENERAL"


class MutationScope(str, Enum):
    NONE = "NONE"
    SINGLE_FILE = "SINGLE_FILE"
    MULTI_FILE = "MULTI_FILE"
    SYSTEM_STATE = "SYSTEM_STATE"


@dataclass(frozen=True)
class CanonicalGoal:
    """Immutable user goal preserved identically across all routers, profilers, and gates."""
    raw_text: str
    cleaned_goal: str
    goal_hash: str
    user_constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, raw_text: str) -> CanonicalGoal:
        cleaned = raw_text.strip()
        g_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]
        return cls(
            raw_text=raw_text,
            cleaned_goal=cleaned,
            goal_hash=g_hash,
        )


@dataclass
class SystemContext:
    """Isolated runtime metadata, skill dossiers, and hardware specs that NEVER contaminate CanonicalGoal."""
    available_skills: List[str] = field(default_factory=list)
    active_dossiers: Dict[str, str] = field(default_factory=dict)
    hardware_profile: Dict[str, Any] = field(default_factory=dict)
    session_variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FastTaskProfile:
    """Multi-dimensional cognitive profile for FAST routing."""
    intent: IntentCategory = IntentCategory.ACTION
    domain: TaskDomain = TaskDomain.GENERAL
    operation: str = "EXECUTE"
    artifact_type: Optional[str] = None # XLSX, DOCX, PDF, PY, JSON, etc.
    requires_mutation: bool = False
    mutation_scope: MutationScope = MutationScope.NONE
    complexity: str = "SINGLE_ACTION"   # SINGLE_ACTION, MICRO_PLAN, COMPLEX_DEEP
    verification_required: bool = True
    target_entity: str = "AI_SELF"      # AI_SELF, USER, SYSTEM
    reason_codes: List[str] = field(default_factory=list)


@dataclass
class ActionIntent:
    """Proposed action from LLM/Cognitive Worker before Governor authorization."""
    intent_id: str
    action_name: str
    target_domain: TaskDomain
    parameters: Dict[str, Any]
    mutation: bool = False
    target_path: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    proposed_at: float = field(default_factory=time.time)


@dataclass
class CapabilityGrant:
    """Authoritative grant issued by the Governor. Decision != Authorization."""
    grant_id: str
    intent_id: str
    allowed: bool
    granted_capabilities: Set[str] = field(default_factory=set) # WORKTREE_WRITE, FILE_CREATE, etc.
    denied_capabilities: Set[str] = field(default_factory=set)
    sandbox_path: Optional[str] = None
    reason: str = "APPROVED"
    granted_at: float = field(default_factory=time.time)


@dataclass
class ToolExecutionRecord:
    """Raw execution result from sandbox/tool. Observation != Truth."""
    execution_id: str
    tool_name: str
    input_hash: str
    output_hash: str
    stdout: str
    stderr: str
    exit_code: int
    context_hash: str
    artifact_path: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FastVerificationEvidence:
    """Individual deterministic verification point."""
    name: str
    passed: bool
    details: str
    evidence_hash: str


@dataclass
class FastVerificationRecord:
    """Deterministic verification result. Verification != Belief."""
    is_verified: bool
    evidence_list: List[FastVerificationEvidence] = field(default_factory=list)
    artifact_path: Optional[str] = None
    artifact_sha256: Optional[str] = None
    failure_class: Optional[str] = None # ARTIFACT_MISSING, MALFORMED, CONTENT_INCOMPLETE
    recovery_hint: Optional[str] = None
    verified_at: float = field(default_factory=time.time)
