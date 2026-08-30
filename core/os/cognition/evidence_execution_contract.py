"""
Evidence Execution Contract (EEC v2.0) — Self-Proving Substrate
================================================================================
Implements the 5-layer Self-Proving Architecture:

  Layer 1: PROPOSITION LAYER       — What must be proven?
  Layer 2: EVIDENCE REQUIREMENT    — What evidence is sufficient?
  Layer 3: EVIDENCE EXECUTION (EET) — Action → Observation (causal chain)
  Layer 4: INDEPENDENT VERIFICATION — Observation → Verification
  Layer 5: EVIDENCE GATE           — Evidence → admissible conclusion

Key changes from v1.0:
  ① EvidencePolicy: OPTIONAL / REQUIRED / REQUIRED_INDEPENDENT / REQUIRED_MULTI_SOURCE
  ② EPA renamed to EET (Evidence Execution Trace) — EPA is an action *within* a trace
  ③ EvidenceRequirement: full proposition-linked contract
  ④ EvidenceRecord: nối vào 8-link identity chain + hash chain
  ⑤ EvidenceStrength: Level × Validity × Relevance × Coverage × Freshness × Independence
  ⑥ CompletionState: ABSTAIN, EVIDENCE_INVALID, EVIDENCE_STALE, EVIDENCE_IRRELEVANT
  ⑦ UCR split into UCR-S (unsupported) and UCR-F (false-supported)
  ⑧ Independent verifier: must NOT read same mutable state as writer
  ⑨ Completion authority: Kernel-only via CompletionVerdict — LLM cannot set COMPLETED
================================================================================
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# Constitutional Invariant Symbol (Runtime-verifiable)
NO_EVIDENCE_NO_COMPLETION: str = "EEC-6:NO_EVIDENCE_NO_COMPLETION"


class EvidencePolicy(str, Enum):
    """Governs what strength of evidence is required for a task completion."""
    OPTIONAL              = "OPTIONAL"              # General conversation; E0/E1 acceptable
    REQUIRED              = "REQUIRED"              # File/IO mutation; needs E2
    REQUIRED_INDEPENDENT  = "REQUIRED_INDEPENDENT"  # Logic/algorithm; needs E3
    REQUIRED_MULTI_SOURCE = "REQUIRED_MULTI_SOURCE"  # DB migration, multi-dimension; needs E3 × N dims


class EvidenceLevel(str, Enum):
    """Ordered epistemic level. E3 > E2 > E1 > E0."""
    E0_CLAIM                 = "E0_CLAIM"                  # LLM assertion — NOT evidence
    E1_OBSERVED              = "E1_OBSERVED"                # Tool executed, returncode/stdout observed
    E2_VERIFIED              = "E2_VERIFIED"                # Readback / schema check matches expected
    E3_INDEPENDENTLY_VERIFIED = "E3_INDEPENDENTLY_VERIFIED" # Deterministic verifier / unit test confirms


_LEVEL_ORDER: Dict[EvidenceLevel, int] = {
    EvidenceLevel.E0_CLAIM: 0,
    EvidenceLevel.E1_OBSERVED: 1,
    EvidenceLevel.E2_VERIFIED: 2,
    EvidenceLevel.E3_INDEPENDENTLY_VERIFIED: 3,
}


def level_gte(a: EvidenceLevel, b: EvidenceLevel) -> bool:
    """Returns True if level a >= level b."""
    return _LEVEL_ORDER.get(a, 0) >= _LEVEL_ORDER.get(b, 0)


class CapabilityDimension(str, Enum):
    REASONING_LOGIC       = "REASONING_LOGIC"
    TOOL_FILE_ACTUATION   = "TOOL_FILE_ACTUATION"
    ADAPTIVE_RECOVERY     = "ADAPTIVE_RECOVERY"
    EPISTEMIC_HUMILITY    = "EPISTEMIC_HUMILITY"
    LONG_HORIZON_AUTONOMY = "LONG_HORIZON_AUTONOMY"
    EXTERNAL_WEB_RECON    = "EXTERNAL_WEB_RECON"
    CODE_EXECUTION        = "CODE_EXECUTION"
    DATABASE_MUTATION     = "DATABASE_MUTATION"
    SELF_EVALUATION       = "SELF_EVALUATION"


class VerificationStatus(str, Enum):
    """Status within a single EET (Evidence Execution Trace)."""
    PENDING               = "PENDING"
    VERIFIED              = "VERIFIED"
    VERIFICATION_BLOCKED  = "VERIFICATION_BLOCKED"   # No verifier available — unknown outcome
    EVIDENCE_INVALID      = "EVIDENCE_INVALID"        # Verifier ran and returned FAIL — known bad
    EVIDENCE_STALE        = "EVIDENCE_STALE"          # Freshness expired since observed_at
    EVIDENCE_IRRELEVANT   = "EVIDENCE_IRRELEVANT"     # Evidence does not match required dimension
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"   # Level below requirement
    FAILED                = "FAILED"                  # Action itself failed (returncode != 0)
    UNVERIFIED            = "UNVERIFIED"              # No action was taken


class VerifierIndependenceClass(str, Enum):
    """
    Classifies whether a verifier is truly independent.
    STRONG: reads from physical source (filesystem bytes, independent DB query)
    WEAK:   reads from same memory state as writer (unreliable)
    INVALID: reads from same mutable state used to produce the claim — not independent
    """
    STRONG  = "STRONG"
    WEAK    = "WEAK"
    INVALID = "INVALID"


class CompletionState(str, Enum):
    """
    Completion states derivable by EvidenceGate (Kernel-only).
    LLM/controller CANNOT set these directly.
    """
    VERIFIED              = "VERIFIED"               # All ProofObligations satisfied
    ABSTAIN               = "ABSTAIN"                # Policy REQUIRED but obligations unresolvable
    LOW_CONFIDENCE        = "LOW_CONFIDENCE"          # Evidence present but coverage < 100%
    INCOMPLETE            = "INCOMPLETE"              # EC < required threshold
    RECOVERY              = "RECOVERY"                # Gate failed, recovery required
    VERIFICATION_PENDING  = "VERIFICATION_PENDING"    # Awaiting verifier
    VERIFICATION_BLOCKED  = "VERIFICATION_BLOCKED"    # No verifier — outcome unknown
    EVIDENCE_INVALID      = "EVIDENCE_INVALID"        # Verifier said FAIL
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"   # Level below minimum
    EVIDENCE_IRRELEVANT   = "EVIDENCE_IRRELEVANT"     # Evidence doesn't match proposition
    EVIDENCE_STALE        = "EVIDENCE_STALE"          # TTL/time-based freshness expired
    EVIDENCE_INVALIDATED  = "EVIDENCE_INVALIDATED"    # Underlying resource changed post-verification
                                                      # (resource_version mismatch — stronger than STALE)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: PROPOSITION & EVIDENCE REQUIREMENT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Proposition:
    """
    An atomic claim about system state that must be proven.
    LLM does NOT write propositions — they come from PropositionRegistry.
    """
    proposition_id: str          # e.g. "FILE_CONTENT_CORRECT"
    description: str             # Human-readable statement of what must be true
    capability_dimension: CapabilityDimension
    minimum_level: EvidenceLevel = EvidenceLevel.E2_VERIFIED
    required_verifier: str = ""  # e.g. "filesystem_readback", "pytest_runner", "ast_parser"
    required_fields: tuple = field(default_factory=tuple)  # e.g. ("path", "content_hash")


@dataclass(frozen=True)
class EvidenceRequirement:
    """
    Links a Proposition to the minimum evidence that satisfies it.
    Produced from PropositionRegistry at mission planning time.
    """
    requirement_id: str = ""
    proposition: Optional[Proposition] = None
    minimum_level: EvidenceLevel = EvidenceLevel.E2_VERIFIED
    required_verifier: str = ""
    required_fields: tuple = ()
    failure_policy: str = "RECOVERY"   # RECOVERY | SAFE_STOP | ABSTAIN
    multi_source_count: int = 1        # For REQUIRED_MULTI_SOURCE: how many distinct sources

    def __init__(
        self,
        requirement_id: str = "",
        proposition: Optional[Proposition] = None,
        minimum_level: EvidenceLevel = EvidenceLevel.E2_VERIFIED,
        required_verifier: str = "",
        required_fields: tuple = (),
        failure_policy: str = "RECOVERY",
        multi_source_count: int = 1,
        capability: Optional[CapabilityDimension] = None,
        required_level: Optional[EvidenceLevel] = None,
    ):
        if capability is not None:
            min_lvl = required_level or minimum_level
            prop = Proposition(
                proposition_id=capability.value,
                description=capability.value,
                capability_dimension=capability,
                minimum_level=min_lvl,
            )
            object.__setattr__(self, 'requirement_id', requirement_id or f"REQ_{capability.value}")
            object.__setattr__(self, 'proposition', prop)
            object.__setattr__(self, 'minimum_level', min_lvl)
            object.__setattr__(self, 'required_verifier', required_verifier)
            object.__setattr__(self, 'required_fields', required_fields)
            object.__setattr__(self, 'failure_policy', failure_policy)
            object.__setattr__(self, 'multi_source_count', multi_source_count)
        else:
            object.__setattr__(self, 'requirement_id', requirement_id)
            object.__setattr__(self, 'proposition', proposition)
            object.__setattr__(self, 'minimum_level', minimum_level)
            object.__setattr__(self, 'required_verifier', required_verifier)
            object.__setattr__(self, 'required_fields', required_fields)
            object.__setattr__(self, 'failure_policy', failure_policy)
            object.__setattr__(self, 'multi_source_count', multi_source_count)


@dataclass
class ProofObligation:
    """
    Runtime instance: one obligation that must be satisfied before COMPLETED is admitted.
    Only EvidenceGate may set satisfied=True.
    """
    obligation_id: str
    proposition_id: str
    required_level: EvidenceLevel
    required_dimensions: Set[str]      # Set of field names that must be present in EvidenceRecord
    satisfied: bool = False            # SET ONLY BY EvidenceGate — never by LLM/controller
    satisfied_by: Optional[str] = None # evidence_id that satisfied this obligation
    blocked_reason: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: 5-ENTITY RECORD SEPARATION (causal chain, not sibling attributes)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClaimRecord:
    """
    E0 — LLM assertion. Explicitly NOT evidence.
    TypeSafety invariant: ClaimRecord ≠ EvidenceRecord.
    """
    claim_id: str
    capability: CapabilityDimension
    statement: str
    is_supported: bool = False
    supporting_evidence_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ActionRecord:
    """Immutable record of an attempted action (step 1 of causal chain)."""
    action_id: str
    tool_name: str
    input_args: Dict[str, Any]
    target_capability: CapabilityDimension
    mission_id: str = ""
    request_id: str = ""
    plan_id: str = ""
    task_id: str = ""
    attempt_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ObservationRecord:
    """
    Immutable record of physical runtime observation (step 2 of causal chain).
    Must be derived from an external, mutable physical source — NOT from in-memory state.
    """
    obs_id: str
    action_id: str
    returncode: int
    stdout_summary: str
    stderr_summary: str
    output_bytes: int
    execution_latency_ms: float
    # Physical source reference — for independence verification
    observation_source: str = "TOOL_STDOUT"  # TOOL_STDOUT | FILESYSTEM | DB_QUERY | NETWORK
    resource_version: Optional[str] = None   # e.g. file mtime, DB row version
    observed_at: float = field(default_factory=time.time)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class VerificationRecord:
    """
    Immutable record of verification (step 3 of causal chain).
    EEC-5: verifier_independence_class determines if this is truly independent.
    """
    ver_id: str
    action_id: str
    obs_id: str
    verifier_type: str   # "AST_PARSER" | "READBACK_EXACT_MATCH" | "DETERMINISTIC_UNIT_TEST" | etc.
    verification_passed: bool
    details: str
    # Independence — must derive verdict from source NOT used by the writer
    verifier_independence_class: VerifierIndependenceClass = VerifierIndependenceClass.WEAK
    verification_source: str = ""        # Where verifier actually read from
    writer_source: str = ""              # Where writer wrote to — must differ for STRONG
    sha256_hash: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class EvidenceRecord:
    """
    Immutable admissible proof unit with full 8-link identity chain (EEC-10 v2.0).
    Only instantiated when physical action + observation occurred.
    Hash chain: evidence_hash = SHA256(content + previous_evidence_hash)
    """
    # ── Identity: 8-link chain linking to JKAI's canonical mission lineage ──
    evidence_id: str
    mission_id: str
    request_id: str
    plan_id: str
    task_id: str
    attempt_id: str
    action_id: str
    invocation_id: str
    observation_id: str
    verification_id: Optional[str]

    # ── Epistemic fields ──
    capability: CapabilityDimension
    level: EvidenceLevel
    relevance_tags: List[str]       # Must match tested capability (EEC-9)
    summary: str
    is_relevant: bool = True

    # ── Source provenance ──
    source_type: str = "TOOL"       # TOOL | FILESYSTEM | DB | NETWORK | TEST_RUNNER
    source_uri: str = ""
    created_at: float = field(default_factory=time.time)
    observed_at: float = field(default_factory=time.time)

    # ── Integrity ──
    raw_result_hash: str = ""
    verification_hash: str = ""
    evidence_hash: str = ""         # SHA256(content + previous_evidence_hash)
    previous_evidence_hash: str = "GENESIS"  # Hash chain anchor

    # ── Independence ──
    producer: str = ""              # Tool/agent that produced the action
    verifier: str = ""              # Tool/agent that verified
    verifier_independence_class: VerifierIndependenceClass = VerifierIndependenceClass.WEAK

    # ── Freshness ──
    valid_until: Optional[float] = None   # None = expires when mission closes
    resource_version: Optional[str] = None

    # ── Legacy provenance_trace (backward compat with v1.0 tests) ──
    provenance_trace: Dict[str, Any] = field(default_factory=dict)


def _compute_evidence_hash(record: EvidenceRecord) -> str:
    """Computes SHA256 hash of evidence content + previous_evidence_hash."""
    content = (
        f"{record.evidence_id}|{record.mission_id}|{record.task_id}|"
        f"{record.action_id}|{record.observation_id}|{record.level.value}|"
        f"{record.summary}|{record.previous_evidence_hash}"
    )
    return hashlib.sha256(content.encode()).hexdigest()[:32]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: EVIDENCE EXECUTION TRACE (EET)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceExecutionTrace:
    """
    EET (formerly EPA) — Evidence Execution Trace.
    Container for the causal chain: Action → Observation → Verification → Evidence.
    EPA (Evidence-Producing Action) is a single action *within* a trace.

    EEC-5: Independent verifier must derive verdict from a source that is NOT
    the same mutable state used to produce the claimed result.
    """
    eet_id: str
    capability_under_test: CapabilityDimension
    test_proposition: str
    expected_observation: str
    requirement: Optional[EvidenceRequirement] = None

    # Causal chain — populated sequentially
    claim: Optional[ClaimRecord] = None
    action: Optional[ActionRecord] = None
    observation: Optional[ObservationRecord] = None
    verification: Optional[VerificationRecord] = None
    evidence: Optional[EvidenceRecord] = None
    status: VerificationStatus = VerificationStatus.PENDING

    # ── Causal chain methods ─────────────────────────────────────────────────

    def register_claim(self, statement: str) -> ClaimRecord:
        c = ClaimRecord(
            claim_id=f"CLM_{uuid.uuid4().hex[:8]}",
            capability=self.capability_under_test,
            statement=statement
        )
        self.claim = c
        return c

    def attach_action(
        self,
        tool_name: str,
        input_args: Dict[str, Any],
        mission_id: str = "",
        request_id: str = "",
        plan_id: str = "",
        task_id: str = "",
        attempt_id: str = "",
    ) -> ActionRecord:
        act = ActionRecord(
            action_id=f"ACT_{uuid.uuid4().hex[:8]}",
            tool_name=tool_name,
            input_args=input_args,
            target_capability=self.capability_under_test,
            mission_id=mission_id,
            request_id=request_id,
            plan_id=plan_id,
            task_id=task_id,
            attempt_id=attempt_id,
        )
        self.action = act
        return act

    def attach_observation(
        self,
        returncode: int,
        stdout: str,
        stderr: str = "",
        output_bytes: int = 0,
        latency_ms: float = 0.0,
        observation_source: str = "TOOL_STDOUT",
        resource_version: Optional[str] = None,
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
            execution_latency_ms=latency_ms,
            observation_source=observation_source,
            resource_version=resource_version,
        )
        self.observation = obs
        return obs

    def attach_verification(
        self,
        verifier_type: str,
        passed: bool,
        details: str,
        verifier_independence_class: VerifierIndependenceClass = VerifierIndependenceClass.WEAK,
        verification_source: str = "",
        writer_source: str = "",
        sha256_hash: Optional[str] = None,
        is_independent: Optional[bool] = None,
    ) -> VerificationRecord:
        if not self.observation or not self.action:
            raise ValueError("Cannot verify without action and observation records.")

        if is_independent is True:
            verifier_independence_class = VerifierIndependenceClass.STRONG
        elif is_independent is False and verifier_independence_class == VerifierIndependenceClass.WEAK:
            verifier_independence_class = VerifierIndependenceClass.WEAK
        # EEC-5: warn if independence is INVALID
        if (
            verifier_independence_class == VerifierIndependenceClass.STRONG
            and verification_source
            and writer_source
            and verification_source == writer_source
        ):
            verifier_independence_class = VerifierIndependenceClass.INVALID

        ver = VerificationRecord(
            ver_id=f"VER_{uuid.uuid4().hex[:8]}",
            action_id=self.action.action_id,
            obs_id=self.observation.obs_id,
            verifier_type=verifier_type,
            verification_passed=passed,
            details=details,
            verifier_independence_class=verifier_independence_class,
            verification_source=verification_source,
            writer_source=writer_source,
            sha256_hash=sha256_hash,
        )
        self.verification = ver
        return ver

    def synthesize_evidence(
        self,
        mission_id: str,
        task_id: str,
        trace_id: str,
        invocation_id: str,
        request_id: str = "",
        plan_id: str = "",
        attempt_id: str = "",
        previous_evidence_hash: str = "GENESIS",
    ) -> Optional[EvidenceRecord]:
        """
        Synthesizes an EvidenceRecord from the causal chain.
        NEVER called directly by LLM — called by EvidenceGate after causal chain complete.
        """
        if not self.action or not self.observation:
            self.status = VerificationStatus.UNVERIFIED
            return None

        # Determine level and status
        if self.observation.returncode != 0:
            self.status = VerificationStatus.FAILED
            level = EvidenceLevel.E1_OBSERVED
            ver_id = None

        elif not self.verification:
            self.status = VerificationStatus.VERIFICATION_BLOCKED
            level = EvidenceLevel.E1_OBSERVED
            ver_id = None

        elif self.verification.verifier_independence_class == VerifierIndependenceClass.INVALID:
            # EEC-5: verifier collusion detected
            self.status = VerificationStatus.VERIFICATION_BLOCKED
            level = EvidenceLevel.E1_OBSERVED
            ver_id = self.verification.ver_id

        elif not self.verification.verification_passed:
            # EEC-3 / EEC-6: Tool returned success BUT verifier disagrees → EVIDENCE_INVALID
            self.status = VerificationStatus.EVIDENCE_INVALID
            level = EvidenceLevel.E1_OBSERVED
            ver_id = self.verification.ver_id

        elif self.verification.verifier_independence_class == VerifierIndependenceClass.STRONG:
            level = EvidenceLevel.E3_INDEPENDENTLY_VERIFIED
            ver_id = self.verification.ver_id
            self.status = VerificationStatus.VERIFIED

        else:
            level = EvidenceLevel.E2_VERIFIED
            ver_id = self.verification.ver_id
            self.status = VerificationStatus.VERIFIED

        # Build raw_result_hash from observation
        raw_content = f"{self.observation.obs_id}|{self.observation.returncode}|{self.observation.stdout_summary}"
        raw_hash = hashlib.sha256(raw_content.encode()).hexdigest()[:16]

        ver_hash = ""
        if self.verification and self.verification.sha256_hash:
            ver_hash = self.verification.sha256_hash

        ev = EvidenceRecord(
            evidence_id=f"EV_{uuid.uuid4().hex[:8]}",
            mission_id=mission_id,
            request_id=request_id,
            plan_id=plan_id,
            task_id=task_id,
            attempt_id=attempt_id,
            action_id=self.action.action_id,
            invocation_id=invocation_id,
            observation_id=self.observation.obs_id,
            verification_id=ver_id,
            capability=self.capability_under_test,
            level=level,
            relevance_tags=[self.capability_under_test.value],
            summary=(
                f"EET {self.eet_id} on {self.capability_under_test.value}: "
                f"Status={self.status.value}, Level={level.value}"
            ),
            source_type=self.observation.observation_source,
            raw_result_hash=raw_hash,
            verification_hash=ver_hash,
            previous_evidence_hash=previous_evidence_hash,
            producer=self.action.tool_name,
            verifier=self.verification.verifier_type if self.verification else "",
            verifier_independence_class=(
                self.verification.verifier_independence_class
                if self.verification else VerifierIndependenceClass.WEAK
            ),
            resource_version=self.observation.resource_version,
            # backward compat provenance_trace
            provenance_trace={
                "mission_id": mission_id,
                "task_id": task_id,
                "trace_id": trace_id,
                "invocation_id": invocation_id,
                "eet_id": self.eet_id,
                # v1.0 compat key
                "epa_id": self.eet_id,
            },
        )

        # Compute hash chain
        ev_hash = _compute_evidence_hash(ev)
        # Reconstruct with computed hash (frozen dataclass workaround via replace)
        ev = EvidenceRecord(
            **{k: v for k, v in ev.__dict__.items() if k != "evidence_hash"},
            evidence_hash=ev_hash,
        )
        self.evidence = ev

        # Link claim to evidence if claim was registered
        if self.claim and self.status == VerificationStatus.VERIFIED:
            self.claim = ClaimRecord(
                claim_id=self.claim.claim_id,
                capability=self.claim.capability,
                statement=self.claim.statement,
                is_supported=True,
                supporting_evidence_id=ev.evidence_id,
                timestamp=self.claim.timestamp,
            )

        return ev


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: EVIDENCE STRENGTH (EEC-7 formalized)
# ─────────────────────────────────────────────────────────────────────────────

def compute_evidence_strength(
    record: EvidenceRecord,
    relevance: float = 1.0,      # 0.0–1.0: domain relevance
    coverage: float = 1.0,       # 0.0–1.0: coverage of required dimensions
    freshness_ttl_seconds: float = 3600.0,  # 0 = do not check
) -> float:
    """
    EvidenceStrength = Level × Validity × Relevance × Coverage × Freshness × Independence

    Returns a float in [0.0, 1.0]. Zero means inadmissible regardless of level.
    """
    level_scores = {
        EvidenceLevel.E0_CLAIM: 0.0,
        EvidenceLevel.E1_OBSERVED: 0.25,
        EvidenceLevel.E2_VERIFIED: 0.65,
        EvidenceLevel.E3_INDEPENDENTLY_VERIFIED: 1.0,
    }
    level_score = level_scores.get(record.level, 0.0)

    validity = 1.0 if record.is_relevant else 0.0

    freshness = 1.0
    if freshness_ttl_seconds > 0:
        age = time.time() - record.observed_at
        freshness = max(0.0, 1.0 - age / freshness_ttl_seconds)

    independence_scores = {
        VerifierIndependenceClass.STRONG: 1.0,
        VerifierIndependenceClass.WEAK: 0.5,
        VerifierIndependenceClass.INVALID: 0.0,
    }
    independence = independence_scores.get(record.verifier_independence_class, 0.5)

    return round(level_score * validity * relevance * coverage * freshness * independence, 4)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: EVIDENCE METRICS v2.0
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvidenceMetrics:
    # Evidence Efficiency: Verified Evidence Coverage / Execution Cost
    evidence_efficiency: float         # EE = verified_coverage / tool_call_count
    # Evidence Coverage: Verified dims / Required dims
    evidence_coverage: float           # EC = verified_req_dims / total_req_dims  [0.0, 1.0]
    # UCR-S: Claims with no evidence whatsoever
    ucr_s: float                       # Unsupported Claim Rate — no evidence
    # UCR-F: Claims with evidence that doesn't actually support the claim strength required
    ucr_f: float                       # False-Supported Claim Rate — misleading evidence
    total_actions: int
    tool_call_count: int               # Execution cost denominator for EE
    verified_evidence_count: int
    unsupported_claim_count: int       # UCR-S numerator
    false_supported_claim_count: int   # UCR-F numerator


@dataclass
class CompletionVerdict:
    """
    Result of EvidenceGate evaluation.
    ONLY issued by EvidenceGate on behalf of Kernel.
    LLM/controller CANNOT instantiate this directly.

    P2 Verdict Binding:
      Binds to mission_id, ledger_head, evidence_hashes, obligation_ids.
      Prevents cross-mission replay and stale state usage.
    """
    verdict: CompletionState
    evidence_coverage: float            # EC
    ucr_s: float                        # Unsupported
    ucr_f: float                        # False-supported
    proof_obligations_satisfied: int
    proof_obligations_total: int
    gate_fail_reasons: List[str]
    metrics: Optional[EvidenceMetrics] = None
    issued_at: float = field(default_factory=time.time)
    issued_by: str = "EvidenceGate"     # Kernel authority marker
    mission_id: str = ""
    ledger_head: str = ""
    evidence_hashes: List[str] = field(default_factory=list)
    obligation_ids: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: PIPELINE-AGNOSTIC EVIDENCE GATE AUDITOR (v2.0)
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceGateAuditor:
    """
    Cognitive Substrate enforcement point — serves FAST, DEEP, AUTO, MULTI-AGENT.

    v2.0 changes:
      - Accepts ProofObligations (known before execution)
      - Detects EVIDENCE_INVALID vs VERIFICATION_BLOCKED
      - Detects stale evidence (valid_until expired)
      - Detects cross-mission evidence contamination
      - Produces CompletionVerdict — Kernel-only derived state
      - Computes UCR-S and UCR-F separately
      - EvidenceStrength formula applied per record
    """

    @staticmethod
    def check_stale(record: EvidenceRecord) -> bool:
        """Returns True if evidence has exceeded its valid_until TTL."""
        if record.valid_until is None:
            return False
        return time.time() > record.valid_until

    @staticmethod
    def check_cross_mission(record: EvidenceRecord, current_mission_id: str) -> bool:
        """Returns True if evidence belongs to a different mission."""
        return bool(record.mission_id) and record.mission_id != current_mission_id

    @staticmethod
    def check_verifier_independence(record: EvidenceRecord) -> VerifierIndependenceClass:
        """Returns independence classification of the verifier in this record."""
        return record.verifier_independence_class

    @staticmethod
    def calculate_metrics(
        eets: List[EvidenceExecutionTrace],
        requirements: List[EvidenceRequirement],
        mission_id: str = "",
    ) -> EvidenceMetrics:
        # Key by proposition_id for precise EC tracking (not CapabilityDimension,
        # which would conflate multiple requirements on the same dimension)
        req_map = {req.proposition.proposition_id: req for req in requirements}
        req_prop_ids = set(req_map.keys())
        req_caps = {req.proposition.capability_dimension for req in requirements}

        tool_call_count = sum(1 for eet in eets if eet.action is not None)
        verified_ev: List[EvidenceRecord] = []
        false_supported: List[ClaimRecord] = []
        verified_prop_ids: Set[str] = set()

        for eet in eets:
            ev = eet.evidence
            if ev is None:
                continue

            # Skip stale / cross-mission evidence
            if EvidenceGateAuditor.check_stale(ev):
                continue
            if mission_id and EvidenceGateAuditor.check_cross_mission(ev, mission_id):
                continue

            if eet.status == VerificationStatus.VERIFIED:
                # Check level meets requirement for the specific proposition
                req = req_map.get(eet.test_proposition)
                min_lvl = req.minimum_level if req else EvidenceLevel.E2_VERIFIED
                if level_gte(ev.level, min_lvl):
                    # Apply EvidenceStrength — must be > 0
                    strength = compute_evidence_strength(ev)
                    if strength > 0.0:
                        verified_ev.append(ev)
                        # Track by proposition_id for precise EC
                        if eet.test_proposition in req_prop_ids:
                            verified_prop_ids.add(eet.test_proposition)
                    else:
                        # Evidence exists but strength = 0 → false-supported
                        if eet.claim:
                            false_supported.append(eet.claim)

        # UCR-S: claims with no evidence
        all_claims = [eet.claim for eet in eets if eet.claim is not None]
        unsupported = [c for c in all_claims if not c.is_supported]

        tot_claims = max(len(all_claims), 1)
        tool_count = max(tool_call_count, 1)
        # EC denominator: number of required proposition_ids
        req_count = max(len(req_prop_ids), 1)

        # EC = satisfied proposition requirements / total required propositions
        ec = round(len(verified_prop_ids) / req_count, 3)
        ee = round(len(verified_ev) / tool_count, 3)
        ucr_s = round(len(unsupported) / tot_claims, 3)
        ucr_f = round(len(false_supported) / tot_claims, 3) if all_claims else 0.0

        return EvidenceMetrics(
            evidence_efficiency=ee,
            evidence_coverage=ec,
            ucr_s=ucr_s,
            ucr_f=ucr_f,
            total_actions=tool_call_count,
            tool_call_count=tool_call_count,

            verified_evidence_count=len(verified_ev),
            unsupported_claim_count=len(unsupported),
            false_supported_claim_count=len(false_supported),
        )

    @staticmethod
    def audit_completion(
        policy: EvidencePolicy,
        eets: Optional[List[EvidenceExecutionTrace]] = None,
        requirements: Optional[List[EvidenceRequirement]] = None,
        proof_obligations: Optional[List[ProofObligation]] = None,
        target_capability: Optional[CapabilityDimension] = None,
        mission_id: str = "",
        target_mission_id: Optional[str] = None,
        active_resource_version: Optional[str] = None,
        evidence_resource_version: Optional[str] = None,
        max_freshness_seconds: Optional[float] = None,
        # v1.0 compat alias
        epas: Optional[List[EvidenceExecutionTrace]] = None,
    ) -> CompletionVerdict:
        """
        Evaluates proposed completion against EEC invariants.
        Returns CompletionVerdict — Kernel-only derived state.

        EEC-6: COMPLETED is NEVER returned here; only CompletionState variants.
               Caller (Kernel) decides whether to admit completion.
        """
        # v1.0 compat: accept epas parameter or default empty list
        if eets is None:
            eets = epas or []
        elif epas is not None and not eets:
            eets = epas

        effective_mission_id = mission_id or target_mission_id or ""
        req_list = requirements or []
        obligations = proof_obligations or []
        fail_reasons: List[str] = []

        # ── Policy OPTIONAL: minimal gate ───────────────────────────────────
        if policy == EvidencePolicy.OPTIONAL:
            return CompletionVerdict(
                verdict=CompletionState.VERIFIED,
                evidence_coverage=1.0,
                ucr_s=0.0,
                ucr_f=0.0,
                proof_obligations_satisfied=0,
                proof_obligations_total=0,
                gate_fail_reasons=[],
            )

        # ── Resource Version Invalidation Check ──────────────────────────────
        if (
            active_resource_version is not None
            and evidence_resource_version is not None
            and active_resource_version != evidence_resource_version
        ):
            fail_reasons.append(
                f"EVIDENCE_INVALIDATED: active_resource_version ({active_resource_version}) "
                f"differs from evidence_resource_version ({evidence_resource_version})"
            )
            return CompletionVerdict(
                verdict=CompletionState.EVIDENCE_INVALIDATED,
                evidence_coverage=0.0,
                ucr_s=1.0,
                ucr_f=0.0,
                proof_obligations_satisfied=0,
                proof_obligations_total=len(obligations),
                gate_fail_reasons=fail_reasons,
            )

        # ── Freshness Check (max_freshness_seconds) ───────────────────────────
        now = time.time()
        stale_freshness_count = 0
        if max_freshness_seconds is not None:
            for eet in eets:
                if eet.evidence and hasattr(eet.evidence, "created_at"):
                    if (now - eet.evidence.created_at) > max_freshness_seconds:
                        stale_freshness_count += 1
                        fail_reasons.append(
                            f"EVIDENCE_STALE: evidence {eet.evidence.evidence_id} created "
                            f"{now - eet.evidence.created_at:.1f}s ago (> max {max_freshness_seconds}s)"
                        )

        if stale_freshness_count > 0:
            return CompletionVerdict(
                verdict=CompletionState.EVIDENCE_STALE,
                evidence_coverage=0.0,
                ucr_s=1.0,
                ucr_f=0.0,
                proof_obligations_satisfied=0,
                proof_obligations_total=len(obligations),
                gate_fail_reasons=fail_reasons,
            )

        # ── Compute metrics ──────────────────────────────────────────────────
        metrics = EvidenceGateAuditor.calculate_metrics(eets, req_list, effective_mission_id)

        # ── Check for stale / cross-mission contamination ────────────────────
        stale_count = sum(
            1 for eet in eets
            if eet.evidence and EvidenceGateAuditor.check_stale(eet.evidence)
        )
        xmission_count = sum(
            1 for eet in eets
            if eet.evidence and effective_mission_id
            and EvidenceGateAuditor.check_cross_mission(eet.evidence, effective_mission_id)
        )
        if stale_count > 0:
            fail_reasons.append(f"EEC-9: {stale_count} stale evidence records (freshness expired)")
        if xmission_count > 0:
            fail_reasons.append(f"EEC-10: {xmission_count} cross-mission evidence rejected")

        # ── EEC-6: No verified evidence → must not complete ─────────────────
        if metrics.verified_evidence_count == 0:
            has_invalid = any(
                eet.status == VerificationStatus.EVIDENCE_INVALID for eet in eets
            )
            has_blocked = any(
                eet.status == VerificationStatus.VERIFICATION_BLOCKED for eet in eets
            )
            if has_invalid:
                fail_reasons.append("EEC-6: Verifier returned FAIL — EVIDENCE_INVALID")
                return CompletionVerdict(
                    verdict=CompletionState.EVIDENCE_INVALID,
                    evidence_coverage=0.0,
                    ucr_s=metrics.ucr_s,
                    ucr_f=metrics.ucr_f,
                    proof_obligations_satisfied=0,
                    proof_obligations_total=len(obligations),
                    gate_fail_reasons=fail_reasons,
                    metrics=metrics,
                )
            if has_blocked:
                fail_reasons.append("EEC-6 & EEC-8: Actions executed but no independent verifier")
                return CompletionVerdict(
                    verdict=CompletionState.VERIFICATION_BLOCKED,
                    evidence_coverage=0.0,
                    ucr_s=metrics.ucr_s,
                    ucr_f=metrics.ucr_f,
                    proof_obligations_satisfied=0,
                    proof_obligations_total=len(obligations),
                    gate_fail_reasons=fail_reasons,
                    metrics=metrics,
                )
            # No actions taken at all
            fail_reasons.append("EEC-6: Policy REQUIRED but zero evidence — initiating Recovery")
            return CompletionVerdict(
                verdict=CompletionState.RECOVERY,
                evidence_coverage=0.0,
                ucr_s=metrics.ucr_s,
                ucr_f=metrics.ucr_f,
                proof_obligations_satisfied=0,
                proof_obligations_total=len(obligations),
                gate_fail_reasons=fail_reasons,
                metrics=metrics,
            )

        # ── EEC-5: Verifier independence check ───────────────────────────────
        collusion_count = sum(
            1 for eet in eets
            if eet.evidence
            and eet.evidence.verifier_independence_class == VerifierIndependenceClass.INVALID
        )
        if collusion_count > 0:
            fail_reasons.append(
                f"EEC-5: {collusion_count} verifier(s) read same mutable state as writer (INVALID independence)"
            )

        # ── ProofObligation evaluation ────────────────────────────────────────
        obligations_satisfied = 0
        for obl in obligations:
            for eet in eets:
                ev = eet.evidence
                if ev is None:
                    continue
                if not level_gte(ev.level, obl.required_level):
                    continue
                if ev.verifier_independence_class == VerifierIndependenceClass.INVALID:
                    continue
                # Check required fields present in evidence
                fields_ok = all(
                    f in (ev.provenance_trace or {}) or hasattr(ev, f)
                    for f in obl.required_dimensions
                )
                if fields_ok and eet.status == VerificationStatus.VERIFIED:
                    obl.satisfied = True
                    obl.satisfied_by = ev.evidence_id
                    obligations_satisfied += 1
                    break

        # ── Policy-specific level check ─────────────────────────────────────
        if policy == EvidencePolicy.REQUIRED_INDEPENDENT:
            has_e3 = any(
                eet.evidence and eet.evidence.level == EvidenceLevel.E3_INDEPENDENTLY_VERIFIED
                for eet in eets
                if eet.status == VerificationStatus.VERIFIED
            )
            if not has_e3:
                fail_reasons.append("EEC-3: REQUIRED_INDEPENDENT policy needs E3 — no independent verifier found")

        if policy == EvidencePolicy.REQUIRED_MULTI_SOURCE:
            verified_sources = {
                eet.evidence.source_type for eet in eets
                if eet.evidence and eet.status == VerificationStatus.VERIFIED
            }
            if len(verified_sources) < 2:
                fail_reasons.append(
                    f"REQUIRED_MULTI_SOURCE: only {len(verified_sources)} distinct source type(s)"
                )

        # ── EEC-9: Relevance check ───────────────────────────────────────────
        if target_capability:
            matching = [
                eet for eet in eets
                if eet.evidence
                and eet.evidence.capability == target_capability
                and eet.status == VerificationStatus.VERIFIED
            ]
            if not matching:
                fail_reasons.append(
                    f"EEC-9: No verified evidence matches target capability {target_capability.value}"
                )

        ev_hashes = [eet.evidence.evidence_hash for eet in eets if eet.evidence and eet.evidence.evidence_hash]
        obl_ids = [o.obligation_id for o in obligations]

        # ── ABSTAIN: Policy requires evidence but obligations unresolvable ────
        if obligations and obligations_satisfied == 0 and fail_reasons:
            return CompletionVerdict(
                verdict=CompletionState.ABSTAIN,
                evidence_coverage=metrics.evidence_coverage,
                ucr_s=metrics.ucr_s,
                ucr_f=metrics.ucr_f,
                proof_obligations_satisfied=0,
                proof_obligations_total=len(obligations),
                gate_fail_reasons=fail_reasons,
                metrics=metrics,
                mission_id=effective_mission_id,
                evidence_hashes=ev_hashes,
                obligation_ids=obl_ids,
            )

        # ── EEC-7/8: Coverage proportionality ────────────────────────────────
        if metrics.evidence_coverage < 1.0 and req_list:
            fail_reasons.append(
                f"EEC-7 & EEC-8: Partial coverage {metrics.evidence_coverage*100:.0f}%"
            )
            # Still have some evidence → LOW_CONFIDENCE, not BLOCKED
            if not fail_reasons or all("stale" not in r and "cross" not in r for r in fail_reasons[:1]):
                return CompletionVerdict(
                    verdict=CompletionState.LOW_CONFIDENCE,
                    evidence_coverage=metrics.evidence_coverage,
                    ucr_s=metrics.ucr_s,
                    ucr_f=metrics.ucr_f,
                    proof_obligations_satisfied=obligations_satisfied,
                    proof_obligations_total=len(obligations),
                    gate_fail_reasons=fail_reasons,
                    metrics=metrics,
                    mission_id=effective_mission_id,
                    evidence_hashes=ev_hashes,
                    obligation_ids=obl_ids,
                )

        # ── If any fail_reasons remain, block completion ──────────────────────
        if fail_reasons:
            return CompletionVerdict(
                verdict=CompletionState.RECOVERY,
                evidence_coverage=metrics.evidence_coverage,
                ucr_s=metrics.ucr_s,
                ucr_f=metrics.ucr_f,
                proof_obligations_satisfied=obligations_satisfied,
                proof_obligations_total=len(obligations),
                gate_fail_reasons=fail_reasons,
                metrics=metrics,
                mission_id=effective_mission_id,
                evidence_hashes=ev_hashes,
                obligation_ids=obl_ids,
            )

        # ── Full satisfaction: VERIFIED ──────────────────────────────────────
        return CompletionVerdict(
            verdict=CompletionState.VERIFIED,
            evidence_coverage=metrics.evidence_coverage,
            ucr_s=metrics.ucr_s,
            ucr_f=metrics.ucr_f,
            proof_obligations_satisfied=obligations_satisfied,
            proof_obligations_total=len(obligations),
            gate_fail_reasons=[],
            metrics=metrics,
            mission_id=effective_mission_id,
            evidence_hashes=ev_hashes,
            obligation_ids=obl_ids,
        )


# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY ALIASES (v1.0 → v2.0)
# ─────────────────────────────────────────────────────────────────────────────

# EvidenceProducingAction is the old name for EvidenceExecutionTrace
EvidenceProducingAction = EvidenceExecutionTrace

# Old verdict enum — map to new CompletionState equivalents
class EvidenceGateVerdict(str, Enum):
    TERMINATE_WITH_PROOF    = "TERMINATE_WITH_PROOF"     # → CompletionState.VERIFIED
    RECOVERY                = "RECOVERY"                  # → CompletionState.RECOVERY
    LOW_CONFIDENCE_CONCLUSION = "LOW_CONFIDENCE_CONCLUSION" # → CompletionState.LOW_CONFIDENCE
    VERIFICATION_BLOCKED    = "VERIFICATION_BLOCKED"     # → CompletionState.VERIFICATION_BLOCKED
