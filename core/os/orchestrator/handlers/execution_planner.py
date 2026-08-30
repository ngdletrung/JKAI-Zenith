"""
JKAI AI OS — Execution Planner Handler
T-7 & T-8: Nạp WorldState, MemoryState, khởi tạo MissionState và gọi ExecutionPlanner tạo execution steps.
"""

from __future__ import annotations

import logging
from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry
from core.os.orchestrator.pipeline_resolver import PipelineResolver
from core.os.mission_state import MissionState
from core.utils.engine import engine

logger = logging.getLogger("jkai.os.orchestrator.planner")


class ExecutionPlannerHandler(BaseHandler):
    """Khởi tạo trạng thái thế giới và lập kế hoạch thực thi đa tầng."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g = plan.goal
        kw_patch = plan.kwargs_patch
        merged_kw = {**ctx.kwargs, **kw_patch}
        trace_id = ctx.trace_id

        # ── 1. Pipeline Resolution Trước Khi Tạo MissionState ──
        mode_param = (ctx.kwargs.get("mode") or "fast").lower()
        user_explicit_deep = mode_param in ("deep", "deliberative") or "/deep" in g.lower() or ctx.kwargs.get("deep")
        has_deep_skill = bool(kw_patch.get("resolved_skill_ids")) and mode_param != "fast"

        PipelineResolver.apply_to_plan(
            plan=plan,
            exec_policy=plan.execution_policy,
            requested_mode=mode_param,
            user_explicit_deep=bool(user_explicit_deep),
            has_deep_skill=has_deep_skill
        )

        # ── 2. Khởi tạo MissionState Ban Đầu ──
        plan.mission_state = MissionState.from_os_plan(
            plan=plan,
            goal=plan.goal,
            original_goal=g,
            task_id=ctx.task_id,
            kwargs=merged_kw,
            trace_id=trace_id,
        )
        plan.mission_state.use_cursor_agent = plan.use_cursor_agent

        cached_manifest = engine.cache_get(ctx.task_id, "intent_manifest")
        if cached_manifest:
            plan.mission_state.routing_manifest = cached_manifest

        # ── 3. Capture World State ──
        try:
            from core.os.world_state import WorldStateMonitor
            workspace_path = kw_patch.get("jkai_workspace_target") or "/workspace"
            world = await WorldStateMonitor.capture_state(workspace_path)
            plan.mission_state.world_state = world
        except Exception as ws_err:
            logger.debug("[WORLD-STATE-CAPTURE-ERR] %s", ws_err)
            world = None

        # ── 4. Capture Memory State ──
        try:
            from core.os.memory_state import MemoryState
            summary = ""
            try:
                from context.mission_context import ctx_mgr
                prev_mission_id = ctx_mgr.get_linked_mission("default")
                if prev_mission_id and prev_mission_id != ctx.task_id:
                    prev_mc = ctx_mgr.get_or_create(prev_mission_id)
                    if prev_mc.conversation.get("last_subject"):
                        summary = prev_mc.conversation.get("last_answer", "")[:200]
            except Exception:
                pass

            plan.mission_state.memory_state = MemoryState(
                reflex_cache_hit=False,
                conversation_summary=summary,
                learned_patterns=[]
            )
        except Exception as mem_err:
            logger.debug("[MEMORY-STATE-CAPTURE-ERR] %s", mem_err)

        # ── 5. Run ExecutionPlanner (Layer 4) để tạo steps ──
        try:
            from core.os.execution_planner import ExecutionPlanner
            exec_plan = await ExecutionPlanner.generate_plan(plan.mission_state, world)
            plan.mission_state.execution_plan = exec_plan
            plan.steps = getattr(exec_plan, "steps", []) or plan.steps

            # 🛡️ Củng cố lại Pipeline Resolution lần cuối: Không cho Planner override mode của Master
            PipelineResolver.apply_to_plan(
                plan=plan,
                exec_policy=plan.execution_policy,
                requested_mode=mode_param,
                user_explicit_deep=bool(user_explicit_deep),
                has_deep_skill=has_deep_skill,
                log_event=False
            )
            engine._increment_stat(plan.pipeline)

        except Exception as plan_err:
            logger.error("[EXECUTION-PLANNER-ERR] %s", plan_err)
            plan.pipeline = "fast"
            plan.is_fast = True
            plan.is_deep = False
            plan.execution_mode = "fast"

        # ── 6. Cập nhật Shared Context & Telemetry Log ──
        log_telemetry(
            plan,
            "SYSTEM",
            f"AI OS: intent={plan.os_intent} pipeline={plan.pipeline} "
            f"mode={plan.execution_mode} tags={','.join(plan.capability_tags) or '-'}",
            stealth=True
        )

        engine.cache_put(ctx.task_id, "pipeline", plan.pipeline)
        engine.cache_put(ctx.task_id, "execution_mode", plan.execution_mode)
        engine.cache_put(ctx.task_id, "os_intent", plan.os_intent)
        engine.cache_put(ctx.task_id, "is_fast", plan.is_fast)
        engine.cache_put(ctx.task_id, "is_deep", plan.is_deep)
        engine.cache_put(ctx.task_id, "capability_tags", plan.capability_tags)
        if plan.mission_state:
            engine.cache_put(ctx.task_id, "mission_state", plan.mission_state)
        engine.save_routing_stats()

        return HandlerResult(early_exit=False)
