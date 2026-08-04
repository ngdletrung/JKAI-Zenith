"""
JKAI ZENITH — VERIFICATION PACKAGE: ADAPTIVE RECOVERY ENGINE (v2.1)
File: core/verification/recovery_engine.py
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from core.contracts.cognitive_contract import IdentityChain, MissionDefinition
from core.contracts.execution_contract import RecoveryPolicy, AttemptRecord
from core.contracts.verification_contract import (
    VerificationResult,
    FailureClassification,
    RecoveryStrategy,
    RuntimeState,
)
from core.mission.mission_registry import MissionRegistry

logger = logging.getLogger("jkai.verification.recovery")


@dataclass
class RecoveryDecision:
    """Hồ sơ quyết định phục hồi tác chiến."""
    outcome: str = "RETRY"
    next_step: Optional[str] = None
    reason: str = ""
    attempt_number: int = 1


class RecoveryEngine:
    """Bộ Phục Hồi Tác Chiến Thích Ứng (Adaptive Recovery Engine)."""

    @classmethod
    def determine_recovery(cls, contract: Any, eval_res: Any, current_attempt: int = 1, max_attempts: int = 3) -> RecoveryDecision:
        return RecoveryDecision(outcome="RETRY", next_step="RETRY_ATTEMPT", reason="Recovery triggered", attempt_number=current_attempt + 1)

    @classmethod
    def process_recovery(
        cls,
        mission: MissionDefinition,
        attempt: AttemptRecord,
        verifier_result: VerificationResult,
        policy: Optional[RecoveryPolicy] = None
    ) -> tuple[RuntimeState, Optional[AttemptRecord]]:
        """
        Xử lý phục hồi và chuyển trạng thái State Machine.
        """
        mid = mission.identity.mission_id
        pol = policy or RecoveryPolicy()

        # 1. Kiểm tra Terminal State POLICY_FAILURE -> ABORTED
        if verifier_result.failure_classification == FailureClassification.POLICY_FAILURE:
            logger.warning(f"⛔ [RECOVERY-ENGINE]: Policy failure on Mission ID={mid} -> ABORTED Terminal State.")
            MissionRegistry.transition_state(mid, RuntimeState.ABORTED)
            return RuntimeState.ABORTED, None

        # 2. Kiểm tra Ngân sách Phục hồi (Recovery Budget)
        if attempt.attempt_number >= pol.max_attempts:
            logger.warning(f"⚠️ [RECOVERY-ENGINE]: Attempt budget exceeded ({attempt.attempt_number}/{pol.max_attempts}) on Mission ID={mid} -> ABORTED.")
            MissionRegistry.transition_state(mid, RuntimeState.ABORTED)
            return RuntimeState.ABORTED, None

        # 3. Phân luồng chiến lược phục hồi
        rec_strat = verifier_result.recommended_recovery
        next_attempt_no = attempt.attempt_number + 1
        
        next_attempt = AttemptRecord(
            identity=IdentityChain(
                request_id=attempt.identity.request_id,
                mission_id=attempt.identity.mission_id,
                plan_id=attempt.identity.plan_id,
                task_id=attempt.identity.task_id,
                attempt_id=f"att_r{next_attempt_no}_{attempt.identity.attempt_id[-6:]}"
            ),
            attempt_number=next_attempt_no,
            strategy_id=f"recovered_{rec_strat.value.lower()}",
            parent_attempt_id=attempt.identity.attempt_id,
            recovery_reason=verifier_result.failure_classification.value
        )

        if rec_strat == RecoveryStrategy.RETRY:
            MissionRegistry.transition_state(mid, RuntimeState.RETRYING)
        elif rec_strat == RecoveryStrategy.SUBSTITUTE_CAPABILITY:
            MissionRegistry.transition_state(mid, RuntimeState.SUBSTITUTING)
        elif rec_strat == RecoveryStrategy.CHANGE_MODEL:
            MissionRegistry.transition_state(mid, RuntimeState.CHANGING_MODEL)
        elif rec_strat == RecoveryStrategy.REPLAN:
            MissionRegistry.transition_state(mid, RuntimeState.REPLANNING)
        elif rec_strat == RecoveryStrategy.DIAGNOSE_AND_REPAIR:
            MissionRegistry.transition_state(mid, RuntimeState.DIAGNOSING)
        elif rec_strat == RecoveryStrategy.REQUEST_CLARIFICATION:
            MissionRegistry.transition_state(mid, RuntimeState.CLARIFICATION_REQUIRED)
            return RuntimeState.CLARIFICATION_REQUIRED, next_attempt

        logger.info(f"🔄 [RECOVERY-ENGINE]: Transitioned Mission ID={mid} strategy={rec_strat.value} (Attempt #{next_attempt_no})")
        return MissionRegistry.get_state(mid), next_attempt
