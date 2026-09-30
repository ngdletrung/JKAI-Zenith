"""
JKAI AI OS — Parallel Enrichment Handler
T-1 đến T-4: Speculative Fork-Join thực thi song song các bước trích xuất & làm giàu goal:
- Skill Deck Inspect & Enrich
- Mission Context Resume
- Remote Repo Clone Detection
- Fast-Fix Path Directive
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.enrichment")


class ParallelEnrichmentHandler(BaseHandler):
    """Làm giàu ngữ cảnh và phát hiện mục tiêu song song."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g = plan.goal
        kw_patch = plan.kwargs_patch

        # ── 1. Skill Deck Inspect & Run Guide (Early-Exit Check) ──
        try:
            from core.utils.ingress_skill_gate import try_skill_deck_inspect, try_skill_deck_run_guide
            inspect_hit = try_skill_deck_inspect(g)
            if inspect_hit:
                log_telemetry(plan, "ZENITH", "Command Deck inspect.")
                try:
                    from core.utils.skill_deck_index import SkillDeckIndex
                    from core.utils.mission_context import save_context_pack
                    refs = SkillDeckIndex.get().parse_refs(g)
                    mid = ctx.kwargs.get("mission_id")
                    if mid and refs:
                        save_context_pack(mid, extra={"last_deck_ids": refs})
                except Exception:
                    pass
                plan.early_response = {
                    "answer": inspect_hit.get("answer", ""),
                    "task_id": ctx.task_id,
                    **{k: v for k, v in inspect_hit.items() if k not in ("answer",)},
                }
                return HandlerResult(early_exit=True)

            run_guide = try_skill_deck_run_guide(g, ctx.history, ctx.kwargs.get("mission_id"))
            if run_guide:
                log_telemetry(plan, "ZENITH", "Skill run guide (đầu vào / cách chạy).")
                plan.pipeline = "skill_run_guide"
                plan.os_intent = "skill_run"
                plan.early_response = {
                    "answer": run_guide.get("answer", ""),
                    "task_id": ctx.task_id,
                    "pipeline": "skill_run_guide",
                    "mode": "fast",
                    "source": run_guide.get("source"),
                }
                return HandlerResult(early_exit=True)

            from core.utils.jkai_capabilities import goal_is_capabilities_inquiry, build_capabilities_report
            if goal_is_capabilities_inquiry(g):
                log_telemetry(plan, "ZENITH", "Yêu cầu thông tin năng lực — Trả về danh mục kỹ năng đăng ký.")
                plan.pipeline = "capabilities"
                plan.os_intent = "capabilities"
                plan.early_response = {
                    "answer": build_capabilities_report(),
                    "task_id": ctx.task_id,
                    "pipeline": "capabilities",
                    "mode": "fast",
                }
                return HandlerResult(early_exit=True)
        except Exception as e:
            logger.debug("[SKILL-GATE-CHECK-ERR] %s", e)

        # ── 2. Speculative Fork-Join: Chạy song song SkillDeck Enrich + Repo Clone + FastFix ──
        async def _enrich_skill_deck(curr_g: str):
            try:
                from core.utils.ingress_skill_gate import enrich_goal_with_deck
                return enrich_goal_with_deck(curr_g)
            except Exception as err:
                return curr_g, [], str(err)

        async def _enrich_repo_clone(curr_g: str):
            try:
                from core.utils.repo_clone import enrich_goal_with_repo_clone
                return await enrich_goal_with_repo_clone(curr_g)
            except Exception as err:
                return curr_g, [], str(err)

        async def _enrich_fast_fix(curr_g: str):
            try:
                from core.utils.fast_fix_routing import goal_should_use_fast_fix_path, fast_fix_directive, detect_fast_fix_target
                if goal_should_use_fast_fix_path(curr_g):
                    fpath = detect_fast_fix_target(curr_g)
                    return True, fpath, fast_fix_directive(curr_g, fpath)
                return False, None, curr_g
            except Exception as err:
                return False, None, curr_g

        # Thực thi song song
        deck_task = _enrich_skill_deck(g)
        repo_task = _enrich_repo_clone(g)
        fix_task = _enrich_fast_fix(g)

        (deck_g, resolved_ids, deck_warn), (repo_g, clone_rels, clone_err), (is_fix, fix_path, fix_g) = await asyncio.gather(
            deck_task, repo_task, fix_task
        )

        if resolved_ids:
            kw_patch["resolved_skill_ids"] = resolved_ids
            log_telemetry(plan, "ZENITH", f"Command Deck → {resolved_ids}")
            g = deck_g
        if deck_warn:
            log_telemetry(plan, "WARN", deck_warn)

        if clone_rels:
            kw_patch["jkai_cloned_repos"] = clone_rels
            kw_patch["jkai_workspace_target"] = clone_rels[0]
            kw_patch["jkai_project_root"] = clone_rels[0]
            kw_patch["jkai_project_mode"] = "audit"
            log_telemetry(plan, "ZENITH", f"REPO-CLONE → `{clone_rels[0]}`")
            g = repo_g
        elif clone_err:
            log_telemetry(plan, "WARN", f"REPO-CLONE: {clone_err}")

        if is_fix:
            kw_patch["jkai_fast_fix"] = True
            kw_patch["jkai_fast_fix_file"] = fix_path
            log_telemetry(plan, "ZENITH", f"FAST-FIX → `{fix_path}`")
            g = fix_g

        # ── 3. Mission Context Enrichment ──
        _internal_keywords = ["nội bộ", "trong máy", "trong hệ thống", "đã lưu", "đã có"]
        _is_internal_query = any(kw in g.lower() for kw in _internal_keywords)
        try:
            from core.utils.mission_context import apply_parent_context, load_context_pack, format_context_block
            parent_mid = ctx.kwargs.get("parent_mission_id")
            mission_mid = ctx.kwargs.get("mission_id")
            if parent_mid:
                if not _is_internal_query:
                    g = apply_parent_context(g, parent_mid)
                    log_telemetry(plan, "ZENITH", f"MISSION-CTX parent `{parent_mid}`")
            elif mission_mid:
                if not _is_internal_query:
                    pack = load_context_pack(mission_mid)
                    block = format_context_block(pack)
                    if block:
                        g = f"{g.strip()}\n\n{block}"
                        log_telemetry(plan, "ZENITH", f"MISSION-CTX resume `{mission_mid}`")
        except Exception as e:
            logger.debug("[MISSION-CTX-ERR] %s", e)

        # ── 4. Cross-Mission Anaphora Context Bridge ──
        # Nếu goal mới chứa đại từ nối ("chi tiết hơn", "còn cái kia", "tiếp", …)
        # nhưng không có context block từ mission/parent → inject tóm tắt hội thoại trước.
        _ANAPHORA_TRIGGERS = frozenset([
            "chi tiết hơn", "giải thích", "giải thích thêm", "chi tiết",
            "tiếp tục", "tiếp theo", "còn", "cái đó", "vừa rồi",
            "ở trên", "như trên", "đó là", "nó là", "cái kia",
            "thêm nữa", "làm rõ", "cụ thể hơn", "expand", "elaborate",
        ])
        g_lower_check = g.lower().strip()
        has_anaphora = any(trigger in g_lower_check for trigger in _ANAPHORA_TRIGGERS)
        # Chỉ inject nếu goal ngắn (< 80 ký tự) — goal dài tự có context riêng
        is_short_followup = len(g.strip()) < 80
        already_has_ctx = "\n\n[Ngữ cảnh" in g or "[MISSION-CTX" in g or "[GROUND-TRUTH" in g

        if has_anaphora and is_short_followup and not already_has_ctx:
            try:
                # Tìm assistant message gần nhất từ history (đã được inject bởi task_manager)
                last_assistant = None
                last_user = None
                for msg in reversed(ctx.history or []):
                    role = msg.get("role", "")
                    content = msg.get("content", "").strip()
                    if not content:
                        continue
                    if last_assistant is None and role == "assistant":
                        last_assistant = content
                    elif last_user is None and role == "user" and content != g.strip():
                        last_user = content
                    if last_assistant and last_user:
                        break

                if last_assistant:
                    # Truncate tóm tắt nếu quá dài
                    prev_ans_preview = last_assistant[:400] + ("…" if len(last_assistant) > 400 else "")
                    prev_q_preview = (last_user or "")[:150] + ("…" if last_user and len(last_user) > 150 else "")
                    ctx_block = (
                        f"\n\n[Ngữ cảnh hội thoại — mission trước]\n"
                        f"Master hỏi: {prev_q_preview}\n"
                        f"JKAI đã trả lời: {prev_ans_preview}\n"
                        f"[/Ngữ cảnh — yêu cầu hiện tại là tiếp nối chủ đề trên]"
                    )
                    g = g.strip() + ctx_block
                    log_telemetry(plan, "ZENITH", "ANAPHORA-CTX: Đã inject ngữ cảnh mission trước vào goal.")
            except Exception as anaphora_err:
                logger.debug("[ANAPHORA-CTX-ERR] %s", anaphora_err)

        plan.goal = g
        plan.kwargs_patch = kw_patch
        return HandlerResult(early_exit=False)

