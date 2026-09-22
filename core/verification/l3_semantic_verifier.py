"""
JKAI Zenith - T6 Verification Layer: L3 Semantic Goal Verifier (v1.0)
Architecture: 5-Tier Verification (L0 -> L1 -> L2 -> L3 Semantic -> L4 Reality Delta)
Approved by: Antigravity (Lead Architect) & Opencode (Senior Red Team Auditor)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from core.cognitive_bus.jev_substrate_adapter import (
    TriTierJevAdapter,
    JevPrimitive,
    TypedJudgementPacket,
    ParallelBatchVerdict,
    ExecutionTier
)


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class L3VerificationVerdict:
    status: VerificationStatus
    score: float                        # Scale 0.0 to 4.0
    confidence: float                   # [0..1]
    criteria_results: Dict[str, float]  # criterion_id -> P(True)
    reasons: List[str]
    escalate_to_system_two: bool
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class L3SemanticVerifier:
    """
    Evaluates semantic goal alignment and acceptance criteria satisfaction using Jev Substrate.
    - 5-Level Continuous Score (0.0 .. 4.0)
    - Dynamic Noul Criteria Batch Verification
    - Strict Boundary: L3 PASS does not mean mission complete; L4 Reality Verifier owns physical truth.
    """

    SCORE_LEVELS = [
        "0 = Unfulfilled: Core criteria not met or completely missing",
        "1 = Partial Core: Core met but peripheral deliverables missing",
        "2 = Sub-spec Delivery: All deliverables present but quality/formatting below spec",
        "3 = Fully Satisfied: All declared constraints and deliverables strictly met with evidence",
        "4 = Exemplary: Exceeded expectations, zero warnings, optimal resource usage"
    ]

    PASS_SCORE_THRESHOLD = 2.75
    FAIL_SCORE_THRESHOLD = 2.00
    MIN_CONFIDENCE_THRESHOLD = 0.85
    CRITERIA_SATISFACTION_THRESHOLD = 0.95

    def __init__(self, jev_adapter: Optional[TriTierJevAdapter] = None):
        self.jev_adapter = jev_adapter or TriTierJevAdapter(enable_mock=True)

    def build_criteria_question(self, criterion_id: str, description: str) -> str:
        """Standardized DSL Template for criteria questions."""
        return f"Does the artifact strictly fulfill criterion '{criterion_id}': '{description}' with unambiguous evidence?"

    def verify_mission_goal(
        self,
        mission_intent: str,
        artifacts: Dict[str, Any],
        acceptance_criteria: List[Tuple[str, str]],  # [(criterion_id, description)]
        execution_evidence: Optional[Dict[str, Any]] = None
    ) -> L3VerificationVerdict:
        t0 = time.time()

        unified_state = {
            "mission_intent": mission_intent,
            "artifacts": artifacts,
            "evidence": execution_evidence or {}
        }

        # 1. Main Score Query
        score_q = "Where does the achieved result stand regarding the original mission criteria and constraints?"
        batch_queries: List[Tuple[JevPrimitive, str, Optional[List[str]]]] = [
            (JevPrimitive.SCORE, score_q, self.SCORE_LEVELS)
        ]

        # 2. Dynamic Batch Noul Criteria Queries
        crit_q_map = {}
        for c_id, c_desc in acceptance_criteria:
            q_text = self.build_criteria_question(c_id, c_desc)
            crit_q_map[q_text] = c_id
            batch_queries.append((JevPrimitive.NOUL, q_text, None))

        # 3. Execute atomic parallel batch over Jev
        batch_verdict: ParallelBatchVerdict = self.jev_adapter.evaluate_parallel_batch(
            unified_state,
            batch_queries
        )

        score_pkt = batch_verdict.judgements.get(score_q)
        score_val = float(score_pkt.result) if score_pkt else 0.0
        score_conf = score_pkt.confidence if score_pkt else 0.0

        criteria_results: Dict[str, float] = {}
        failed_criteria = []

        for q_text, c_id in crit_q_map.items():
            pkt = batch_verdict.judgements.get(q_text)
            p_val = float(pkt.result) if pkt else 0.0
            criteria_results[c_id] = p_val
            if p_val < self.CRITERIA_SATISFACTION_THRESHOLD:
                failed_criteria.append(f"Criterion '{c_id}' satisfied only with probability {p_val:.3f} (< {self.CRITERIA_SATISFACTION_THRESHOLD})")

        # 4. Gating logic
        reasons = []
        if score_val >= self.PASS_SCORE_THRESHOLD and score_conf >= self.MIN_CONFIDENCE_THRESHOLD and not failed_criteria:
            status = VerificationStatus.PASS
            reasons.append(f"L3 Semantic Goal fully satisfied (Score: {score_val:.2f}/4.0, Conf: {score_conf:.2f})")
            escalate = False
        elif score_val < self.FAIL_SCORE_THRESHOLD:
            status = VerificationStatus.FAIL
            reasons.append(f"L3 Semantic Goal failed threshold (Score: {score_val:.2f}/4.0 < {self.FAIL_SCORE_THRESHOLD})")
            reasons.extend(failed_criteria)
            escalate = False
        else:
            # Ambiguous zone -> Escalate to System Two
            status = VerificationStatus.AMBIGUOUS
            reasons.append(f"L3 Verification in ambiguous range (Score: {score_val:.2f}/4.0, Conf: {score_conf:.2f})")
            reasons.extend(failed_criteria)
            escalate = True

        latency = (time.time() - t0) * 1000.0
        return L3VerificationVerdict(
            status=status,
            score=score_val,
            confidence=score_conf,
            criteria_results=criteria_results,
            reasons=reasons,
            escalate_to_system_two=escalate,
            latency_ms=latency,
            metadata={
                "state_fingerprint": batch_verdict.state_fingerprint,
                "execution_tier": batch_verdict.execution_tier.value
            }
        )
