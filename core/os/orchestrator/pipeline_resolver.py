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
        has_deep_mandatory_skill: bool,
        log_event: bool = True
    ) -> Tuple[str, bool, bool, bool]:
        """
        Quyết định pipeline cuối cùng kết hợp Adaptive Hybrid Intelligence.
        Trả về tuple: (pipeline, is_fast, is_deep, use_deep_full)
        """
        req_mode = (requested_mode or "auto").lower()

        # 🛡️ SAFETY GATE (Invariant 0 — Bất biến an toàn tối cao)
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

        # 🧠 ADAPTIVE HYBRID INTELLIGENCE: Phân tích Ý định & Topology để chọn Pipeline tối ưu
        # Ưu tiên lấy từ route_decision của CentralIntentRouter mới nếu có
        route_decision = getattr(plan, "route_decision", None)
        router_mode = getattr(route_decision, "mode", None)
        router_mode_val = router_mode.value.lower() if hasattr(router_mode, "value") else str(router_mode or "").lower()
        
        os_intent = (getattr(plan, "os_intent", "") or router_mode_val).lower()
        tags = getattr(plan, "capability_tags", []) or (getattr(route_decision, "tags", []) if route_decision else [])
        
        # 1. Nhóm Phản xạ Nhanh Siêu Thanh (Fast Reflex): Chào hỏi, Toán học, Tình trạng hệ thống
        is_reflex_intent = (
            os_intent in ("social", "math", "meta_introspection", "meta", "self", "introspection", "chat")
            or any(t in ("SOCIAL", "MATH", "META", "CHAT", "REFLEX") for t in tags)
        )
        
        if is_reflex_intent and not is_high_risk:
            pipeline = "fast"
            is_fast = True
            is_deep = False
            use_deep_full = False
            if log_event:
                log_telemetry(plan, "ZENITH", "⚡ [PIPELINE-RESOLVER]: Phản xạ tức thì FAST (Social/Math/Meta Reflex).", stealth=True)
            return pipeline, is_fast, is_deep, use_deep_full

        # 2. Nhóm Tư Duy Chiến Lược Sâu (Deep Multi-Agent): Lập trình lớn, Kiến trúc, Phản biện đa chiều
        is_complex_intent = (
            user_explicit_deep
            or (has_deep_mandatory_skill and req_mode != "fast")
            or exec_policy.topology == ExecutionTopology.MULTI_AGENT
            or os_intent in ("build", "fix", "refactor", "code", "coding", "architecture")
            or any(t in ("CODING", "ARCHITECTURE", "MULTI_AGENT", "SYSTEM") for t in tags)
        )

        if is_complex_intent or is_high_risk:
            pipeline = "deep"
            is_fast = False
            is_deep = True
            # use_deep_full linh hoạt: chỉ bật full ensemble khi topology là MULTI_AGENT hoặc lệnh phức tạp
            use_deep_full = (exec_policy.topology == ExecutionTopology.MULTI_AGENT or is_high_risk or user_explicit_deep)
            if log_event:
                log_telemetry(plan, "ZENITH", f"🧠 [PIPELINE-RESOLVER]: Chế độ DEEP tự động kích hoạt (Reason: {exec_policy.reason or os_intent}).")
            return pipeline, is_fast, is_deep, use_deep_full

        # 3. Mặc định chạy FAST Standard (Tiết kiệm tài nguyên và sub-second response)
        pipeline = "fast"
        is_fast = True
        is_deep = False
        use_deep_full = False

        # Override đặc biệt cho Fast Fix
        if plan.kwargs_patch.get("jkai_fast_fix"):
            pipeline = "fast_fix"

        reason = "default FAST"
        if is_high_risk:
            reason = "SAFETY_GATE high-risk"
        elif is_reflex_intent:
            reason = "Reflex intent (Social/Math/Meta)"
        elif is_complex_intent:
            reason = f"Complex intent: {exec_policy.reason or os_intent}"
        elif plan.kwargs_patch.get("jkai_fast_fix"):
            reason = "Fast fix override"

        logger.info(f"[PIPELINE-RESOLVER] Decided {pipeline} | is_fast={is_fast} | is_deep={is_deep} | reason: {reason}")
        return pipeline, is_fast, is_deep, use_deep_full

    @classmethod
    def apply_to_plan(
        cls,
        plan: OSRequestPlan,
        exec_policy: ExecutionPolicy,
        requested_mode: str,
        user_explicit_deep: bool,
        has_deep_mandatory_skill: bool,
        log_event: bool = True
    ) -> None:
        """Áp dụng quyết định pipeline vào plan và mission_state."""
        pipeline, is_fast, is_deep, use_deep_full = cls.resolve(
            plan=plan,
            exec_policy=exec_policy,
            requested_mode=requested_mode,
            user_explicit_deep=user_explicit_deep,
            has_deep_mandatory_skill=has_deep_mandatory_skill,
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
