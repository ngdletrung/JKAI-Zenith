"""
JKAI AI OS — Workspace Scope Handler
T-5: Xác định mục tiêu workspace, web-only analysis scope, và phân quyền Cursor Agent.
"""

from __future__ import annotations

import logging
from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.workspace")


class WorkspaceScopeHandler(BaseHandler):
    """Xác định phạm vi Workspace và quyền Cursor Agent trước khi tạo MissionState."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g = plan.goal
        kw_patch = plan.kwargs_patch

        try:
            from core.utils.project_workspace import (
                enrich_goal_for_workspace_target,
                detect_workspace_target,
                goal_forces_web_analysis_pipeline,
                goal_is_external_repo_url_analysis,
                workspace_scope_exists,
            )

            scope = None
            if kw_patch.get("jkai_cloned_repos"):
                scope = kw_patch.get("jkai_workspace_target")
            elif goal_forces_web_analysis_pipeline(g) or (
                goal_is_external_repo_url_analysis(g) and not kw_patch.get("jkai_cloned_repos")
            ):
                kw_patch["jkai_web_only_analysis"] = True
                g = (
                    g.strip()
                    + "\n\n[JKAI WEB-ONLY]\n"
                    "- Đọc/scrape URL đã cho (README / trang web).\n"
                    "- KHÔNG list_dir toàn workspace JKAI.\n"
                    "- Ưu tiên SEARCH_WEB_GLOBAL / read_url.\n"
                )
                log_telemetry(plan, "ZENITH", "WEB-ONLY pipeline.")
            else:
                scope = detect_workspace_target(g)

            if scope and not workspace_scope_exists(scope):
                log_telemetry(plan, "WARN", f"Workspace `{scope}` không tồn tại — bỏ scope.")
                scope = None

            if scope:
                g, scope, scope_mode = enrich_goal_for_workspace_target(g, target=scope)
                kw_patch["jkai_workspace_target"] = scope
                kw_patch["jkai_project_root"] = scope
                kw_patch["jkai_project_mode"] = scope_mode
                log_telemetry(plan, "ZENITH", f"WORKSPACE `{scope}` ({scope_mode})")

            # 🛡️ Xác định sớm use_cursor_agent trước khi tạo MissionState
            use_agent = bool(scope) and not kw_patch.get("jkai_fast_fix") and not kw_patch.get("jkai_web_only_analysis")
            if use_agent and ctx.container:
                try:
                    from core.kernel.project_agent_loop import _env_enabled
                    plan.use_cursor_agent = _env_enabled()
                except Exception:
                    plan.use_cursor_agent = False
            else:
                plan.use_cursor_agent = False

        except Exception as e:
            logger.warning("[WORKSPACE-SCOPE-ERR] %s", e)

        plan.goal = g
        plan.kwargs_patch = kw_patch
        return HandlerResult(early_exit=False)
