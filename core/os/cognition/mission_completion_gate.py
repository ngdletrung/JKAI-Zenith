"""
JKAI ZENITH AI OS — MISSION COMPLETION GATE & RECOVERY MANAGER (PHASE 10)
File: core/os/cognition/mission_completion_gate.py

Implements:
- MissionCompletionGate (D1, D21, P1-5)
- RecoveryManager with deterministic mapping & RECONCILE support (D24, D30, C8, P0-7)
"""

from __future__ import annotations
import logging
import time
from typing import Dict, List, Optional, Tuple

from core.os.cognition.deep_schemas import (
    MissionCriterion,
    CriterionStatus,
    MissionOutcome,
    MissionOutcomeStatus,
    RecoveryPolicyType
)
from core.os.cognition.event_model import emit_contract_violation, event_store

logger = logging.getLogger("jkai.cognition.completion_gate")


class MissionCompletionGate:
    """
    Enforces that finishing all waves != Mission completion.
    A mission completes ONLY when 100% of Success Criteria are VERIFIED (D1, D21).
    """

    @staticmethod
    def evaluate(
        mission_id: str,
        criteria: List[MissionCriterion],
        verification_context_hash: str,
        evidence_count: int,
        total_tokens: int = 0,
        total_vram_peak_mb: int = 0,
        total_wallclock_ms: int = 0,
        trace_id: str = "trace_default"
    ) -> MissionOutcome:
        total = len(criteria)
        verified = sum(1 for c in criteria if c.status == CriterionStatus.VERIFIED)
        unresolved = total - verified

        if total > 0 and unresolved == 0:
            status = MissionOutcomeStatus.COMPLETED_VERIFIED
        elif verified > 0:
            status = MissionOutcomeStatus.COMPLETED_WITH_LIMITATIONS
        else:
            status = MissionOutcomeStatus.FAILED_VERIFICATION

        outcome = MissionOutcome(
            mission_id=mission_id,
            status=status,
            success_criteria_total=total,
            success_criteria_verified=verified,
            success_criteria_unresolved=unresolved,
            verification_context_hash=verification_context_hash,
            evidence_count=evidence_count,
            total_tokens_consumed=total_tokens,
            total_vram_peak_mb=total_vram_peak_mb,
            total_wallclock_ms=total_wallclock_ms
        )

        event_store.append(
            aggregate_id=mission_id,
            event_type="MISSION_COMPLETION_EVALUATED",
            payload={
                "status": status.value,
                "verified_ratio": f"{verified}/{total}",
                "context_hash": verification_context_hash
            },
            correlation_id=trace_id
        )

        return outcome


class RecoveryManager:
    """
    Deterministic failure classification to recovery policy mapper (D24, C8, P0-7).
    """

    MAPPING: Dict[str, RecoveryPolicyType] = {
        "SYNTAX_ERROR": RecoveryPolicyType.RETRY,
        "COMPILER_ERROR": RecoveryPolicyType.RETRY,
        "TOOL_TIMEOUT_UNKNOWN": RecoveryPolicyType.RECONCILE,
        "PREMISE_FALSIFIED": RecoveryPolicyType.REPLAN,
        "CRITIC_REJECTED": RecoveryPolicyType.REPLAN,
        "EVIDENCE_INSUFFICIENT": RecoveryPolicyType.WAIT_FOR_EVIDENCE,
        "SAFETY_VIOLATION": RecoveryPolicyType.ABORT,
        "SANDBOX_BREACH": RecoveryPolicyType.ABORT,
        "WORKTREE_CORRUPTED": RecoveryPolicyType.ROLLBACK,
    }

    @classmethod
    def resolve_policy(cls, failure_class: str) -> RecoveryPolicyType:
        return cls.MAPPING.get(failure_class, RecoveryPolicyType.ESCALATE)


# Global instances
completion_gate = MissionCompletionGate()
recovery_manager = RecoveryManager()
