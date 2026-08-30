"""
JKAI AI OS — Pipeline Resolver
Nguồn sự thật duy nhất (Single Source of Truth) quyết định pipeline FAST vs DEEP.
Đảm bảo Chế độ FAST của Master là tối thượng và không bị ghi đè ngầm.
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

from core.os.cognition.execution_governor import ExecutionTopology, ExecutionPolicy
from core.os.orchestrator.types import OSRequestPlan, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.resolver")


class PipelineResolver:
    """Bộ giải quyết lộ trình thực thi tối cao của JKAI AI OS."""

    @staticmethod
    def resolve(
        plan: OSRequestPlan,
        exec_policy: ExecutionPolicy,
        requested_mode: str,
        user_explicit_deep: bool,
        has_deep_skill: bool,
        log_event: bool = True
    ) -> Tuple[str, bool, bool, bool]:
        """
        Quyết định pipeline cuối cùng.
        Trả về tuple: (pipeline, is_fast, is_deep, use_deep_full)
        
        Quy tắc bất biến (Invariants):
        1. Nếu Master yêu cầu 'fast' tường minh -> 100% chạy FAST pipeline (1 model).
        2. Nếu Master yêu cầu 'deep' tường minh hoặc slash /deep -> Chạy DEEP pipeline.
        3. Nếu mode='auto'/unspecified và có deep skill hợp lệ hoặc topology MULTI_AGENT -> Chạy DEEP.
        4. Với REFLEX topology -> Chạy FAST sub-second.
        """
        req_mode = (requested_mode or "fast").lower()

        # 🛡️ SAFETY GATE (Invariant 0 — Không thể bị ghi đè bởi bất kỳ mode nào)
        # Nếu Execution Governor đã xác định topology là MULTI_AGENT với requires_policy_gate=True
        # (tức là high-risk / destructive command), pipeline PHẢI là DEEP bất kể Master yêu cầu gì.
        is_high_risk = (
            exec_policy.requires_policy_gate
            and exec_policy.topology == ExecutionTopology.MULTI_AGENT
        )
        if is_high_risk and not user_explicit_deep:
            pipeline = "deep"
            is_fast = False
            is_deep = True
            use_deep_full = True
            if log_event:
                log_telemetry(
                    plan, "ZENITH",
                    "🛡️ [SAFETY-GATE]: High-risk destructive command detected. "
                    "Overriding to DEEP pipeline (Policy Gate mandatory).",
                )
            return pipeline, is_fast, is_deep, use_deep_full

        # Master ép buộc chạy FAST tường minh -> FAST tối thượng (chỉ với low/medium risk)
        if req_mode == "fast" and not user_explicit_deep:
            pipeline = "fast"
            is_fast = True
            is_deep = False
            use_deep_full = False
            if log_event:
                log_telemetry(plan, "ZENITH", "⚡ [PIPELINE-RESOLVER]: Chế độ FAST tối thượng của Master được duy trì (1 Model).", stealth=True)
            return pipeline, is_fast, is_deep, use_deep_full

        # Master yêu cầu DEEP tường minh hoặc Deep Skill được kích hoạt hợp lệ
        if user_explicit_deep or (has_deep_skill and req_mode != "fast"):
            pipeline = "deep"
            is_fast = False
            is_deep = True
            use_deep_full = True
            if log_event:
                log_telemetry(plan, "ZENITH", f"🧠 [PIPELINE-RESOLVER]: Chế độ DEEP kích hoạt (Reason: {exec_policy.reason}).")
            return pipeline, is_fast, is_deep, use_deep_full

        # Tự động điều phối theo Execution Governor Topology
        if exec_policy.topology == ExecutionTopology.MULTI_AGENT:
            pipeline = "deep"
            is_fast = False
            is_deep = True
            use_deep_full = True
        else:
            pipeline = "fast"
            is_fast = True
            is_deep = False
            use_deep_full = False

        # Override đặc biệt cho Fast Fix
        if plan.kwargs_patch.get("jkai_fast_fix"):
            pipeline = "fast_fix"

        return pipeline, is_fast, is_deep, use_deep_full

    @classmethod
    def apply_to_plan(
        cls,
        plan: OSRequestPlan,
        exec_policy: ExecutionPolicy,
        requested_mode: str,
        user_explicit_deep: bool,
        has_deep_skill: bool,
        log_event: bool = True
    ) -> None:
        """Áp dụng quyết định pipeline vào plan và mission_state."""
        pipeline, is_fast, is_deep, use_deep_full = cls.resolve(
            plan=plan,
            exec_policy=exec_policy,
            requested_mode=requested_mode,
            user_explicit_deep=user_explicit_deep,
            has_deep_skill=has_deep_skill,
            log_event=log_event
        )
        plan.pipeline = pipeline
        plan.execution_mode = pipeline
        plan.is_fast = is_fast
        plan.is_deep = is_deep
        plan.use_deep_full = use_deep_full

        if plan.mission_state:
            plan.mission_state.pipeline = pipeline
            plan.mission_state.execution_mode = pipeline
            plan.mission_state.is_fast = is_fast
            plan.mission_state.is_deep = is_deep
            plan.mission_state.use_deep_full = use_deep_full
