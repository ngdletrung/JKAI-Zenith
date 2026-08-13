"""
JKAI ZENITH AI OS — SHADOW CONTROLLER
File: core/os/cognition/shadow_controller.py

Shadow Evaluator running in Non-Mutating Isolation mode.
Observes execution, forms beliefs, evaluates decision matrix, and logs telemetry comparison.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.os.cognition.mission_state_v2 import ImmutableMission, MutableRuntimeState, Belief, BeliefStatus
from core.os.cognition.decision_matrix import evaluate_decision_matrix, DecisionExplanation
from core.os.config.feature_flags import KET_FAST_V2_SHADOW

logger = logging.getLogger("jkai.cognition.shadow_controller")


@dataclass
class ShadowEvaluationResult:
    mission_id: str
    v1_topology: str
    proposed_v2_topology: str
    decision_explanation: DecisionExplanation
    beliefs: List[Dict[str, Any]]
    telemetry_payload: Dict[str, Any]


class ShadowController:
    """
    Shadow Controller — Runs evaluation silently alongside Phase 1 runtime path.
    Guaranteed NO-OP on runtime execution when KET_FAST_V2_SHADOW is False or in dry-run mode.
    """

    def __init__(self, mission_id: str, goal: str):
        self.mission = ImmutableMission(mission_id=mission_id, goal=goal, original_goal=goal)
        self.state = MutableRuntimeState(mission_id=mission_id)

    def observe_and_evaluate(
        self,
        v1_current_topology: str,
        observed_files: List[str] = None,
        observed_errors: List[str] = None,
        kwargs: Dict[str, Any] = None,
    ) -> ShadowEvaluationResult:
        obs_files = observed_files or []
        obs_errs = observed_errors or []
        kw = kwargs or {}

        # 1. Add evidence
        ev_id = f"E{len(self.state.evidence_ledger.items) + 1:02d}"
        self.state.evidence_ledger.add_evidence(
            evidence_id=ev_id,
            description=f"Observed {len(obs_files)} files and {len(obs_errs)} errors",
            source="runtime_observer",
            modified_files=obs_files,
        )

        # 2. Form/Update belief
        is_multi_file = len(obs_files) > 1 or kw.get("multi_file", False)
        confidence = 0.55 if is_multi_file else 0.88
        uncertainty = 0.75 if (is_multi_file or obs_errs) else 0.2
        impact = 0.85 if is_multi_file else 0.3
        reversibility = 0.3 if is_multi_file else 0.9
        tool_risk = 0.9 if any(pat in self.mission.goal.lower() for pat in ["xóa", "rm -rf", "drop"]) else 0.2

        b = Belief(
            belief_id="B01",
            hypothesis="MULTI_FILE_MUTATION" if is_multi_file else "SINGLE_FILE_ACTION",
            confidence=confidence,
            evidence_for=[ev_id],
            status=BeliefStatus.ACTIVE,
        )
        self.state.beliefs["B01"] = b

        # 3. Compute decision matrix
        explanation = evaluate_decision_matrix(
            confidence=confidence,
            uncertainty=uncertainty,
            impact=impact,
            reversibility=reversibility,
            evidence_quality=0.9,
            tool_risk=tool_risk,
            evidence_ids=[ev_id],
        )

        proposed_topology = explanation.decision if explanation.decision in ("FAST", "DEEP") else "DEEP"


        telemetry = {
            "mission_id": self.mission.mission_id,
            "v1_topology": v1_current_topology,
            "v2_shadow_topology": proposed_topology,
            "decision_score": explanation.score,
            "reason_codes": explanation.reason_codes,
            "evidence_ids": explanation.evidence_ids,
            "would_have_escalated": (v1_current_topology == "FAST" and proposed_topology == "DEEP"),
        }

        logger.info("[ShadowController Telemetry] %s", telemetry)

        return ShadowEvaluationResult(
            mission_id=self.mission.mission_id,
            v1_topology=v1_current_topology,
            proposed_v2_topology=proposed_topology,
            decision_explanation=explanation,
            beliefs=[{"hypothesis": b.hypothesis, "confidence": b.confidence}],
            telemetry_payload=telemetry,
        )
