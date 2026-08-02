"""
JKAI AI OS — Request Orchestrator

Một điểm vào duy nhất: phân loại ý định, làm giàu goal, chọn pipeline, gắn ràng buộc.
Mọi kênh (Mission Control, API, Telegram) nên dùng module này thay vì if/elif rời rạc.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.os.intent_taxonomy import (
    OSIntent,
    capability_tags,
    classify_os_intent,
    default_pipeline_for_intent,
)
from core.os.mission_state import MissionState
from core.utils.engine import engine

logger = logging.getLogger("jkai.os.orchestrator")

# Module-level constants — không recreate mỗi lần gọi
_BYPASS_WHITELIST: frozenset = frozenset(["xin chào", "chào", "hello", "hi", "ok", "yes", "2+2", "tạm biệt", "bye", "cảm ơn", "thanks"])


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
    mission_state: Optional[MissionState] = None

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
    engine._increment_stat("total")
    kw_patch: Dict[str, Any] = {}
    g = plan.goal

    # ── T-0: Zero-Latency Math Reflex (<1ms) ──
    try:
        import re
        g_low = g.lower().strip()
        if not any(kw in g_low for kw in ['tại sao', 'vì sao', 'giải mã', 'kiến trúc', 'code', 'hàm', 'script', 'lỗi', 'python', 'javascript', 'nội dung', 'bài tập']):
            if any(k in g_low for k in ['tính', 'bằng mấy', 'bằng bao nhiêu', 'kết quả', 'bao nhiêu']) or any(op in g for op in ['*', '+', '-', '/']):
                if not re.search(r'\d{1,2}\/\d{1,2}\/\d{2,4}', g):
                    matches = re.findall(r'(?:\d+[\s]*[\+\-\*\/]+[\s]*)+\d+', g)
                    if matches:
                        expr = max(matches, key=len).strip()
                        if re.match(r'^[0-9\s\+\-\*\/\.\(\)]+$', expr) and len(expr) >= 3:
                            val = eval(expr, {"__builtins__": None}, {})
                            if isinstance(val, (int, float)):
                                if isinstance(val, float) and val.is_integer():
                                    val = int(val)
                                val_str = f"{val:,.4f}".rstrip('0').rstrip('.') if isinstance(val, float) else f"{val:,}"
                                val_str = val_str.replace(',', '.')
                                _log(plan, "ZENITH", "⚡ [MATH-REFLEX]: Phản xạ tính toán dưới 1ms từ Ingress Root.")
                                plan.pipeline = "fast"
                                plan.early_response = {
                                    "answer": (
                                        f"**[MATH-REFLEX (<1ms)]**\n\n"
                                        f"📌 **Phép tính:** `{expr}`\n"
                                        f"🎯 **Kết quả:** **{val_str}** (hoặc `{val}`)\n\n"
                                        f"*Xử lý qua cổng phản xạ toán học ở chế độ FAST trên JKAI Zenith OS.*"
                                    ),
                                    "task_id": task_id,
                                    "cached": True,
                                    "pipeline": "fast",
                                    "mode": "fast"
                                }
                                return plan
    except Exception:
        pass

    # ── Fast Path Bypass: Chỉ bypass với whitelist + kiểm tra history ──
    g_clean = g.lower().strip()
    has_history = history and len(history) > 1
    is_simple = g_clean in _BYPASS_WHITELIST and not has_history
    if is_simple:
        plan.pipeline = "fast"
        plan.is_fast = True
        plan.is_deep = False
        plan.execution_mode = "fast"
        
        from core.os.execution_plan import ExecutionPlan, ExecutionPlanStep
        
        plan.mission_state = MissionState(
            goal=plan.goal,
            original_goal=goal,
            task_id=task_id,
            os_intent="social",
            pipeline="fast",
            execution_mode="fast",
            is_fast=True,
            is_deep=False,
            trace_id=kwargs.get("trace_id") or task_id
        )
        plan.mission_state.execution_plan = ExecutionPlan(
            selected_pipeline="fast",
            estimated_cost=1.0,
            steps=[ExecutionPlanStep(step_id="S1_FAST_REACTIVE", description="Phản xạ nhanh bypass", assigned_agent="general")]
        )
        engine._increment_stat("bypass")
        _log(plan, "ZENITH", "⚡ [FAST-PATH-BYPASS]: Câu hỏi đơn giản. Bỏ qua 14 tầng phân tích Router.")
        return plan

    # ── T0: Reflex memory ──
    reflex = None
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
                **{k: v for k, v in inspect_hit.items() if k not in ("answer",)},
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
                _log(plan, "ZENITH", "Yêu cầu thông tin năng lực — Trả về danh mục kỹ năng đăng ký (Bỏ qua LLM).")
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
    _internal_keywords = ["nội bộ", "trong máy", "trong hệ thống", "đã lưu", "đã có"]
    _is_internal_query = any(kw in g.lower() for kw in _internal_keywords)
    try:
        from core.utils.mission_context import (
            apply_parent_context,
            load_context_pack,
            format_context_block,
        )

        parent_mid = kwargs.get("parent_mission_id")
        mission_mid = kwargs.get("mission_id")
        if parent_mid:
            if _is_internal_query:
                _log(plan, "ZENITH", f"MISSION-CTX parent `{parent_mid}` — skipped (internal data query)")
            else:
                g = apply_parent_context(g, parent_mid)
                _log(plan, "ZENITH", f"MISSION-CTX parent `{parent_mid}`")
        elif mission_mid:
            if _is_internal_query:
                _log(plan, "ZENITH", f"MISSION-CTX resume `{mission_mid}` — skipped (internal data query)")
            else:
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

    has_deep_skill = False
    if kw_patch.get("resolved_skill_ids"):
        try:
            from core.utils.deep_routing import _DEEP_SKILLS
            if any(sid in _DEEP_SKILLS for sid in kw_patch["resolved_skill_ids"]):
                has_deep_skill = True
                is_deep = True
                is_fast = False
                _log(plan, "ZENITH", f"DEEP — kích hoạt do skill yêu cầu DEEP mode: {kw_patch['resolved_skill_ids']}")
        except Exception:
            pass

    has_workspace_target = bool(kw_patch.get("jkai_workspace_target"))

    # Chỉ chạy logic force deep hoặc tự động định tuyến khi chưa có chỉ định FAST/DEEP (chế độ AUTO)
    if not is_fast and not is_deep:
        if not (kw_patch.get("resolved_skill_ids") and not has_deep_skill and not has_workspace_target):
            if not g.startswith("/"):
                try:
                    from core.utils.deep_routing import (
                        goal_should_force_deep,
                        goal_should_force_deep_for_analysis,
                    )

                    if "<ZENITH_SKILL_ACTIVATED>" not in g and goal_should_force_deep_for_analysis(g):
                        is_deep, is_fast = True, False
                        _log(plan, "ZENITH", "DEEP — phân tích (producer_reviewer + CRITIC).")
                    elif goal_should_force_deep(g, history):
                        is_deep, is_fast = True, False
                        from core.utils.deep_routing import get_deep_routing_label
                        label = get_deep_routing_label(g, history)
                        _log(plan, "ZENITH", label)
                except Exception as e:
                    logger.warning("[OS] deep routing: %s", e)

            if mode_param == "auto" and not is_deep and not is_fast:
                # Skill đã resolve mà không yêu cầu DEEP → chạy fast
                if kw_patch.get("resolved_skill_ids"):
                    try:
                        from core.utils.deep_routing import _DEEP_SKILLS
                        if not any(sid in _DEEP_SKILLS for sid in kw_patch["resolved_skill_ids"]):
                            is_fast = True
                            _log(plan, "ZENITH", f"FAST — skill resolve, không yêu cầu DEEP.")
                    except Exception:
                        pass
                if not is_fast:
                    try:
                        from core.utils.intent_cortex import IntentCortex

                        cortex = await IntentCortex().analyze(g, history=history, images=kwargs.get("images"))
                        engine.cache_put(task_id, "intent_manifest", cortex)
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
        else:
            # Ép chạy Fast cho skill thông thường
            is_deep = False
            is_fast = True

    # ── T7 (mới): Khởi tạo MissionState & WorldState trước thưa Master ──
    try:
        trace_id = kwargs.get("trace_id") or task_id
        cached_manifest = engine.cache_get(task_id, "intent_manifest")

        # ⚠️ Đồng bộ quyết định is_deep/is_fast/use_deep_full vào plan trước khi tạo MissionState
        # Tránh ExecutionPlanner dùng default False/False và ra quyết định sai
        plan.is_deep = is_deep
        plan.is_fast = is_fast
        plan.use_deep_full = is_deep

        # Tạo MissionState ban đầu để nạp dữ liệu
        plan.mission_state = MissionState.from_os_plan(
            plan=plan,
            goal=plan.goal,
            original_goal=goal,
            task_id=task_id,
            kwargs={**kwargs, **kw_patch},
            trace_id=trace_id,
        )
        if cached_manifest:
            plan.mission_state.routing_manifest = cached_manifest

        # Capture World State
        from core.os.world_state import WorldStateMonitor
        workspace_path = kwargs.get("jkai_workspace_target") or "/workspace"
        world = await WorldStateMonitor.capture_state(workspace_path)
        plan.mission_state.world_state = world

        # [NEW]: Capture Memory State (reflex hit, conversation summary) thưa Master
        try:
            from core.os.memory_state import MemoryState
            reflex_hit = reflex is not None
            summary = ""
            # Lấy liên kết hội thoại gần nhất (chỉ khi cùng mission_id, không phải "+" mới)
            try:
                from context.mission_context import ctx_mgr
                prev_mission_id = ctx_mgr.get_linked_mission("default")
                if prev_mission_id and prev_mission_id != task_id:
                    prev_mc = ctx_mgr.get_or_create(prev_mission_id)
                    # Chỉ lấy summary nếu mission trước có context (không phải "+")
                    if prev_mc.conversation.get("last_subject"):
                        summary = prev_mc.conversation.get("last_answer", "")[:200]
            except Exception:
                pass
                
            plan.mission_state.memory_state = MemoryState(
                reflex_cache_hit=reflex_hit,
                conversation_summary=summary,
                learned_patterns=[]
            )
        except Exception as mem_err:
            logger.warning("[OS] capture memory state failed: %s", mem_err)

        # ── T8 (mới): Run ExecutionPlanner (Layer 4) để phán quyết pipeline động ──
        from core.os.execution_planner import ExecutionPlanner
        exec_plan = await ExecutionPlanner.generate_plan(plan.mission_state, world)
        plan.mission_state.execution_plan = exec_plan

        # Áp dụng phán quyết lập lịch động của ExecutionPlanner vào OSRequestPlan
        plan.pipeline = exec_plan.selected_pipeline
        plan.is_deep = exec_plan.selected_pipeline == "deep"
        plan.is_fast = exec_plan.selected_pipeline == "fast"
        plan.use_deep_full = plan.is_deep
        if plan.mission_state:
            plan.mission_state.use_deep_full = plan.use_deep_full
        plan.execution_mode = exec_plan.selected_pipeline
        
        # Override đặc biệt cho jkai_fast_fix
        if kw_patch.get("jkai_fast_fix"):
            plan.pipeline = "fast_fix"

        engine._increment_stat(exec_plan.selected_pipeline)

        # Xác định use_cursor_agent thưa Master
        scope = kw_patch.get("jkai_workspace_target")
        use_agent = bool(scope) and not kw_patch.get("jkai_fast_fix") and not kw_patch.get(
            "jkai_web_only_analysis"
        )
        if use_agent and container:
            try:
                from core.kernel.project_agent_loop import _env_enabled
                plan.use_cursor_agent = _env_enabled()
                plan.mission_state.use_cursor_agent = plan.use_cursor_agent
            except Exception:
                plan.use_cursor_agent = False
            
    except Exception as os_plan_err:
        logger.error("[OS] Execution Planner Layer 4 failed: %s", os_plan_err)
        # Fallback cơ bản nếu lỗi
        plan.pipeline = "fast"
        plan.is_fast = True
        plan.is_deep = False
        plan.execution_mode = "fast"

    _log(
        plan,
        "SYSTEM",
        f"AI OS: intent={plan.os_intent} pipeline={plan.pipeline} "
        f"mode={plan.execution_mode} tags={','.join(plan.capability_tags) or '-'}",
    )
    # Luu pipeline decision vao shared context (thread-safe)
    engine.cache_put(task_id, "pipeline", plan.pipeline)
    engine.cache_put(task_id, "execution_mode", plan.execution_mode)
    engine.cache_put(task_id, "os_intent", plan.os_intent)
    engine.cache_put(task_id, "is_fast", plan.is_fast)
    engine.cache_put(task_id, "is_deep", plan.is_deep)
    engine.cache_put(task_id, "capability_tags", plan.capability_tags)
    if plan.mission_state:
        engine.cache_put(task_id, "mission_state", plan.mission_state)
    engine.save_routing_stats()
    return plan
