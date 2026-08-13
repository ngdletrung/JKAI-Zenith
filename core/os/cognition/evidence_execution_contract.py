"""
Evidence Execution Contract (EEC v1.0) & Grounded Epistemic Substrate
=============================================================================
Defines the 10 Evidence Execution Contracts (EEC-1 to EEC-10),
5-entity separation (ClaimRecord, ActionRecord, ObservationRecord, VerificationRecord, EvidenceRecord),
Per-Capability EvidenceRequirement, EvidenceLevel (E1..E3), and Pipeline-Agnostic EvidenceGateAuditor.
=============================================================================
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ─────────────────────────────────────────────────────────────────────────────
# 1. ENUMS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

class EvidencePolicy(str, Enum):
    OPTIONAL = "OPTIONAL"      # General conversation, conceptual inquiry
    REQUIRED = "REQUIRED"      # Self-evaluation, critical operations, audit tasks


class EvidenceLevel(str, Enum):
    E1_OBSERVED = "E1_OBSERVED"                             # Tool executed with observable returncode/stdout
    E2_VERIFIED = "E2_VERIFIED"                             # Direct read-back / schema check matches
    E3_INDEPENDENTLY_VERIFIED = "E3_INDEPENDENTLY_VERIFIED" # Deterministic verifier / unit test confirms


class CapabilityDimension(str, Enum):
    REASONING_LOGIC = "REASONING_LOGIC"
    TOOL_FILE_ACTUATION = "TOOL_FILE_ACTUATION"
    ADAPTIVE_RECOVERY = "ADAPTIVE_RECOVERY"
    EPISTEMIC_HUMILITY = "EPISTEMIC_HUMILITY"
    LONG_HORIZON_AUTONOMY = "LONG_HORIZON_AUTONOMY"
    EXTERNAL_WEB_RECON = "EXTERNAL_WEB_RECON"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    VERIFICATION_BLOCKED = "VERIFICATION_BLOCKED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


class EvidenceGateVerdict(str, Enum):
    TERMINATE_WITH_PROOF = "TERMINATE_WITH_PROOF"
    RECOVERY = "RECOVERY"
    LOW_CONFIDENCE_CONCLUSION = "LOW_CONFIDENCE_CONCLUSION"
    VERIFICATION_BLOCKED = "VERIFICATION_BLOCKED"


# ─────────────────────────────────────────────────────────────────────────────
# 2. EVIDENCE REQUIREMENT CONTRACT (Per-Capability / Test Acceptance Criteria)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvidenceRequirement:
    """
    Per-Capability Specification of what constitutes valid proof.
    E2 is sufficient for File/IO, E3 required for deterministic reasoning.
    """
    capability: CapabilityDimension
    required_level: EvidenceLevel = EvidenceLevel.E2_VERIFIED
    verification_required: bool = True
    independent_verifier_required: bool = False
    min_evidence_count: int = 1
    acceptance_criteria: str = ""
    failure_policy: str = "RECOVERY"  # RECOVERY, SAFE_STOP, LOW_CONFIDENCE


# ─────────────────────────────────────────────────────────────────────────────
# 3. 5-ENTITY SEPARATION SCHEMAS (EEC-4 & EEC-10)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClaimRecord:
    """
    Separated Claim Record (E0) representing an assertion by the model.
    Not an EvidenceRecord to prevent accidental evidence inflation.
    """
    claim_id: str
    capability: CapabilityDimension
    statement: str
    is_supported: bool = False
    supporting_evidence_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ActionRecord:
    """Immutable record of an attempted action."""
    action_id: str
    tool_name: str
    input_args: Dict[str, Any]
    target_capability: CapabilityDimension
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ObservationRecord:
    """Immutable record of physical runtime observation."""
    obs_id: str
    action_id: str
    returncode: int
    stdout_summary: str
    stderr_summary: str
    output_bytes: int
    execution_latency_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class VerificationRecord:
    """Immutable record of independent verification."""
    ver_id: str
    action_id: str
    obs_id: str
    verifier_type: str                   # e.g., "AST_PARSER", "READBACK_EXACT_MATCH", "DETERMINISTIC_UNIT_TEST"
    is_independent: bool
    verification_passed: bool
    details: str
    sha256_hash: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class EvidenceRecord:
    """
    Immutable Evidence with 8-link provenance trace (EEC-10).
    Only instantiated from E1 (OBSERVED), E2 (VERIFIED), or E3 (INDEPENDENTLY_VERIFIED).
    """
    evidence_id: str
    action_id: str
    obs_id: str
    ver_id: Optional[str]
    capability: CapabilityDimension
    level: EvidenceLevel
    relevance_tags: List[str]            # EEC-9: Must match tested capability
    provenance_trace: Dict[str, Any]     # mission_id, task_id, trace_id, invocation_id
    summary: str
    is_relevant: bool = True
    timestamp: float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────────────────────────────
# 4. EVIDENCE-PRODUCING ACTION (EPA) CONTAINER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceProducingAction:
    """
    Structured EPA Container coordinating the epistemic records.
    """
    epa_id: str
    capability_under_test: CapabilityDimension
    test_proposition: str
    expected_observation: str
    requirement: EvidenceRequirement = field(
        default_factory=lambda: EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)
    )
    claim: Optional[ClaimRecord] = None
    action: Optional[ActionRecord] = None
    observation: Optional[ObservationRecord] = None
    verification: Optional[VerificationRecord] = None
    evidence: Optional[EvidenceRecord] = None
    status: VerificationStatus = VerificationStatus.PENDING

    def register_claim(self, statement: str) -> ClaimRecord:
        c = ClaimRecord(
            claim_id=f"CLM_{uuid.uuid4().hex[:8]}",
            capability=self.capability_under_test,
            statement=statement
        )
        self.claim = c
        return c

    def attach_action(self, tool_name: str, input_args: Dict[str, Any]) -> ActionRecord:
        act = ActionRecord(
            action_id=f"ACT_{uuid.uuid4().hex[:8]}",
            tool_name=tool_name,
            input_args=input_args,
            target_capability=self.capability_under_test
        )
        self.action = act
        return act

    def attach_observation(
        self, returncode: int, stdout: str, stderr: str = "", output_bytes: int = 0, latency_ms: float = 0.0
    ) -> ObservationRecord:
        if not self.action:
            raise ValueError("Cannot attach observation without an action record.")
        obs = ObservationRecord(
            obs_id=f"OBS_{uuid.uuid4().hex[:8]}",
            action_id=self.action.action_id,
            returncode=returncode,
            stdout_summary=stdout[:500],
            stderr_summary=stderr[:500],
            output_bytes=output_bytes,
            execution_latency_ms=latency_ms
        )
        self.observation = obs
        return obs

    def attach_verification(
        self, verifier_type: str, passed: bool, details: str, is_independent: bool = True, sha256_hash: Optional[str] = None
    ) -> VerificationRecord:
        if not self.observation or not self.action:
            raise ValueError("Cannot verify without action and observation records.")
        ver = VerificationRecord(
            ver_id=f"VER_{uuid.uuid4().hex[:8]}",
            action_id=self.action.action_id,
            obs_id=self.observation.obs_id,
            verifier_type=verifier_type,
            is_independent=is_independent,
            verification_passed=passed,
            details=details,
            sha256_hash=sha256_hash
        )
        self.verification = ver
        return ver

    def synthesize_evidence(
        self,
        mission_id: str,
        task_id: str,
        trace_id: str,
        invocation_id: str
    ) -> Optional[EvidenceRecord]:
        """Synthesizes an EvidenceRecord if physical action occurred."""
        if not self.action or not self.observation:
            self.status = VerificationStatus.UNVERIFIED
            return None

        if self.observation.returncode != 0:
            self.status = VerificationStatus.FAILED
            level = EvidenceLevel.E1_OBSERVED
            ver_id = None
        elif not self.verification:
            level = EvidenceLevel.E1_OBSERVED
            ver_id = None
            self.status = VerificationStatus.VERIFICATION_BLOCKED
        elif not self.verification.verification_passed:
            level = EvidenceLevel.E1_OBSERVED
            ver_id = self.verification.ver_id
            self.status = VerificationStatus.FAILED
        elif self.verification.is_independent:
            level = EvidenceLevel.E3_INDEPENDENTLY_VERIFIED
            ver_id = self.verification.ver_id
            self.status = VerificationStatus.VERIFIED
        else:
            level = EvidenceLevel.E2_VERIFIED
            ver_id = self.verification.ver_id
            self.status = VerificationStatus.VERIFIED

        ev = EvidenceRecord(
            evidence_id=f"EV_{uuid.uuid4().hex[:8]}",
            action_id=self.action.action_id,
            obs_id=self.observation.obs_id,
            ver_id=ver_id,
            capability=self.capability_under_test,
            level=level,
            relevance_tags=[self.capability_under_test.value],
            provenance_trace={
                "mission_id": mission_id,
                "task_id": task_id,
                "trace_id": trace_id,
                "invocation_id": invocation_id,
                "epa_id": self.epa_id
            },
            summary=f"EPA {self.epa_id} on {self.capability_under_test.value}: Status={self.status.value}, Level={level.value}"
        )
        self.evidence = ev

        # Link supporting evidence to claim if claim exists
        if self.claim and self.status == VerificationStatus.VERIFIED:
            self.claim = ClaimRecord(
                claim_id=self.claim.claim_id,
                capability=self.claim.capability,
                statement=self.claim.statement,
                is_supported=True,
                supporting_evidence_id=ev.evidence_id,
                timestamp=self.claim.timestamp
            )

        return ev


# ─────────────────────────────────────────────────────────────────────────────
# 5. PIPELINE-AGNOSTIC EVIDENCE GATE AUDITOR (Cognitive Substrate Layer)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceMetrics:
    evidence_efficiency: float         # Verified relevant evidence / Total actions
    evidence_coverage: float           # Verified dimensions meeting requirement / Required dimensions [0.0, 1.0]
    unsupported_claim_rate: float      # Claims with no supporting valid evidence / Total claims
    total_actions: int
    verified_evidence_count: int
    unsupported_claim_count: int


class EvidenceGateAuditor:
    """
    The Single Pipeline-Agnostic Enforcement Point for Evidence-Governed Task Completion.
    Operates at Cognitive Substrate level, serving FAST, DEEP, AUTO, and MULTI-AGENT.
    """

    @staticmethod
    def calculate_metrics(
        epas: List[EvidenceProducingAction],
        requirements: List[EvidenceRequirement]
    ) -> EvidenceMetrics:
        total_actions = sum(1 for epa in epas if epa.action is not None)
        
        # Build capability -> requirement map
        req_map = {req.capability: req for req in requirements}

        # Check which EPAs satisfy their specific capability's required evidence level
        verified_ev = []
        for epa in epas:
            if epa.evidence and epa.status == VerificationStatus.VERIFIED:
                req = req_map.get(epa.capability_under_test)
                min_level = req.required_level if req else EvidenceLevel.E2_VERIFIED
                # Compare level hierarchy (E3 >= E2 >= E1)
                level_order = {EvidenceLevel.E1_OBSERVED: 1, EvidenceLevel.E2_VERIFIED: 2, EvidenceLevel.E3_INDEPENDENTLY_VERIFIED: 3}
                if level_order.get(epa.evidence.level, 0) >= level_order.get(min_level, 2):
                    verified_ev.append(epa.evidence)

        # Count unsupported claims
        claims = [epa.claim for epa in epas if epa.claim is not None]
        unsupported_claims = [c for c in claims if not c.is_supported]

        verified_dims = {ev.capability for ev in verified_ev}
        req_dims = set(req_map.keys())

        req_count = max(len(req_dims), 1)
        tot_act_count = max(total_actions, 1)
        tot_claims = max(len(claims), 1)

        ee = round(len(verified_ev) / tot_act_count, 3)
        ec = min(1.0, round(len(verified_dims.intersection(req_dims)) / req_count, 3))
        ucr = round(len(unsupported_claims) / tot_claims, 3) if claims else 0.0

        return EvidenceMetrics(
            evidence_efficiency=ee,
            evidence_coverage=ec,
            unsupported_claim_rate=ucr,
            total_actions=total_actions,
            verified_evidence_count=len(verified_ev),
            unsupported_claim_count=len(unsupported_claims)
        )

    @staticmethod
    def audit_completion(
        policy: EvidencePolicy,
        epas: List[EvidenceProducingAction],
        requirements: Optional[List[EvidenceRequirement]] = None,
        target_capability: Optional[CapabilityDimension] = None
    ) -> Dict[str, Any]:
        """
        Evaluates proposed completion against EEC invariants and specific EvidenceRequirements.
        """
        req_list = requirements or []

        # EEC-6: If Policy is OPTIONAL, standard completion allowed
        if policy == EvidencePolicy.OPTIONAL:
            return {
                "verdict": EvidenceGateVerdict.TERMINATE_WITH_PROOF,
                "reason": "Evidence policy is OPTIONAL for this conversational inquiry.",
                "verified_dimensions": [],
                "unverified_dimensions": [],
                "metrics": None
            }

        # Policy == REQUIRED: Strict Evidence Evaluation
        metrics = EvidenceGateAuditor.calculate_metrics(epas, req_list)

        # 1. EEC-6: No Evidence -> No Completion (Rejection)
        if metrics.verified_evidence_count == 0:
            has_blocked = any(epa.status == VerificationStatus.VERIFICATION_BLOCKED for epa in epas)
            if has_blocked:
                return {
                    "verdict": EvidenceGateVerdict.VERIFICATION_BLOCKED,
                    "reason": "EEC-6 & EEC-8: Actions executed but verification requirement not satisfied (VERIFICATION_BLOCKED).",
                    "metrics": metrics
                }
            return {
                "verdict": EvidenceGateVerdict.RECOVERY,
                "reason": "EEC-6 Violation: Mission requires evidence but verified evidence count is 0. Kicking off recovery.",
                "metrics": metrics
            }

        # 2. EEC-9: Relevance Check
        if target_capability:
            matching_ev = [
                epa.evidence for epa in epas
                if epa.evidence and epa.evidence.capability == target_capability and epa.status == VerificationStatus.VERIFIED
            ]
            if not matching_ev:
                return {
                    "verdict": EvidenceGateVerdict.RECOVERY,
                    "reason": f"EEC-9 Violation: Generated evidence does not match target capability {target_capability.value}.",
                    "metrics": metrics
                }

        # 3. EEC-8: Epistemic Humility (Coverage Check)
        verified_dims = {
            epa.evidence.capability for epa in epas
            if epa.evidence and epa.status == VerificationStatus.VERIFIED
        }
        req_dims = {r.capability for r in req_list}
        unverified_dims = list(req_dims - verified_dims)

        if metrics.evidence_coverage < 1.0 and req_dims:
            return {
                "verdict": EvidenceGateVerdict.LOW_CONFIDENCE_CONCLUSION,
                "reason": f"EEC-7 & EEC-8: Partial evidence coverage ({metrics.evidence_coverage*100}%). Unverified capabilities: {unverified_dims}.",
                "verified_dimensions": list(verified_dims),
                "unverified_dimensions": unverified_dims,
                "metrics": metrics
            }

        # 4. Full Satisfaction
        return {
            "verdict": EvidenceGateVerdict.TERMINATE_WITH_PROOF,
            "reason": f"EEC v1.0 Passed: {metrics.verified_evidence_count} verified evidence records satisfying all required capabilities.",
            "verified_dimensions": list(verified_dims),
            "unverified_dimensions": [],
            "metrics": metrics
        }
