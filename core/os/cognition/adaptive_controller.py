# -*- coding: utf-8 -*-
"""
core/os/cognition/adaptive_controller.py
========================================
JKAI Zenith — Cognitive Adaptive Controller (Phase A2).
Directive: Master Lee Trung's Approved Strategic Pivot & SOP v2.4.

Chức năng cốt lõi:
Lựa chọn chiến lược dựa trên trạng thái và bằng chứng thực tế (không dựa vào tên tác vụ đơn thuần):
1. Tác vụ đơn giản (FAST_DIRECT): Model nhỏ xử lý trực tiếp không qua DAG.
2. Tác vụ nhiều bước (MULTI_STEP_PLANNING): Lập kế hoạch DAG, lưu checkpoint, theo dõi tiến độ.
3. Gặp lỗi (ERROR_ADAPTIVE_RECOVERY): Phân tích bằng chứng lỗi, chọn nhánh phục hồi khác (cấm lặp mù).
4. Thiếu thông tin (ASK_USER_CLARIFICATION): Dừng lại hỏi Master thay vì đoán/hallucinate.
5. Nguy cơ/Không chắc chắn (ESCALATE_MODEL_OR_HUMAN): Chuyển tiếp model lớn hoặc yêu cầu phê duyệt.

Nguyên lý: Model đề xuất chiến lược; Runtime kiểm soát quyền thực thi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger("JKAI.Cognition.AdaptiveController")


class AdaptiveStrategy(str, Enum):
    FAST_DIRECT = "FAST_DIRECT"
    MULTI_STEP_PLANNING = "MULTI_STEP_PLANNING"
    ERROR_ADAPTIVE_RECOVERY = "ERROR_ADAPTIVE_RECOVERY"
    ASK_USER_CLARIFICATION = "ASK_USER_CLARIFICATION"
    ESCALATE_MODEL_OR_HUMAN = "ESCALATE_MODEL_OR_HUMAN"


@dataclass
class CognitiveStateSnapshot:
    mission_id: str
    prompt: str
    is_multi_step: bool = False
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)
    missing_information_keys: List[str] = field(default_factory=list)
    uncertainty_score: float = 0.0  # [0.0, 1.0]
    safety_risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    failed_attempts_count: int = 0
    step_budget_remaining: int = 5
    model_suggested_strategy: Optional[str] = None
    last_strategy_tried: Optional[str] = None
    outcome_status: Optional[str] = None  # COMPLETE, INCOMPLETE, BLOCKED, PARTIAL
    unresolved_criteria_ids: List[str] = field(default_factory=list)
    verified_criteria_ids: List[str] = field(default_factory=list)


@dataclass
class ControllerDecision:
    selected_strategy: AdaptiveStrategy
    rationale: str
    step_budget: int
    require_user_interaction: bool = False
    escalation_target: Optional[str] = None
    recovery_branch: Optional[str] = None
    retrieved_memory_ids: List[str] = field(default_factory=list)
    grounded_scaffolding_prompt: str = ""



class AdaptiveController:
    """
    Bộ điều khiển thích ứng lựa chọn chiến lược theo trạng thái thực tế.
    """

    def __init__(self, default_step_budget: int = 5):
        self.default_step_budget = default_step_budget

    def decide_strategy(
        self,
        state: CognitiveStateSnapshot,
        trace_id: Optional[str] = None,
    ) -> ControllerDecision:
        """
        Ra quyết định chiến lược dựa trên trạng thái nhận thức.
        """
        # 1. Chốt chặn An toàn tối thượng (Invariant 1): Nguy cơ an toàn hoặc độ bất định quá cao
        if state.safety_risk_level in ("HIGH", "CRITICAL") or state.uncertainty_score >= 0.8:
            decision = ControllerDecision(
                selected_strategy=AdaptiveStrategy.ESCALATE_MODEL_OR_HUMAN,
                rationale=f"Safety risk '{state.safety_risk_level}' or uncertainty {state.uncertainty_score:.2f} exceeds threshold. Escalating to human authority or stronger model.",
                step_budget=1,
                require_user_interaction=True,
                escalation_target="MASTER_APPROVAL" if state.safety_risk_level in ("HIGH", "CRITICAL") else "TEACHER_MODEL",
            )
            self._sync_telemetry(trace_id, decision)
            return decision

        # 2. Chốt chặn Thiếu thông tin (Invariant 2): Hỏi lại thay vì bịa đặt/đoán
        if state.missing_information_keys:
            missing_str = ", ".join(state.missing_information_keys)
            decision = ControllerDecision(
                selected_strategy=AdaptiveStrategy.ASK_USER_CLARIFICATION,
                rationale=f"Critical information missing ({missing_str}). Requesting clarification from Master instead of guessing.",
                step_budget=1,
                require_user_interaction=True,
            )
            self._sync_telemetry(trace_id, decision)
            return decision

        # 3. Chốt chặn Thích ứng Phục hồi Lỗi & Tái Lập Kế Hoạch (Invariant 3): Gặp lỗi hoặc Kết quả bán phần (PARTIAL/INCOMPLETE)
        has_failure_or_partial = (
            bool(state.recent_errors)
            or state.failed_attempts_count > 0
            or state.outcome_status in ("INCOMPLETE", "PARTIAL")
            or bool(state.unresolved_criteria_ids)
        )
        if has_failure_or_partial:
            if state.failed_attempts_count >= 3:
                # Quá 3 lần thất bại -> Leo thang hỗ trợ
                decision = ControllerDecision(
                    selected_strategy=AdaptiveStrategy.ESCALATE_MODEL_OR_HUMAN,
                    rationale=f"Task failed or incomplete after {state.failed_attempts_count} recovery attempts. Escalating to avoid resource exhaustion.",
                    step_budget=1,
                    require_user_interaction=True,
                    escalation_target="MASTER_APPROVAL",
                )
            else:
                branch = self._select_recovery_branch(state)
                decision = ControllerDecision(
                    selected_strategy=AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY,
                    rationale=f"Detected runtime failure or partial delivery (status: '{state.outcome_status}', attempt {state.failed_attempts_count}). Switching recovery branch to '{branch}' instead of repeating failed command.",
                    step_budget=max(1, state.step_budget_remaining - 1),
                    recovery_branch=branch,
                )
            self._sync_telemetry(trace_id, decision)
            return decision

        # 4. Chốt chặn Tác vụ Nhiều Bước (Invariant 4): Lập kế hoạch và theo dõi tiến độ
        if state.is_multi_step or self._detect_multi_step_intent(state.prompt):
            budget = min(self.default_step_budget, max(2, state.step_budget_remaining))
            decision = ControllerDecision(
                selected_strategy=AdaptiveStrategy.MULTI_STEP_PLANNING,
                rationale="Multi-step task detected. Initializing DAG planning, step checkpointing, and criteria verification.",
                step_budget=budget,
            )
            self._sync_telemetry(trace_id, decision)
            return decision

        # 5. Mặc định: Tác vụ Đơn Giản (Invariant 5): Model nhỏ xử lý trực tiếp không qua DAG
        decision = ControllerDecision(
            selected_strategy=AdaptiveStrategy.FAST_DIRECT,
            rationale="Single-step simple task. Executing directly on small model without planning overhead.",
            step_budget=1,
        )
        self._sync_telemetry(trace_id, decision)
        return decision

    def _select_recovery_branch(self, state: CognitiveStateSnapshot) -> str:
        """Chọn nhánh phục hồi khác biệt, dựa trên bằng chứng lỗi hoặc kết quả bán phần."""
        # Ưu tiên 1: Kết quả bán phần (PARTIAL/INCOMPLETE) hoặc có tiêu chí chưa hoàn thành -> TARGETED_REPAIR
        if state.outcome_status in ("INCOMPLETE", "PARTIAL") or state.unresolved_criteria_ids:
            return "TARGETED_REPAIR"

        last_err = state.recent_errors[-1] if state.recent_errors else {}
        err_msg = str(last_err.get("error", "")).lower()

        if "syntax" in err_msg or "argument" in err_msg:
            return "ARGUMENT_RE_ENCODING"
        if "timeout" in err_msg or "network" in err_msg:
            return "FALLBACK_OFFLINE_SEARCH"
        if any(k in err_msg for k in ("not found", "no such file", "permission", "access denied", "enoent")):
            return "PATH_RECONCILIATION"
        if state.last_strategy_tried == AdaptiveStrategy.FAST_DIRECT:
            return "PROMOTE_TO_DAG_WITH_CHECKPOINT"

        return "DEEP_BACKTRACK_REPLAN"

    def _detect_multi_step_intent(self, prompt: str) -> bool:
        """Phát hiện yêu cầu gồm nhiều bước hoặc nhiều đầu ra."""
        p_lower = prompt.lower()
        triggers = [
            "và sau đó", "đồng thời", "các bước", "bước 1", "bước 2",
            "tạo và sửa", "phân tích và viết", "tìm kiếm và tổng hợp",
            "sau khi", "tiếp theo", "toàn bộ các file", "nhiều file"
        ]
        return any(t in p_lower for t in triggers) or len(prompt.splitlines()) > 3

    def decide_strategy_with_memory(
        self,
        state: CognitiveStateSnapshot,
        memory_store: Optional[Any] = None,
        domain_group: Optional[str] = None,
        base_system_prompt: str = "Bạn là trợ lý AI JKAI. Hãy suy luận chính xác, trả lời ngắn gọn và đúng trọng tâm.",
        top_k: int = 2,
        trace_id: Optional[str] = None,
    ) -> ControllerDecision:
        """
        Ra quyết định chiến lược kết hợp truy xuất động Tri thức & Kinh nghiệm đã xác minh (Phase A4).
        """
        decision = self.decide_strategy(state, trace_id=trace_id)
        if memory_store is None:
            try:
                from core.os.cognition.verified_memory_store import ensure_canonical_memory_store
                memory_store = ensure_canonical_memory_store()
            except Exception as e:
                logger.debug(f"Memory store load bypassed: {e}")
                decision.grounded_scaffolding_prompt = base_system_prompt
                return decision

        retrieved = memory_store.retrieve_for_task(
            prompt=state.prompt,
            domain_group=domain_group,
            strategy=decision.selected_strategy.value,
            top_k=top_k,
        )
        decision.retrieved_memory_ids = [m.memory_id for m in retrieved]
        decision.grounded_scaffolding_prompt = memory_store.build_memory_augmented_system_prompt(
            base_system_prompt=base_system_prompt,
            retrieved_entries=retrieved,
        )
        return decision

    def _sync_telemetry(self, trace_id: Optional[str], decision: ControllerDecision) -> None:
        if not trace_id:
            return
        try:
            from core.telemetry.full_chain_tracer import full_chain_tracer
            if trace_id in full_chain_tracer._active_traces:
                full_chain_tracer.record_controller(
                    trace_id=trace_id,
                    strategy=decision.selected_strategy.value,
                    rationale=decision.rationale,
                    step_budget=decision.step_budget,
                )
        except Exception as e:
            logger.debug(f"Telemetry sync bypassed: {e}")


# Singleton instance
adaptive_controller = AdaptiveController()

