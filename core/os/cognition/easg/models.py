"""
core/os/cognition/easg/models.py
Evidence Applicability & Source Governance (EASG) — Canonical Data Models.

Adheres to:
- Axiom 9: Valid evidence is not necessarily applicable or authorized evidence.
- Hierarchy: VALID != APPLICABLE != AUTHORIZED FOR USE.
- 4-State Applicability: APPLICABLE, INAPPLICABLE, UNKNOWN, CONDITIONAL.
- Anti-Evidence-Laundering Lineage & D13 Independence Clustering.
"""

from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class SourceTier(str, Enum):
    INTERNAL_MASTER_DIRECTIVE = "INTERNAL_MASTER_DIRECTIVE"  # Authority: 1.00
    INTERNAL_ORGANIZATION_POLICY = "INTERNAL_ORGANIZATION_POLICY"  # Authority: 0.95
    INTERNAL_PROJECT_DOC = "INTERNAL_PROJECT_DOC"  # Authority: 0.85
    EXTERNAL_OFFICIAL_DOCS = "EXTERNAL_OFFICIAL_DOCS"  # Authority: 0.90
    EXTERNAL_ACADEMIC_PEER_REVIEWED = "EXTERNAL_ACADEMIC_PEER_REVIEWED"  # Authority: 0.85
    EXTERNAL_VENDOR_KB = "EXTERNAL_VENDOR_KB"  # Authority: 0.80
    EXTERNAL_COMMUNITY_VERIFIED = "EXTERNAL_COMMUNITY_VERIFIED"  # Authority: 0.60
    EXTERNAL_UNTRUSTED_BLOG = "EXTERNAL_UNTRUSTED_BLOG"  # Authority: 0.20
    LLM_SYNTHESIZED_TEXT = "LLM_SYNTHESIZED_TEXT"  # Authority: 0.00 (Strictly NOT independent evidence)


class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    INAPPLICABLE = "INAPPLICABLE"
    UNKNOWN = "UNKNOWN"
    CONDITIONAL = "CONDITIONAL"


class HardGateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONDITIONAL = "CONDITIONAL"


@dataclass
class LineageRecord:
    """Provenance audit record preventing Evidence Laundering (D13/D20)."""
    origin_uri: str
    artifact_id: str
    derivation_chain: List[str] = field(default_factory=list) # e.g. ["blog_a", "agent_1", "agent_2"]
    root_cluster_id: str = ""
    is_laundered: bool = False

    def compute_cluster_id(self) -> str:
        root = self.origin_uri.strip().lower()
        self.root_cluster_id = f"cluster_{hashlib.sha256(root.encode()).hexdigest()[:12]}"
        return self.root_cluster_id


@dataclass
class HardGateResult:
    """Deterministic result of Hard Gate checks (cannot be overridden by soft score)."""
    status: HardGateStatus
    passed_gates: List[str] = field(default_factory=list)
    failed_gates: List[str] = field(default_factory=list)
    conditions_required: List[str] = field(default_factory=list)
    failure_details: Optional[str] = None


@dataclass
class CandidateEvidence:
    """Incoming evidence candidate with full provenance and confidentiality metadata."""
    candidate_id: str
    content: str
    source_uri: str
    source_tier: SourceTier
    provenance_owner: str
    jurisdiction: str
    department: Optional[str] = None
    effective_year: int = 2026
    is_expired: bool = False
    confidentiality_level: str = "PUBLIC" # PUBLIC, INTERNAL, RESTRICTED, TOP_SECRET
    tenant_id: str = "default_tenant"
    lineage: Optional[LineageRecord] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def get_lineage(self) -> LineageRecord:
        if not self.lineage:
            self.lineage = LineageRecord(
                origin_uri=self.source_uri,
                artifact_id=f"art_{self.candidate_id}",
                derivation_chain=[self.source_uri]
            )
            self.lineage.compute_cluster_id()
        return self.lineage


@dataclass
class EvidenceApplicabilityProfile:
    """Comprehensive evaluation profile of an evidence candidate."""
    evidence_id: str
    candidate_id: str
    source_tier: SourceTier
    applicability_state: ApplicabilityState
    hard_gate_result: HardGateResult
    authority_score: float # 0.0 to 1.0
    freshness_score: float # 0.0 to 1.0
    specificity_score: float # 0.0 to 1.0
    overall_ranking_score: float # 0.0 to 1.0
    policy_authorized: bool = False # Usage Authorization Gate
    policy_restriction_reason: Optional[str] = None
    primary_role: str = "SUPPORTING" # PRIMARY_AUTHORITY, SUPPORTING, COMPARATIVE, QUARANTINED, REJECTED
    bound_criteria: List[str] = field(default_factory=list)

    @property
    def is_applicable(self) -> bool:
        return self.applicability_state == ApplicabilityState.APPLICABLE

    @property
    def is_admitted(self) -> bool:
        return self.source_tier != SourceTier.LLM_SYNTHESIZED_TEXT

    @property
    def rejection_reason(self) -> Optional[str]:
        return self.hard_gate_result.failure_details or self.policy_restriction_reason


@dataclass
class EvidenceUsageRecord:
    """Epistemic usage audit trail explaining 'Why this evidence was selected'."""
    record_id: str
    mission_id: str
    selected_evidence_id: str
    used_for_criterion: str
    reason_for_use: str
    authority_level: str
    applicability_state: str
    ranking_score: float
    cluster_id: str
    alternatives_considered: List[str] = field(default_factory=list)
    rejected_sources: List[Dict[str, str]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def applicability_score(self) -> float:
        return self.ranking_score
