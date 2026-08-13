"""
JKAI ZENITH AI OS — IDEMPOTENCY REGISTRY (PHASE 8)
File: core/os/cognition/idempotency_registry.py

Implements:
- Idempotent Side-Effect Execution (D27, P0-6)
- Mutation Lifecycle Tracking (NOT_FOUND, IN_PROGRESS, SUCCEEDED, FAILED, UNKNOWN)
"""

from __future__ import annotations
import logging
import time
from typing import Dict, Optional, Tuple, Any

from core.os.cognition.deep_schemas import IdempotencyStatus
from core.os.cognition.event_model import emit_contract_violation, event_store

logger = logging.getLogger("jkai.cognition.idempotency")


class IdempotencyRegistry:
    """Tracks mutation idempotency keys and enforces no duplicate executions."""

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {} # idempotency_key -> {status, result, timestamp}

    def check_and_start(self, idempotency_key: str, mission_id: str, trace_id: str) -> Tuple[bool, IdempotencyStatus, Optional[Any]]:
        """
        Checks if key was previously executed.
        Returns: (can_execute: bool, status: IdempotencyStatus, cached_result)
        """
        if idempotency_key in self._records:
            rec = self._records[idempotency_key]
            status = rec["status"]
            logger.info("[Idempotency] Key %s found with status %s", idempotency_key, status.value)

            if status == IdempotencyStatus.SUCCEEDED:
                # Return cached result without re-executing
                return False, status, rec.get("result")
            elif status == IdempotencyStatus.UNKNOWN:
                # Must NOT re-execute automatically (P0-6)
                logger.warning("[Idempotency] Key %s is in UNKNOWN state. Reconcile required!", idempotency_key)
                emit_contract_violation(
                    contract_id="D27",
                    mission_id=mission_id,
                    trace_id=trace_id,
                    expected="Reconciliation before retry",
                    actual="Attempted retry on UNKNOWN mutation",
                    recovery_policy="RECONCILE",
                    enforcement_point="IdempotencyRegistry.check_and_start"
                )
                return False, status, None
            elif status == IdempotencyStatus.IN_PROGRESS:
                return False, status, None

        self._records[idempotency_key] = {
            "status": IdempotencyStatus.IN_PROGRESS,
            "result": None,
            "timestamp": time.time()
        }
        return True, IdempotencyStatus.NOT_FOUND, None

    def mark_completed(self, idempotency_key: str, result: Any, success: bool = True) -> None:
        if idempotency_key in self._records:
            self._records[idempotency_key]["status"] = IdempotencyStatus.SUCCEEDED if success else IdempotencyStatus.FAILED
            self._records[idempotency_key]["result"] = result

    def mark_unknown_timeout(self, idempotency_key: str) -> None:
        """P0-6: Sets status to UNKNOWN on timeout so subsequent retries are gated on RECONCILE."""
        if idempotency_key in self._records:
            self._records[idempotency_key]["status"] = IdempotencyStatus.UNKNOWN


# Global Idempotency Registry
idempotency_registry = IdempotencyRegistry()
