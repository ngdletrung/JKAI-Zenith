"""
JKAI ZENITH AI OS — SHADOW CONTROLLER v2.2 (Phase 2 Full Cognitive Loop)
File: core/os/cognition/shadow_controller_v2.py

Dual-Trace Shadow Evaluation:
    v1 (current FAST) vs v2.2 (Shadow Cognitive Loop)
Emits structured telemetry for Go/No-Go decision on 100-500 real missions.
"""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.os.cognition.evidence_ledger_v2 import (
    EvidenceLedger, EvidenceRecord, Belief, BeliefStatus,
    Claim, ConclusionStrength, FSMState, VerificationStatus,
)
from core.os.cognition.reasoning_judge import (
    ReasoningJudge, ReasoningAssessment, BudgetPolicy, ProgressVector, ActionFingerprint,
)
from core.os.config.feature_flags import KET_FAST_V2_SHADOW

logger = logging.getLogger("jkai.cognition.shadow_controller_v2")

TASK_PROFILE_BUDGET: Dict[str, int] = {
    "REFLEX":        2,
    "SELF_QUERY":    2,
    "SINGLE_TOOL":   5,
    "FIX":           5,
    "RESEARCH":     10,
    "DEEP_RESEARCH": 10,
    "DEFAULT":       8,
}
B_HARD_MAP: Dict[str, int] = {
    "REFLEX": 3, "SELF_QUERY": 3, "SINGLE_TOOL": 7, "FIX": 7,
    "RESEARCH": 12, "DEEP_RESEARCH": 12, "DEFAULT": 12,
}


@dataclass
class DualTraceResult:
    mission_id:        str
    goal:              str
    v1_topology:       str
    v2_topology:       str
    v1_conclusion:     str
    v2_assessment:     ReasoningAssessment
    fsm_state:         FSMState
    budget_used:       int
    extensions_granted:int
    extension_reasons: List[str]
    would_have_escalated: bool
    overconfident:     bool          # I8 violation flag
    belief_revision_log: List[Dict[str, Any]]
    telemetry:         Dict[str, Any]


class ShadowControllerV2:
    """
    Phase 2 Shadow Controller — Full Cognitive Loop (non-mutating).
    Runs alongside v1 runtime and emits dual-trace telemetry.
    All operations are read-only with respect to production state (I12 respected).
    """

    def __init__(self, mission_id: str, goal: str, task_profile: str = "DEFAULT") -> None:
        self.mission_id    = mission_id
        self.goal          = goal
        self.task_profile  = task_profile
        self._ledger       = EvidenceLedger()
        self._judge        = ReasoningJudge(self._ledger)
        self._fsm_state    = FSMState.CREATED
        self._beliefs: Dict[str, Belief] = {}
        b0  = TASK_PROFILE_BUDGET.get(task_profile, 8)
        bh  = B_HARD_MAP.get(task_profile, 12)
        self._budget       = BudgetPolicy(initial_budget=b0, b_hard=bh)
        self._turn         = 0
        self._claims_added: List[str] = []

    # ─── Public API ───────────────────────────────────────────────────────────

    def add_evidence(self, record: EvidenceRecord) -> None:
        """Ingest evidence from runtime observation (append-only, I3)."""
        self._ledger.add_evidence(record)

    def add_claim(self, claim: Claim) -> None:
        self._ledger.add_claim(claim)
        if claim.claim_id not in self._claims_added:
            self._claims_added.append(claim.claim_id)

    def add_belief(self, belief: Belief) -> None:
        self._beliefs[belief.belief_id] = belief

    def revise_belief(self, belief_id: str, new_confidence: float,
                      new_status: Optional[BeliefStatus], trigger_evidence: List[str], reason: str) -> None:
        """I9 + I10 enforced via EvidenceLedger.update_belief."""
        if belief_id in self._beliefs:
            self._ledger.update_belief(
                self._beliefs[belief_id], new_confidence, new_status, trigger_evidence, reason
            )

    def step(self, action_fp: Optional[ActionFingerprint] = None) -> FSMState:
        """Advance one ReAct turn. Returns new FSMState."""
        self._turn += 1

        # Semantic Stall Detection
        if action_fp and self._judge.record_action(action_fp):
            self._fsm_state = FSMState.RECOVERY
            logger.warning("[ShadowV2] STALL_DETECTED at turn %d", self._turn)
            return self._fsm_state

        self._fsm_state = FSMState.EXECUTING
        return self._fsm_state

    def evaluate(self, hypotheses: List[str], v1_topology: str, v1_conclusion: str) -> DualTraceResult:
        """Run full Cognitive Loop assessment and emit dual-trace telemetry."""
        if not KET_FAST_V2_SHADOW:
            logger.debug("[ShadowV2] KET_FAST_V2_SHADOW=False → no-op.")

        self._fsm_state = FSMState.REASSESSING

        # Compute ProgressVector for budget extension decision
        prev_evidence_count = max(len(self._ledger.all_evidence) - 1, 0)
        new_evidence_count  = len(self._ledger.all_evidence)

        # Count contradictions from ledger (discovered this turn vs resolved)
        all_ev = list(self._ledger.all_evidence.values())
        contradictions_found    = sum(1 for r in all_ev if r.contradicts)
        contradictions_resolved = sum(
            1 for r in all_ev
            if r.contradicts and r.verification_status != VerificationStatus.CANDIDATE
        )
        verified_count = sum(1 for r in all_ev if r.verification_status == VerificationStatus.VERIFIED)

        pv = ProgressVector.from_resolution(
            evidence_gain         = min(1.0, (new_evidence_count - prev_evidence_count) / max(new_evidence_count, 1)),
            uncertainty_reduction = 0.3 if self._claims_added else 0.0,
            goal_coverage         = min(1.0, len(self._claims_added) * 0.15),
            verification_progress = min(1.0, verified_count / max(new_evidence_count, 1)),
            new_information       = min(1.0, new_evidence_count * 0.1),
            contradictions_found=contradictions_found,
            contradictions_resolved=contradictions_resolved,
        )
        ps = pv.score()
        extended, _ = self._budget.try_extend(ps, f"turn={self._turn} progress_score={ps:.3f}")
        if extended:
            logger.info("[ShadowV2] Budget extended +2. Extensions used: %d", self._budget.extensions_used)

        # Run Hybrid Reasoning Judge
        assessment: ReasoningAssessment = self._judge.assess(
            claim_ids=self._claims_added,
            hypotheses=hypotheses,
            budget=self._budget,
            turn=self._turn,
        )

        # Determine FSM state from assessment
        if assessment.stop_condition == "SUFFICIENT":
            self._fsm_state = FSMState.VERIFYING
        elif assessment.recommended_action == "ACQUIRE_MORE":
            self._fsm_state = FSMState.WAITING_FOR_EVIDENCE
        else:
            self._fsm_state = FSMState.LOW_CONFIDENCE_CONCLUSION

        # I8 Overconfidence check
        overconfident = (
            assessment.conclusion_strength == ConclusionStrength.HIGH and
            len(self._ledger.all_evidence) < 3
        )
        if overconfident:
            logger.warning("[I8-VIOLATION] Overconfidence: HIGH conclusion with <3 evidence records.")

        proposed_topology = "DEEP" if assessment.conclusion_strength == ConclusionStrength.UNRESOLVED else v1_topology

        telemetry = {
            "mission_id":           self.mission_id,
            "task_profile":         self.task_profile,
            "v1_topology":          v1_topology,
            "v2_shadow_topology":   proposed_topology,
            "v1_conclusion":        v1_conclusion,
            "v2_conclusion_strength": assessment.conclusion_strength.value,
            "v2_confidence":        assessment.confidence,
            "v2_stop_condition":    assessment.stop_condition,
            "v2_recommended_action":assessment.recommended_action,
            "evidence_count":       len(self._ledger.all_evidence),
            "independent_clusters": len({r.independence_cluster for r in self._ledger.all_evidence.values()}),
            "turns_used":           self._turn,
            "budget_initial":       self._budget.initial_budget,
            "budget_ceiling":       self._budget.current_ceiling,
            "extensions_granted":   self._budget.extensions_used,
            "would_have_escalated": v1_topology == "FAST" and proposed_topology == "DEEP",
            "overconfident":        overconfident,
            "fsm_state":            self._fsm_state.value,
        }
        logger.info("[ShadowV2 Telemetry] %s", telemetry)

        return DualTraceResult(
            mission_id=self.mission_id,
            goal=self.goal,
            v1_topology=v1_topology,
            v2_topology=proposed_topology,
            v1_conclusion=v1_conclusion,
            v2_assessment=assessment,
            fsm_state=self._fsm_state,
            budget_used=self._turn,
            extensions_granted=self._budget.extensions_used,
            extension_reasons=list(self._budget.extension_log),
            would_have_escalated=telemetry["would_have_escalated"],
            overconfident=overconfident,
            belief_revision_log=self._ledger.belief_revision_log,
            telemetry=telemetry,
        )
