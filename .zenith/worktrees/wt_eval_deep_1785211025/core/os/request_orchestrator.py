"""
JKAI AI OS — Request Orchestrator

Một điểm vào duy nhất: phân loại ý định, làm giàu goal, chọn pipeline, gắn ràng buộc.
Mọi kênh (Mission Control, API, Telegram) nên dùng module này thay vì if/elif rời rạc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.os.intent_taxonomy import (
    OSIntent,
    capability_tags,
    classify_os_intent,
    default_pipeline_for_intent,
)

logger = logging.getLogger("jkai.os.orchestrator")


@dataclass
class OSRequestPlan:
    """Kế hoạch thực thi do AI OS kernel sinh ra."""

    goal: str
    pipeline: str = "auto"
    execution_mode: str = "auto"
    is_deep: bool = False
    is_fast: bool = False
    use_deep_full: bool = False
    use_cursor_agent: bool = False
    os_intent: str = "general"
    team_pattern: str = "pipeline"
    capability_tags: List[str] = field(default_factory=list)
    kwargs_patch: Dict[str, Any] = field(default_factory=dict)
    log_messages: List[Tuple[str, str]] = field(default_factory=list)
    early_response: Optional[Dict[str, Any]] = None

    def merge_into_kwargs(self, kwargs: dict) -> dict:
        out = dict(kwargs or {})
        out.update(self.kwargs_patch)
        return out


def _log(plan: OSRequestPlan, tag: str, msg: str) -> None:
    plan.log_messages.append((tag, msg))


async def orchestrate_request(
    goal: str,
    task_id: str = "system",
    history: Optional[List] = None,
    *,
    check_reflex: bool = True,
    container: Any = None,
    **kwargs,
) -> OSRequestPlan:
    """
    Chuẩn bị mọi yêu cầu Master trước khi Receptionist / TaskManager thực thi.
    """
    plan = OSRequestPlan(goal=(goal or "").strip())
    kw_patch: Dict[str, Any] = {}
    g = plan.goal

    # ── T0: Reflex memory ──
    if check_reflex:
        try:
            from core.utils.cognitive_memory import cognitive_memory

            reflex = await cognitive_memory.check_reflex(g, task_id)
            if reflex:
                _log(plan, "ZENITH", "Phản xạ nơ-ron — trả lời từ bộ nhớ chung.")
                plan.early_response = {
                    "answer": reflex["answer"],
                    "task_id": task_id,
                    "cached": True,
                }
                return plan
        except Exception as e:
            logger.debug("[OS] reflex: %s", e)

    # ── T1: Skill deck inspect ──
    try:
        from core.utils.ingress_skill_gate import try_skill_deck_inspect, enrich_goal_with_deck

        inspect_hit = try_skill_deck_inspect(g)
        if inspect_hit:
            _log(plan, "ZENITH", "Command Deck inspect.")
            try:
                from core.utils.skill_deck_index import SkillDeckIndex
                from core.utils.mission_context import save_context_pack

                refs = SkillDeckIndex.get().parse_refs(g)
                mid = kwargs.get("mission_id")
                if mid and refs:
                    save_context_pack(mid, extra={"last_deck_ids": refs})
            except Exception:
                pass
            plan.early_response = {
                "answer": inspect_hit.get("answer", ""),
                "task_id": task_id,
                **{k: v for v in inspect_hit.items() if k not in ("answer",)},
            }
            return plan

        from core.utils.ingress_skill_gate import try_skill_deck_run_guide

        run_guide = try_skill_deck_run_guide(g, history, kwargs.get("mission_id"))
        if run_guide:
            _log(plan, "ZENITH", "Skill run guide (đầu vào / cách chạy).")
            plan.pipeline = "skill_run_guide"
            plan.os_intent = "skill_run"
            plan.early_response = {
                "answer": run_guide.get("answer", ""),
                "task_id": task_id,
                "pipeline": "skill_run_guide",
                "mode": "fast",
                "source": run_guide.get("source"),
            }
            return plan

        try:
            from core.utils.jkai_capabilities import (
                goal_is_capabilities_inquiry,
                build_capabilities_report,
            )

            if goal_is_capabilities_inquiry(g):
                _log(plan, "ZENITH", "CAPABILITIES — báo cáo registry (không gọi LLM).")
                plan.pipeline = "capabilities"
                plan.os_intent = "capabilities"
                plan.early_response = {
                    "answer": build_capabilities_report(),
                    "task_id": task_id,
                    "pipeline": "capabilities",
                    "mode": "fast",
                }
                return plan
        except Exception as cap_err:
            logger.debug("[OS] capabilities: %s", cap_err)

        g, resolved_ids, deck_warn = enrich_goal_with_deck(g)
        if resolved_ids:
            kw_patch["resolved_skill_ids"] = resolved_ids
            _log(plan, "ZENITH", f"Command Deck → {resolved_ids}")
        if deck_warn:
            _log(plan, "WARN", deck_warn)
    except Exception as e:
        logger.warning("[OS] skill deck: %s", e)

    # ── T2: Mission context ──
    try:
        from core.utils.mission_context import (
            apply_parent_context,
            load_context_pack,
            format_context_block,
        )

        parent_mid = kwargs.get("parent_mission_id")
        mission_mid = kwargs.get("mission_id")
        if parent_mid:
            g = apply_parent_context(g, parent_mid)
            _log(plan, "ZENITH", f"MISSION-CTX parent `{parent_mid}`")
        elif mission_mid:
            pack = load_context_pack(mission_mid)
            block = format_context_block(pack)
            if block:
                g = f"{g.strip()}\n\n{block}"
                _log(plan, "ZENITH", f"MISSION-CTX resume `{mission_mid}`")
    except Exception as e:
        logger.debug("[OS] mission ctx: %s", e)

    # ── T3: Remote repo clone (OS storage) ──
    try:
        from core.utils.repo_clone import enrich_goal_with_repo_clone

        g, clone_rels, clone_err = await enrich_goal_with_repo_clone(g)
        if clone_rels:
            kw_patch["jkai_cloned_repos"] = clone_rels
            kw_patch["jkai_workspace_target"] = clone_rels[0]
            kw_patch["jkai_project_root"] = clone_rels[0]
            kw_patch["jkai_project_mode"] = "audit"
            _log(plan, "ZENITH", f"REPO-CLONE → `{clone_rels[0]}`")
        elif clone_err:
            _log(plan, "WARN", f"REPO-CLONE: {clone_err}")
    except Exception as e:
        logger.warning("[OS] repo clone: %s", e)

    # ── T4: Fast-fix (minimal change) ──
    try:
        from core.utils.fast_fix_routing import (
            goal_should_use_fast_fix_path,
            fast_fix_directive,
            detect_fast_fix_target,
        )

        if goal_should_use_fast_fix_path(g):
            fpath = detect_fast_fix_target(g)
            g = fast_fix_directive(g, fpath)
            kw_patch["jkai_fast_fix"] = True
            kw_patch["jkai_fast_fix_file"] = fpath
            _log(plan, "ZENITH", f"FAST-FIX → `{fpath}`")
    except Exception as e:
        logger.debug("[OS] fast-fix: %s", e)

    # ── T5: Workspace / web-only scope ──
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
        elif goal_forces_web_analysis_pipeline(goal) or (
            goal_is_external_repo_url_analysis(goal) and not kw_patch.get("jkai_cloned_repos")
        ):
            kw_patch["jkai_web_only_analysis"] = True
            g = (
                g.strip()
                + "\n\n[JKAI WEB-ONLY]\n"
                "- Đọc/scrape URL đã cho (README / trang web).\n"
                "- KHÔNG list_dir toàn workspace JKAI.\n"
                "- Ưu tiên SEARCH_WEB_GLOBAL / read_url.\n"
            )
            _log(plan, "ZENITH", "WEB-ONLY pipeline.")
        else:
            scope = detect_workspace_target(goal)

        if scope and not workspace_scope_exists(scope):
            _log(plan, "WARN", f"Workspace `{scope}` không tồn tại — bỏ scope.")
            scope = None
        if scope:
            g, scope, scope_mode = enrich_goal_for_workspace_target(g, target=scope)
            kw_patch["jkai_workspace_target"] = scope
            kw_patch["jkai_project_root"] = scope
            kw_patch["jkai_project_mode"] = scope_mode
            _log(plan, "ZENITH", f"WORKSPACE `{scope}` ({scope_mode})")
    except Exception as e:
        logger.warning("[OS] workspace: %s", e)

    plan.goal = g
    plan.kwargs_patch = kw_patch
    merged_kw = {**kwargs, **kw_patch}

    # ── T6: OS intent + capabilities ──
    intent = classify_os_intent(g, {**merged_kw, "history": history})
    tags = capability_tags(g, merged_kw)
    plan.os_intent = intent.value
    plan.capability_tags = sorted(tags)

    try:
        from core.utils.team_patterns import infer_team_pattern

        plan.team_pattern = infer_team_pattern(g).id
        merged_kw["team_pattern"] = plan.team_pattern
    except Exception:
        pass

    # ── T7: Execution mode (fast / deep / auto) ──
    mode_param = (kwargs.get("mode") or "auto").lower()
    is_deep = mode_param in ("deep", "deliberative") or "/deep" in g.lower() or kwargs.get("deep")
    is_fast = mode_param == "fast" or "/fast" in g.lower() or kw_patch.get("jkai_fast_fix")

    if kw_patch.get("jkai_workspace_target") and not kw_patch.get("jkai_web_only_analysis"):
        is_deep = True
        is_fast = False
    if kw_patch.get("jkai_web_only_analysis"):
        is_deep = True
        is_fast = False

    if not g.startswith("/"):
        try:
            from core.utils.deep_routing import (
                goal_should_force_deep,
                goal_should_force_deep_for_analysis,
            )

            if goal_should_force_deep_for_analysis(g):
                is_deep, is_fast = True, False
                _log(plan, "ZENITH", "DEEP — phân tích (producer_reviewer + CRITIC).")
            elif goal_should_force_deep(g, history):
                is_deep, is_fast = True, False
                _log(plan, "ZENITH", "DEEP — lỗi/debug.")
        except Exception as e:
            logger.warning("[OS] deep routing: %s", e)

    if mode_param == "auto" and not is_deep and not is_fast:
        try:
            from core.utils.intent_cortex import IntentCortex

            cortex = await IntentCortex().analyze(g, history=history, images=kwargs.get("images"))
            if cortex.execution_mode.value in ("DELIBERATIVE", "HYBRID"):
                is_deep = True
                _log(
                    plan,
                    "ZENITH",
                    f"DEEP — IntentCortex ({cortex.execution_mode.value}, "
                    f"complexity={cortex.complexity_score:.2f}).",
                )
            elif getattr(cortex, "intent", None) and str(
                getattr(cortex.intent, "value", cortex.intent)
            ).upper() in ("DEBUG", "BUILD"):
                is_deep = True
                _log(plan, "ZENITH", "DEEP — intent DEBUG/BUILD.")
            elif intent == OSIntent.SOCIAL and cortex.complexity_score < 0.35:
                is_fast = True
            elif default_pipeline_for_intent(intent, tags) == "fast_chat":
                is_fast = True
            else:
                is_fast = not is_deep
        except Exception as e:
            logger.error("[OS] IntentCortex: %s", e)
            is_fast = not is_deep

    plan.is_deep = is_deep
    plan.is_fast = is_fast and not is_deep
    plan.execution_mode = "deep" if is_deep else ("fast" if is_fast else mode_param)

    # ── T8: Pipeline selection ──
    preferred = default_pipeline_for_intent(intent, tags)
    if kw_patch.get("jkai_fast_fix"):
        plan.pipeline = "fast_fix"
    elif is_deep:
        try:
            from core.utils.deep_routing import should_use_deep_pipeline_full

            plan.use_deep_full = should_use_deep_pipeline_full(g, merged_kw)
            plan.pipeline = "deep_full" if plan.use_deep_full else "deep"
        except Exception:
            plan.pipeline = "deep"
    elif is_fast:
        plan.pipeline = preferred if preferred in ("fast", "fast_chat") else "fast"
    else:
        plan.pipeline = preferred

    scope = kw_patch.get("jkai_workspace_target")
    use_agent = bool(scope) and not kw_patch.get("jkai_fast_fix") and not kw_patch.get(
        "jkai_web_only_analysis"
    )
    if use_agent and container:
        try:
            from core.kernel.project_agent_loop import _env_enabled

            plan.use_cursor_agent = _env_enabled()
        except Exception:
            plan.use_cursor_agent = False

    _log(
        plan,
        "SYSTEM",
        f"AI OS: intent={plan.os_intent} pipeline={plan.pipeline} "
        f"mode={plan.execution_mode} tags={','.join(plan.capability_tags) or '-'}",
    )
    return plan
