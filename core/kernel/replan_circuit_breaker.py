# -*- coding: utf-8 -*-
"""
core/kernel/replan_circuit_breaker.py
🛡️ REPLAN CIRCUIT BREAKER MODULE (P0-1)
Chặn đứng thảm họa lặp vô tận (Infinite Re-plan Storm).
Phân loại chính xác lỗi hạ tầng (INFRA), hợp đồng (CONTRACT), logic (LOGIC), chính sách (POLICY).
Nếu lỗi hạ tầng lặp lại >= 2 lần -> FAIL-FAST ngay lập tức (<10s) thay vì lặp 4.5 tiếng.
"""

from __future__ import annotations
import hashlib
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ReplanCircuitBreaker")


@dataclass(frozen=True)
class ErrorSignature:
    kind: str   # INFRA | CONTRACT | LOGIC | POLICY
    code: str   # e.g. JSON_EMPTY_BODY, TOOL_NOT_FOUND, SYNTAX_ERROR, HARD_DENY
    tool: str

    def get_hash(self) -> str:
        raw = f"{self.kind}:{self.code}:{self.tool}".lower()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class BreakerDecision:
    action: str          # "ALLOW_RETRY" | "FAIL_FAST" | "ESCALATE"
    reason: str
    error_count: int
    signature: ErrorSignature


class ReplanCircuitBreaker:
    """
    Two-Tier Replan Circuit Breaker.
    Enforces maximum failure thresholds per task_id and error signature.
    """
    INFRA_THRESHOLD: int = 2     # Lỗi hạ tầng (HTTP sập, JSON empty) lặp 2 lần -> FAIL-FAST ngay
    CONTRACT_THRESHOLD: int = 2  # Sai hợp đồng/tên tool lặp 2 lần -> FAIL-FAST
    LOGIC_THRESHOLD: int = 3     # Lỗi logic code lặp 3 lần -> ESCALATE
    POLICY_THRESHOLD: int = 1    # Vi phạm chính sách an ninh -> FAIL-FAST ngay

    MAX_TRACKED_TASKS: int = 1000  # F2: Giới hạn lưu trữ tránh phình bộ nhớ

    def __init__(self, window_sec: int = 600):
        self.window_sec = window_sec
        # task_id -> {sig_hash: [timestamp1, timestamp2, ...]}
        self._history: Dict[str, Dict[str, List[float]]] = {}
        # task_id -> last_decision
        self._tripped: Dict[str, BreakerDecision] = {}

    def _evict_stale_tasks(self, now: float) -> None:
        """F2: Dọn dẹp các task cũ vượt ngưỡng cửa sổ window_sec để chống rò rỉ RAM."""
        if len(self._history) <= self.MAX_TRACKED_TASKS:
            return
        stale_tasks = []
        for tid, sig_dict in self._history.items():
            all_ts = [t for ts_list in sig_dict.values() for t in ts_list]
            if not all_ts or (now - max(all_ts) > self.window_sec):
                stale_tasks.append(tid)
        for tid in stale_tasks:
            self._history.pop(tid, None)
            self._tripped.pop(tid, None)

    def classify(self, error: Exception | str, tool: str = "unknown") -> ErrorSignature:
        """Classify any exception or error message into a structured ErrorSignature."""
        err_str = str(error).strip()

        # 1. Infrastructure Errors (F3: thu hẹp chỉ bắt lỗi hạ tầng xác thực)
        if any(k in err_str for k in [
            "Expecting value: line 1", "JSONDecodeError", "ConnectionRefused",
            "Cannot connect", "HTTPConnectionPool", "Error calling executor:", "502 Bad Gateway",
            "503 Service Unavailable", "504 Gateway Time-out", "Task timeout"
        ]):
            return ErrorSignature(kind="INFRA", code="JSON_EMPTY_OR_CONN_REFUSED", tool=tool)

        # 2. Policy Violations (F3: thu hẹp không match 'DENIED' mơ hồ, dùng prefix rõ ràng)
        if any(k in err_str for k in [
            "[HARD-DENY]", "HARD-DENY", "HARD BOUNDARY", "HUMAN APPROVAL REQUIRED", "FAIL-CLOSED"
        ]):
            return ErrorSignature(kind="POLICY", code="POLICY_HARD_DENIAL", tool=tool)

        # 3. Tool Contract Violations
        if any(k in err_str for k in [
            "TOOL_CONTRACT_NOT_FOUND", "CONTRACT_VIOLATION", "Missing required field",
            "Type mismatch", "Tool not recognized"
        ]):
            return ErrorSignature(kind="CONTRACT", code="TOOL_CONTRACT_FAILURE", tool=tool)

        # 4. Syntax & Code Errors
        if any(k in err_str for k in ["SyntaxError", "IndentationError", "NameError", "TypeError"]):
            return ErrorSignature(kind="LOGIC", code="SYNTAX_OR_NAME_ERROR", tool=tool)

        # Default fallback
        return ErrorSignature(kind="LOGIC", code="GENERAL_EXECUTION_FAILURE", tool=tool)

    def record(self, task_id: str, signature: ErrorSignature) -> BreakerDecision:
        """
        Records an error for a given task and signature.
        Returns BreakerDecision indicating whether retry is allowed or circuit is broken.
        """
        now = time.time()
        self._evict_stale_tasks(now)
        if task_id not in self._history:
            self._history[task_id] = {}

        sig_hash = signature.get_hash()
        if sig_hash not in self._history[task_id]:
            self._history[task_id][sig_hash] = []

        # Filter window
        self._history[task_id][sig_hash] = [
            t for t in self._history[task_id][sig_hash] if now - t <= self.window_sec
        ]
        self._history[task_id][sig_hash].append(now)
        count = len(self._history[task_id][sig_hash])

        # Evaluate threshold by kind
        if signature.kind == "INFRA" and count >= self.INFRA_THRESHOLD:
            decision = BreakerDecision(
                action="FAIL_FAST",
                reason=f"CIRCUIT BREAKER TRIPPED [INFRA]: Infrastructure failure on tool '{signature.tool}' repeated {count} times ({signature.code}). Halting to prevent infinite loop.",
                error_count=count,
                signature=signature
            )
            self._tripped[task_id] = decision
            logger.critical("🛑 [CIRCUIT-BREAKER-TRIPPED] %s", decision.reason)
            return decision

        if signature.kind == "CONTRACT" and count >= self.CONTRACT_THRESHOLD:
            decision = BreakerDecision(
                action="FAIL_FAST",
                reason=f"CIRCUIT BREAKER TRIPPED [CONTRACT]: Schema/Contract violation on tool '{signature.tool}' repeated {count} times ({signature.code}).",
                error_count=count,
                signature=signature
            )
            self._tripped[task_id] = decision
            logger.error("🛑 [CIRCUIT-BREAKER-TRIPPED] %s", decision.reason)
            return decision

        if signature.kind == "POLICY" and count >= self.POLICY_THRESHOLD:
            decision = BreakerDecision(
                action="FAIL_FAST",
                reason=f"CIRCUIT BREAKER TRIPPED [POLICY]: Security policy rejection on tool '{signature.tool}' ({signature.code}).",
                error_count=count,
                signature=signature
            )
            self._tripped[task_id] = decision
            logger.warning("🛑 [CIRCUIT-BREAKER-TRIPPED] %s", decision.reason)
            return decision

        if signature.kind == "LOGIC" and count >= self.LOGIC_THRESHOLD:
            decision = BreakerDecision(
                action="ESCALATE",
                reason=f"CIRCUIT BREAKER TRIPPED [LOGIC]: Code/Logic error repeated {count} times on '{signature.tool}'. Escalate to Master.",
                error_count=count,
                signature=signature
            )
            self._tripped[task_id] = decision
            logger.warning("⚠️ [CIRCUIT-BREAKER-ESCALATE] %s", decision.reason)
            return decision

        return BreakerDecision(
            action="ALLOW_RETRY",
            reason="Retry allowed within safety threshold.",
            error_count=count,
            signature=signature
        )

    def is_tripped(self, task_id: str) -> Tuple[bool, Optional[BreakerDecision]]:
        """Returns True and the decision if the breaker is active for task_id."""
        dec = self._tripped.get(task_id)
        if dec:
            return True, dec
        return False, None

    def reset(self, task_id: str) -> None:
        """Reset breaker state for task_id upon successful completion."""
        self._history.pop(task_id, None)
        self._tripped.pop(task_id, None)


# Global singleton instance
replan_circuit_breaker = ReplanCircuitBreaker()
