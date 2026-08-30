"""
JKAI AI OS — Intent & Governor Handler
T-0.2 & T-6: Tích hợp CentralIntentRouter v4.0 và Single-Pass TaskProfiler / ExecutionGovernor.
Chỉ gọi phân tích hồ sơ task đúng một lần duy nhất và lưu vào plan.
"""

from __future__ import annotations

import hashlib
import logging
from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry
from core.os.routing.intent_router import CentralIntentRouter
from core.os.cognition.task_profiler import profile_task
from core.os.cognition.execution_governor import govern_execution, ExecutionTopology

logger = logging.getLogger("jkai.os.orchestrator.intent")


class IntentGovernorHandler(BaseHandler):
    """Phân loại ý định, xây dựng hồ sơ nhiệm vụ và thiết lập Execution Policy (1 Lần Duy Nhất)."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g = plan.goal
        merged_kw = {**ctx.kwargs, **plan.kwargs_patch}

        # ── 1. Trace F1 Goal Identity ──
        try:
            pref_goal_hash = hashlib.sha256(g.encode("utf-8")).hexdigest()[:16]
            log_telemetry(
                plan, "TRACE",
                f"F1 goal identity | len={len(g)} | preview={g[:200]!r} | hash={pref_goal_hash} "
                f"| task_id={ctx.task_id} | trace_id={ctx.trace_id}",
                stealth=True
            )
        except Exception:
            pass

        # ── 2. CentralIntentRouter v4.0 Multi-Label Routing ──
        try:
            from core.os.routing.intent_router import intent_router
            route_decision = intent_router.route(g, history=ctx.history)
            plan.route_decision = route_decision
            # Chỉ ghi đè os_intent nếu chưa được gán bởi SlashCommand hoặc module chuyên biệt
            if not plan.os_intent or plan.os_intent == "general":
                plan.os_intent = route_decision.mode.value.lower()
            plan.capability_tags = sorted(list(set(plan.capability_tags) | set(route_decision.tags or [])))
        except Exception as router_err:
            logger.debug("[CENTRAL-ROUTER-FALLBACK] %s", router_err)
            from core.os.intent_taxonomy import classify_os_intent, capability_tags
            if not plan.os_intent or plan.os_intent == "general":
                plan.os_intent = classify_os_intent(g, {**merged_kw, "history": ctx.history}).value
            plan.capability_tags = sorted(list(set(plan.capability_tags) | set(capability_tags(g, merged_kw))))

        # ── 3. Team Pattern Inference ──
        try:
            from core.utils.team_patterns import infer_team_pattern
            plan.team_pattern = infer_team_pattern(g).id
            merged_kw["team_pattern"] = plan.team_pattern
        except Exception:
            pass

        # ── 4. Single-Pass Task Profiler & Execution Governor ──
        mode_param = (ctx.kwargs.get("mode") or "fast").lower()
        task_prof = profile_task(g, ctx.history, merged_kw)
        exec_policy = govern_execution(task_prof, requested_mode=mode_param)

        plan.task_profile = task_prof
        plan.execution_policy = exec_policy

        log_telemetry(
            plan, "ZENITH",
            f"Task Profile: {task_prof.reason_codes} | Policy Topology: {exec_policy.topology.value} ({exec_policy.user_facing_mode})",
            stealth=True
        )

        return HandlerResult(early_exit=False)
