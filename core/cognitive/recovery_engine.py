"""
JKAI ZENITH — COGNITIVE DOMAIN: RECOVERY ENGINE
File: core/cognitive/recovery_engine.py

Recovery & Replanning Engine.
Translates EvaluationResult into control decisions (COMPLETE, REPLAN, RECOVER, ABORT).
Does NOT mutate MissionContract.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from core.contracts import MissionContract, EvaluationResult, MissionState


@dataclass
class RecoveryDecision:
    """Decision emitted by RecoveryEngine."""
    action: str = "COMPLETE"            # "COMPLETE" | "REPLAN" | "RECOVER" | "ABORT"
    target_state: MissionState = MissionState.COMPLETED
    reason: str = "Evaluation PASSED"
    retry_attempt: int = 1


class RecoveryEngine:
    """Translates evaluation findings into Cognitive Kernel recovery control decisions."""

    def determine_recovery(
        self,
        contract: MissionContract,
        eval_result: EvaluationResult,
        current_attempt: int = 1,
        max_attempts: int = 3
    ) -> RecoveryDecision:
        if eval_result.mission_succeeded:
            return RecoveryDecision(
                action="COMPLETE",
                target_state=MissionState.COMPLETED,
                reason="Evaluation criteria satisfied",
                retry_attempt=current_attempt
            )

        if current_attempt < max_attempts:
            return RecoveryDecision(
                action="REPLAN",
                target_state=MissionState.RUNNING,
                reason=f"Attempt #{current_attempt} failed evaluation: {eval_result.evidence_summary}. Triggering Replan.",
                retry_attempt=current_attempt + 1
            )
        else:
            return RecoveryDecision(
                action="ABORT",
                target_state=MissionState.FAILED,
                reason=f"Exceeded max attempts ({max_attempts}). Mission FAILED.",
                retry_attempt=current_attempt
            )
