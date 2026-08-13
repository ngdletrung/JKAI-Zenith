"""
JKAI ZENITH AI OS — REASONING JUDGE v2.2 (Constitution I7, I8, I9, Hybrid Architecture)
File: core/os/cognition/reasoning_judge.py

Hybrid Reasoning Judge:
    Layer 1 — Deterministic Analysis (always runs, zero LLM cost)
    Layer 2 — Evidence Scoring     (structured computation)
    Layer 3 — LLM Reasoner         (only when ambiguity is high)

Separation of Authority (I7):
    Reasoning Judge answers: "What do I believe / how strong is evidence / what next?"
    Policy Governor answers:  "Is this authorized / which topology / budget?"
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from core.os.cognition.evidence_ledger_v2 import (
    EvidenceLedger, EvidenceRecord, EvidenceStrength, ConclusionStrength,
    VerificationStatus, Belief, BeliefStatus,
)

logger = logging.getLogger("jkai.cognition.reasoning_judge")

EXTENSION_THRESHOLD = 0.35  # ProgressScore threshold to grant budget extension
MAX_EXTENSIONS = 2          # I6: hard limit on extensions per mission


@dataclass
class ProgressVector:
    """
    Normalized ∈ [0,1] per component. ProgressScore ∈ [-1,1].

    Contradiction model (per formal spec correction):
        contradiction_discovered ≠ negative progress.
        Discovering a contradiction is epistemic advancement — it reduces uncertainty.
        Only UNRESOLVED contradiction (discovered but not classified) is a stall signal.

        contradiction_discovered : float  — new contradictions found this turn (↑ = progress)
        contradiction_unresolved : float  — contradictions still open at assessment (↑ = stall)
    """
    evidence_gain:             float = 0.0   # New independent verified evidence added
    uncertainty_reduction:     float = 0.0   # Uncertainty narrowed (claims classified)
    goal_coverage:             float = 0.0   # Fraction of success_criteria addressed
    verification_progress:     float = 0.0   # Verified evidence / total evidence
    new_information:           float = 0.0   # Novel claims (not previously in ledger)
    contradiction_discovered:  float = 0.0   # New contradictions found — POSITIVE signal
    contradiction_unresolved:  float = 0.0   # Open contradictions not yet classified — NEGATIVE signal

    def score(self, α=0.28, β=0.22, γ=0.18, δ=0.15, η=0.10, φ=0.07, ε=0.10) -> float:
        """
        Weighted ProgressScore ∈ [-1,1].

        contradiction_discovered adds to score (finding a contradiction is progress).
        contradiction_unresolved subtracts (open contradictions = stall risk).
        """
        s = (α * self.evidence_gain
           + β * self.uncertainty_reduction
           + γ * self.goal_coverage
           + δ * self.verification_progress
           + η * self.new_information
           + φ * self.contradiction_discovered    # ← positive: epistemic progress
           - ε * self.contradiction_unresolved)   # ← negative: unresolved stall
        return max(-1.0, min(1.0, round(s, 4)))

    @classmethod
    def from_resolution(
        cls,
        evidence_gain: float,
        uncertainty_reduction: float,
        goal_coverage: float,
        verification_progress: float,
        new_information: float,
        contradictions_found: int,
        contradictions_resolved: int,
    ) -> "ProgressVector":
        """
        Construct ProgressVector from raw contradiction counts.
        Resolved contradictions count as full epistemic progress.
        Unresolved = discovered - resolved (capped ∈ [0,1]).
        """
        discovered  = min(1.0, contradictions_found * 0.25)
        unresolved  = min(1.0, max(0.0, contradictions_found - contradictions_resolved) * 0.25)
        return cls(
            evidence_gain=evidence_gain,
            uncertainty_reduction=uncertainty_reduction,
            goal_coverage=goal_coverage,
            verification_progress=verification_progress,
            new_information=new_information,
            contradiction_discovered=discovered,
            contradiction_unresolved=unresolved,
        )


@dataclass
class ActionFingerprint:
    """Semantic stall detection — detects semantically equivalent repeated actions."""
    tool:               str
    normalized_target:  str
    normalized_query:   str
    purpose:            str
    evidence_delta:     float = 0.0
    belief_delta:       float = 0.0


@dataclass
class BudgetPolicy:
    """3-Tier Bounded Budget (I6)."""
    initial_budget:  int
    b_hard:          int
    max_extensions:  int = MAX_EXTENSIONS
    extensions_used: int = 0
    extension_log:   List[str] = field(default_factory=list)

    @property
    def current_ceiling(self) -> int:
        extension_budget = self.extensions_used * 2
        return min(self.initial_budget + extension_budget, self.b_hard)

    def try_extend(self, progress_score: float, reason: str) -> Tuple[bool, int]:
        """Grant +2 turns if ProgressScore > threshold and extensions remain. Returns (granted, new_ceiling)."""
        if self.extensions_used >= self.max_extensions:
            return False, self.current_ceiling
        if progress_score <= EXTENSION_THRESHOLD:
            return False, self.current_ceiling
        self.extensions_used += 1
        self.extension_log.append(reason)
        return True, self.current_ceiling


@dataclass
class ReasoningAssessment:
    """Standard 9-field output of Reasoning Judge (I7: judge ≠ governor)."""
    hypotheses:           List[str]
    supported_claims:     List[str]
    contradicted_claims:  List[str]
    uncertainty:          List[str]
    evidence_gaps:        List[str]
    confidence:           float           # ∈ [0,1]
    conclusion_strength:  ConclusionStrength
    recommended_action:   str             # DECIDE / ACQUIRE_MORE / WAIT
    stop_condition:       str             # SUFFICIENT / INSUFFICIENT / FALSIFIED / STALL


class ReasoningJudge:
    """
    Hybrid Reasoning Judge.
    Deterministic + Evidence Scoring always run first.
    LLM called only when ambiguity score is high.
    """

    _STALL_SIMILARITY_THRESHOLD = 0.85
    _AMBIGUITY_THRESHOLD        = 0.65

    def __init__(self, ledger: EvidenceLedger) -> None:
        self._ledger = ledger
        self._action_history: List[ActionFingerprint] = []

    # ─── Public API ───────────────────────────────────────────────────────────

    def assess(
        self,
        claim_ids: List[str],
        hypotheses: List[str],
        budget: BudgetPolicy,
        turn: int,
    ) -> ReasoningAssessment:
        """Run Hybrid Reasoning: Deterministic → Evidence Scoring → (optional LLM)."""

        # Layer 1: Deterministic Analysis
        supported, contradicted, gaps, uncertainty = self._deterministic_layer(claim_ids)

        # Layer 2: Evidence Scoring
        overall_evidence_strength, confidence = self._evidence_scoring_layer(claim_ids)

        # Layer 3: LLM (stub — only invoked when ambiguity is high)
        ambiguity_score = self._compute_ambiguity(confidence, len(uncertainty), len(contradicted))
        if ambiguity_score >= self._AMBIGUITY_THRESHOLD:
            logger.info("[ReasoningJudge] Ambiguity=%.2f — LLM layer would be invoked here.", ambiguity_score)
            # In Phase 2 Shadow: LLM call is simulated / deferred

        # I8: Conclusion strength must not exceed evidence strength
        conclusion_strength = self._scale_conclusion(overall_evidence_strength, confidence, contradicted)

        # Determine recommended action
        recommended_action, stop_condition = self._decide_next_step(
            conclusion_strength, gaps, budget, turn
        )

        return ReasoningAssessment(
            hypotheses=hypotheses,
            supported_claims=supported,
            contradicted_claims=contradicted,
            uncertainty=uncertainty,
            evidence_gaps=gaps,
            confidence=round(confidence, 4),
            conclusion_strength=conclusion_strength,
            recommended_action=recommended_action,
            stop_condition=stop_condition,
        )

    def record_action(self, fp: ActionFingerprint) -> bool:
        """Semantic Stall Detection. Returns True if stall detected."""
        stall = self._detect_semantic_stall(fp)
        self._action_history.append(fp)
        return stall

    # ─── Layer 1: Deterministic ───────────────────────────────────────────────

    def _deterministic_layer(self, claim_ids: List[str]):
        supported, contradicted, gaps, uncertainty = [], [], [], []
        for cid in claim_ids:
            suf = self._ledger.evidence_sufficiency(cid)
            # I8: contradiction takes absolute priority over sufficiency
            if suf["contradiction_level"] > 0.3:
                contradicted.append(cid)
            elif suf["sufficient"]:
                supported.append(cid)
            elif suf["supporting_count"] == 0:
                gaps.append(cid)
            else:
                uncertainty.append(cid)
        return supported, contradicted, gaps, uncertainty

    # ─── Layer 2: Evidence Scoring ────────────────────────────────────────────

    def _evidence_scoring_layer(self, claim_ids: List[str]):
        if not claim_ids:
            return EvidenceStrength.NONE, 0.0

        strengths, confidences = [], []
        for cid in claim_ids:
            suf = self._ledger.evidence_sufficiency(cid)
            s = suf["evidence_strength"]
            strengths.append(s)
            ind = suf["independent_clusters"]
            base = {"NONE": 0.0, "WEAK": 0.35, "MODERATE": 0.65, "STRONG": 0.9}.get(s, 0.0)
            contradiction_penalty = suf["contradiction_level"] * 0.2
            confidence = max(0.0, min(1.0, base + min(ind * 0.05, 0.1) - contradiction_penalty))
            confidences.append(confidence)

        # Aggregate (weakest-link for strength, mean for confidence)
        order = [EvidenceStrength.NONE, EvidenceStrength.WEAK,
                 EvidenceStrength.MODERATE, EvidenceStrength.STRONG]
        weakest = min(strengths, key=lambda s: order.index(s))
        avg_conf = sum(confidences) / len(confidences)
        return weakest, avg_conf

    # ─── I8: Scale Conclusion ─────────────────────────────────────────────────

    def _scale_conclusion(
        self,
        evidence_strength: EvidenceStrength,
        confidence: float,
        contradicted: List[str],
    ) -> ConclusionStrength:
        if contradicted:
            return ConclusionStrength.UNRESOLVED
        if evidence_strength == EvidenceStrength.NONE:
            return ConclusionStrength.UNRESOLVED
        if evidence_strength == EvidenceStrength.WEAK or confidence < 0.50:
            return ConclusionStrength.LOW
        if evidence_strength == EvidenceStrength.MODERATE or confidence < 0.75:
            return ConclusionStrength.MEDIUM
        return ConclusionStrength.HIGH

    # ─── Recommended Action ───────────────────────────────────────────────────

    def _decide_next_step(
        self,
        conclusion_strength: ConclusionStrength,
        gaps: List[str],
        budget: BudgetPolicy,
        turn: int,
    ) -> Tuple[str, str]:
        if conclusion_strength in (ConclusionStrength.MEDIUM, ConclusionStrength.HIGH):
            return "DECIDE", "SUFFICIENT"
        if gaps and turn < budget.current_ceiling:
            return "ACQUIRE_MORE", "INSUFFICIENT"
        if not gaps:
            return "DECIDE", "INSUFFICIENT"
        return "WAIT", "INSUFFICIENT"

    # ─── Semantic Stall Detection ─────────────────────────────────────────────

    def _detect_semantic_stall(self, fp: ActionFingerprint) -> bool:
        recent = self._action_history[-2:] if len(self._action_history) >= 2 else self._action_history
        for prev in recent:
            if (prev.tool == fp.tool and
                prev.normalized_target == fp.normalized_target and
                fp.evidence_delta < 0.05 and fp.belief_delta < 0.05):
                logger.warning("[ReasoningJudge] Semantic stall detected: tool=%s target=%s",
                               fp.tool, fp.normalized_target)
                return True
        return False

    def _compute_ambiguity(self, confidence: float, uncertainty_count: int, contradiction_count: int) -> float:
        return min(1.0, (1 - confidence) * 0.5 + uncertainty_count * 0.1 + contradiction_count * 0.15)
