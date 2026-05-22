"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH — COGNITIVE GUARDRAILS v1.0                                   ║
║  "AI thông minh biết khi nào dừng lại."                                    ║
║   Loop detection · Token watchdog · Replan limiter · Divergence detector   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Vấn đề cần giải quyết:
  - Recursive replanning vô hạn (Planner → fail → replan → fail → ...)
  - Tool được gọi với cùng args nhiều lần (loop không thoát)
  - Token runaway (task đơn giản tốn 50k tokens)
  - Agent disagreement storm (Planner và Critic mâu thuẫn vô hạn)

Cách dùng:
  guardrails = CognitiveGuardrails(task_id)
  # Trước mỗi tool call:
  check = guardrails.check_before_tool(tool_id, args)
  if check.should_abort:
      raise GuardrailException(check.reason)
"""

import hashlib
import json
import time
import logging
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("JKAI.Guardrails")


# ─────────────────────────────────────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GuardrailViolation:
    should_abort:  bool
    should_warn:   bool
    violation:     str                    # "loop" | "token" | "replan" | "divergence" | "ok"
    reason:        str
    suggested_action: str                 # Gợi ý xử lý


class GuardrailException(Exception):
    def __init__(self, reason: str, violation: str = "guardrail"):
        super().__init__(reason)
        self.violation = violation


# ─────────────────────────────────────────────────────────────────────────────
#  COGNITIVE GUARDRAILS
# ─────────────────────────────────────────────────────────────────────────────

class CognitiveGuardrails:
    """
    Bộ giám sát nhận thức — chạy liên tục trong suốt task lifecycle.

    Không phải blocker. Là advisor.
    Ưu tiên warn trước, abort chỉ khi vượt hard limit.
    """

    # ── HARD LIMITS (không thể override) ────────────────────────────────────
    MAX_REPLAN_DEPTH          = 3      # Số lần replan tối đa trong 1 task
    MAX_CRITIC_LOOPS          = 4      # Planner ↔ Critic max vòng lặp
    MAX_IDENTICAL_TOOL_CALLS  = 2      # Tool + identical args tối đa 2 lần
    MAX_TOTAL_TOKENS          = 50_000 # Hard cap token toàn task
    MAX_PARALLEL_STEPS        = 8      # Số steps parallel tối đa
    MAX_BRANCHING_FACTOR      = 4      # Tối đa 4 sub-steps từ 1 replan
    MAX_ELAPSED_MINUTES       = 15     # Task timeout tổng

    # ── SOFT LIMITS (warn nhưng không abort) ────────────────────────────────
    WARN_REPLAN_DEPTH         = 2
    WARN_TOKEN_THRESHOLD      = 30_000
    WARN_ELAPSED_MINUTES      = 10

    def __init__(self, task_id: str, on_violation: Optional[Callable] = None) -> None:
        self.task_id     = task_id
        self._on_violation = on_violation  # Callback để publish lên monitor

        # State counters
        self._replan_count:   int   = 0
        self._critic_loops:   int   = 0
        self._total_tokens:   int   = 0
        self._start_time:     float = time.time()
        self._tool_call_log:  Deque[Tuple[str, str]] = deque(maxlen=50)  # (tool_id, args_hash)

        # Loop detection: tool_id → list of args_hash
        self._tool_fingerprints: Dict[str, List[str]] = defaultdict(list)

        # Plan fingerprints: detect lặp plan
        self._plan_fingerprints: List[str] = []

        # Violation log
        self._violations: List[GuardrailViolation] = []

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def check_before_tool(
        self,
        tool_id: str,
        args:    Dict[str, Any],
    ) -> GuardrailViolation:
        """
        Gọi trước mỗi tool execution.
        Phát hiện loop và hard limits.
        """
        # 1. Token check
        token_check = self._check_token_budget()
        if token_check.should_abort:
            return token_check

        # 2. Elapsed time check
        time_check = self._check_elapsed_time()
        if time_check.should_abort:
            return time_check

        # 3. Loop detection
        args_hash = self._hash_args(args)
        prior_calls = self._tool_fingerprints[tool_id]

        if args_hash in prior_calls:
            count = prior_calls.count(args_hash)
            if count >= self.MAX_IDENTICAL_TOOL_CALLS:
                violation = GuardrailViolation(
                    should_abort   = True,
                    should_warn    = True,
                    violation      = "loop",
                    reason         = f"Tool '{tool_id}' đã được gọi {count+1} lần với cùng arguments. Loop detected.",
                    suggested_action = "Chuyển sang fallback_tool hoặc thay đổi approach.",
                )
                self._record_violation(violation)
                return violation

            # Warn khi bắt đầu lặp
            return GuardrailViolation(
                should_abort    = False,
                should_warn     = True,
                violation       = "loop_warning",
                reason          = f"Tool '{tool_id}' đã được gọi với args tương tự. Monitor.",
                suggested_action = "Xem xét thay đổi args hoặc cách tiếp cận.",
            )

        # Ghi nhận call fingerprint
        prior_calls.append(args_hash)
        self._tool_call_log.append((tool_id, args_hash))

        return GuardrailViolation(
            should_abort  = False,
            should_warn   = False,
            violation     = "ok",
            reason        = "",
            suggested_action = "",
        )

    def check_before_replan(self, new_plan: List[Dict]) -> GuardrailViolation:
        """Gọi trước mỗi lần Planner tạo plan mới (replan)."""
        self._replan_count += 1

        # Hard limit
        if self._replan_count > self.MAX_REPLAN_DEPTH:
            violation = GuardrailViolation(
                should_abort  = True,
                should_warn   = True,
                violation     = "replan",
                reason        = f"Đã replan {self._replan_count} lần — vượt giới hạn ({self.MAX_REPLAN_DEPTH}).",
                suggested_action = "Trả về plan cuối cùng với feedback, yêu cầu Master review.",
            )
            self._record_violation(violation)
            return violation

        # Detect plan lặp (plan mới giống plan cũ)
        plan_hash = self._hash_plan(new_plan)
        if plan_hash in self._plan_fingerprints:
            violation = GuardrailViolation(
                should_abort  = True,
                should_warn   = True,
                violation     = "plan_loop",
                reason        = "Planner đang tạo ra plan trùng lặp. Tư duy đang drift.",
                suggested_action = "Inject fresh context hoặc escalate lên Master.",
            )
            self._record_violation(violation)
            return violation

        self._plan_fingerprints.append(plan_hash)

        # Soft warning
        if self._replan_count >= self.WARN_REPLAN_DEPTH:
            return GuardrailViolation(
                should_abort  = False,
                should_warn   = True,
                violation     = "replan_warning",
                reason        = f"Đã replan {self._replan_count} lần. Tiếp cận giới hạn.",
                suggested_action = "Cân nhắc giảm scope hoặc clarify goal.",
            )

        return GuardrailViolation(False, False, "ok", "", "")

    def check_critic_loop(self) -> GuardrailViolation:
        """Gọi mỗi khi Critic phản hồi Planner."""
        self._critic_loops += 1

        if self._critic_loops > self.MAX_CRITIC_LOOPS:
            violation = GuardrailViolation(
                should_abort  = True,
                should_warn   = True,
                violation     = "critic_loop",
                reason        = f"Planner ↔ Critic đã loop {self._critic_loops} lần. Debate storm detected.",
                suggested_action = "Accept plan hiện tại với caveat. Không tiếp tục debate.",
            )
            self._record_violation(violation)
            return violation

        return GuardrailViolation(False, False, "ok", "", "")

    def record_tokens_used(self, count: int) -> GuardrailViolation:
        """Cập nhật token counter và kiểm tra budget."""
        self._total_tokens += count
        return self._check_token_budget()

    def check_parallel_steps(self, parallel_count: int) -> GuardrailViolation:
        """Kiểm tra số steps parallel không vượt giới hạn."""
        if parallel_count > self.MAX_PARALLEL_STEPS:
            return GuardrailViolation(
                should_abort  = False,
                should_warn   = True,
                violation     = "parallel_limit",
                reason        = f"{parallel_count} steps parallel — khuyến nghị max {self.MAX_PARALLEL_STEPS}.",
                suggested_action = "Nhóm các steps thành batches.",
            )
        return GuardrailViolation(False, False, "ok", "", "")

    def get_health_report(self) -> Dict[str, Any]:
        """Snapshot trạng thái guardrails hiện tại."""
        elapsed = (time.time() - self._start_time) / 60
        return {
            "task_id":         self.task_id,
            "replan_count":    self._replan_count,
            "critic_loops":    self._critic_loops,
            "total_tokens":    self._total_tokens,
            "elapsed_min":     round(elapsed, 2),
            "tool_calls":      len(self._tool_call_log),
            "violations":      len(self._violations),
            "status":          self._compute_status(),
        }

    def inject_context_for_planner(self) -> str:
        """
        Cung cấp guardrail status cho Planner biết mà điều chỉnh.
        Không dài dòng — chỉ những gì quan trọng.
        """
        lines = []
        if self._replan_count > 0:
            lines.append(f"[GUARDRAIL] Đã replan {self._replan_count}/{self.MAX_REPLAN_DEPTH} lần.")
        if self._total_tokens > self.WARN_TOKEN_THRESHOLD:
            remaining = self.MAX_TOTAL_TOKENS - self._total_tokens
            lines.append(f"[GUARDRAIL] Token còn lại ~{remaining:,}. Ưu tiên giải pháp ngắn gọn.")
        if self._critic_loops > 2:
            lines.append(f"[GUARDRAIL] Critic đã loop {self._critic_loops} lần. Hạn chế debate.")
        return "\n".join(lines) if lines else ""

    # ── PRIVATE HELPERS ───────────────────────────────────────────────────────

    def _check_token_budget(self) -> GuardrailViolation:
        if self._total_tokens >= self.MAX_TOTAL_TOKENS:
            violation = GuardrailViolation(
                should_abort   = True,
                should_warn    = True,
                violation      = "token_exhausted",
                reason         = f"Token budget exhausted: {self._total_tokens:,}/{self.MAX_TOTAL_TOKENS:,}.",
                suggested_action = "Dừng task, trả về kết quả tốt nhất hiện có.",
            )
            self._record_violation(violation)
            return violation

        if self._total_tokens >= self.WARN_TOKEN_THRESHOLD:
            return GuardrailViolation(
                should_abort  = False,
                should_warn   = True,
                violation     = "token_warning",
                reason        = f"Đã dùng {self._total_tokens:,} tokens — tiếp cận giới hạn.",
                suggested_action = "Ưu tiên fast model và ngắn gọn.",
            )

        return GuardrailViolation(False, False, "ok", "", "")

    def _check_elapsed_time(self) -> GuardrailViolation:
        elapsed_min = (time.time() - self._start_time) / 60

        if elapsed_min >= self.MAX_ELAPSED_MINUTES:
            return GuardrailViolation(
                should_abort   = True,
                should_warn    = True,
                violation      = "timeout",
                reason         = f"Task timeout: {elapsed_min:.1f}/{self.MAX_ELAPSED_MINUTES} phút.",
                suggested_action = "Trả về partial result, notify Master.",
            )

        if elapsed_min >= self.WARN_ELAPSED_MINUTES:
            return GuardrailViolation(
                should_abort   = False,
                should_warn    = True,
                violation      = "time_warning",
                reason         = f"Task đã chạy {elapsed_min:.1f} phút.",
                suggested_action = "Tăng tốc: bỏ verification không critical.",
            )

        return GuardrailViolation(False, False, "ok", "", "")

    def _hash_args(self, args: Dict[str, Any]) -> str:
        """Hash tool args để detect identical calls."""
        try:
            serialized = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
            return hashlib.sha256(serialized.encode()).hexdigest()[:16]
        except:
            return hashlib.md5(str(args).encode()).hexdigest()[:16]

    def _hash_plan(self, plan: List[Dict]) -> str:
        """Hash plan structure để detect plan loops."""
        try:
            structure = [(s.get("tool", ""), s.get("description", "")[:30]) for s in plan]
            return hashlib.md5(str(structure).encode()).hexdigest()[:16]
        except:
            return str(len(plan))

    def _compute_status(self) -> str:
        if self._violations:
            abort_violations = [v for v in self._violations if v.should_abort]
            if abort_violations:
                return "critical"
            return "warning"
        return "healthy"

    def _record_violation(self, violation: GuardrailViolation) -> None:
        self._violations.append(violation)
        logger.warning(f"[GUARDRAIL-VIOLATION]: {violation.violation} | {violation.reason}")
        if self._on_violation:
            try:
                self._on_violation(self.task_id, violation)
            except:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION REGISTRY — Quản lý guardrails theo task_id
# ─────────────────────────────────────────────────────────────────────────────

class GuardrailRegistry:
    """
    Factory để lấy Guardrails instance theo task_id.
    Tự động cleanup task đã xong.
    """
    def __init__(self) -> None:
        self._sessions: Dict[str, CognitiveGuardrails] = {}

    def get_or_create(
        self,
        task_id:       str,
        on_violation:  Optional[Callable] = None,
    ) -> CognitiveGuardrails:
        if task_id not in self._sessions:
            self._sessions[task_id] = CognitiveGuardrails(task_id, on_violation)
        return self._sessions[task_id]

    def close(self, task_id: str) -> Optional[Dict[str, Any]]:
        guard = self._sessions.pop(task_id, None)
        if guard:
            report = guard.get_health_report()
            logger.info(f"[GUARDRAIL-REGISTRY]: Task {task_id} closed. Report: {report}")
            return report
        return None

    def get_all_health(self) -> List[Dict[str, Any]]:
        return [g.get_health_report() for g in self._sessions.values()]


# Singleton
guardrail_registry = GuardrailRegistry()


# ─────────────────────────────────────────────────────────────────────────────
#  HƯỚNG DẪN TÍCH HỢP
# ─────────────────────────────────────────────────────────────────────────────
"""
1. Trong planner.py — Trước mỗi attempt replan:

    from cognitive_guardrails import guardrail_registry
    guard = guardrail_registry.get_or_create(task_id, on_violation=self._log_violation)

    # Trước replan:
    check = guard.check_before_replan(steps)
    if check.should_abort:
        return {"status": "guardrail_abort", "reason": check.reason}

    # Inject vào system prompt:
    guardrail_ctx = guard.inject_context_for_planner()
    if guardrail_ctx:
        messages.append({"role": "system", "content": guardrail_ctx})

    # Sau mỗi engine.call_chat():
    guard.record_tokens_used(estimated_tokens)

    # Trong critic loop:
    critic_check = guard.check_critic_loop()
    if critic_check.should_abort:
        # Accept plan hiện tại luôn
        return blueprint.model_dump()

2. Trong executor.py — Trước mỗi tool call:

    check = guard.check_before_tool(step.tool, step.args)
    if check.should_abort:
        raise GuardrailException(check.reason, check.violation)
    if check.should_warn:
        engine.publish_mission_log("GUARDRAIL", check.reason, task_id)

3. Khi task kết thúc:

    final_report = guardrail_registry.close(task_id)
    engine.publish_mission_log("GUARDRAIL", str(final_report), task_id)
"""
