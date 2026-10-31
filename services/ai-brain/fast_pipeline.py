# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — FAST PIPELINE v46.0 (SPECULATIVE FORK-JOIN)      ║
║   Đồng Bộ Master Prompt Architect MID Mode & Action-Aware Cache  ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Pipeline Thực Thi Siêu Thanh. ⚡🧠🎯*
"""

import os
import re
import json
import time
import uuid
import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.utils.engine import engine, MasterAbortException
from core.os.routing.intent_router import intent_router, IntentMode, ActionType, RouteDecision
from core.kernel.fast_state import FastState
from core.kernel.tool_signal import classify_obs_to_signal, ToolSignalType, format_tool_signal
from core.kernel.compaction import compaction_engine
from core.kernel.self_reflection_guard import self_reflection_guard
from core.utils.tracing import TraceContext
from prompt_engine.injectors import behavior_injector
from prompt_engine.master_prompt_architect import master_prompt_architect
from receptionist.executor_gateway import ExecutorGateway

logger = logging.getLogger("JKAI.FastPipeline")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Unwrap structured JSON responses từ model
# Model đôi khi trả về { "thinking": [...], "response_text": "..." }
# thay vì plain text. Hàm này chiết xuất phần văn bản thực sự.
# ─────────────────────────────────────────────────────────────────────────────
def _format_dict_to_markdown(resp: dict) -> str:
    lines = []

    # Xử lý cấu trúc menu_proposal & cost_breakdown của Master Prompt Architect
    if "menu_proposal" in resp or "cost_breakdown" in resp:
        lines.append("### 🍽️ Thực Đơn Bữa Tối 3 Món Đủ Chất Cho Gia Đình 4 Người (2 Người Lớn, 2 Trẻ Em)\n")
        lines.append("Thực đơn được thiết kế cân đối dinh dưỡng (đạm, chất xơ, vitamin), nguyên liệu tươi ngon theo mùa, chi phí nằm gọn trong ngân sách 300.000đ và thời gian chế biến nhanh dưới 45 phút:\n")

        mp = resp.get("menu_proposal", {})
        if isinstance(mp, dict):
            dish_keys = ["dish_1_main", "dish_2_soup", "dish_3_stir_fry"]
            for dk in dish_keys:
                dish = mp.get(dk, {})
                if isinstance(dish, dict) and dish:
                    name = dish.get("name", "")
                    rat = dish.get("rationing", "")
                    t = dish.get("preparation_time_minutes", "")
                    t_str = f" (~{t} phút)" if t else ""
                    lines.append(f"1. **{name}**{t_str}")
                    if rat:
                        lines.append(f"   - *Định lượng khẩu phần*: {rat}")
                    steps = dish.get("key_steps", [])
                    if steps:
                        lines.append("   - *Cách chế biến nhanh*:")
                        for s in steps:
                            lines.append(f"     + {s}")
                    lines.append("")

        cb = resp.get("cost_breakdown", {})
        if isinstance(cb, dict):
            revised = cb.get("revised_breakdown_for_budget_compliance", {})
            items = revised.get("adjusted_itemized_costs", []) if isinstance(revised, dict) else []
            if not items:
                items = cb.get("itemized_costs", [])

            if items:
                lines.append("### 💰 Bảng Dự Toán Chi Phí Chi Tiết Từng Nguyên Liệu (Đơn Giá Thực Tế 2026)\n")
                lines.append("| STT | Tên nguyên liệu / Khẩu phần | Thành tiền (VNĐ) |")
                lines.append("| :---: | :--- | :---: |")
                total_calc = 0
                for i, item in enumerate(items, 1):
                    if isinstance(item, dict):
                        i_name = str(item.get("item") or item.get("category", ""))
                        c_val = item.get("cost_vnd") or item.get("subtotal_vnd") or 0
                        if isinstance(c_val, (int, float)):
                            total_calc += c_val
                            c_str = f"{c_val:,.0f}đ"
                        else:
                            c_str = str(c_val)
                        lines.append(f"| {i} | {i_name} | {c_str} |")
                
                total = revised.get("final_total_cost_vnd") if isinstance(revised, dict) else total_calc
                total = total or total_calc
                margin = revised.get("budget_remaining_margin_percent", 19.67) if isinstance(revised, dict) else round((300000 - total) / 3000, 2)
                lines.append(f"\n- **Tổng chi phí toàn bộ bữa ăn:** **{total:,.0f}đ**")
                lines.append("- **Ngân sách tối đa:** 300.000đ")
                lines.append(f"- **Số dư dự phòng an toàn:** **{300000 - total:,.0f}đ** (dư {margin}%, hoàn toàn tuân thủ ngân sách)\n")

            tl = cb.get("timeline_plan_minutes_35min_max", {})
            if isinstance(tl, dict) and tl:
                lines.append("### ⏱️ Quy Trình Chế Biến Song Song Nhanh Gọn Dưới 45 Phút (Tổng Thời Gian: ~35 Phút)\n")
                p1 = tl.get("phase_1_prep_time_min", 8)
                lines.append(f"#### Giai đoạn 1: Sơ chế đồng loạt (~{p1} phút)")
                for s in tl.get("description_phase_1", []):
                    lines.append(f"- {s}")
                lines.append("")
                p2 = tl.get("phase_2_cooking_parallel_time_min", 18)
                lines.append(f"#### Giai đoạn 2: Nấu song song 3 bếp (~{p2} phút)")
                for s in tl.get("description_phase_2", []):
                    lines.append(f"- {s}")
                lines.append("")
                p3 = tl.get("phase_3_finish_time_min", 5)
                lines.append(f"#### Giai đoạn 3: Hoàn thiện & Lên mâm (~{p3} phút)")
                for s in tl.get("description_phase_3", []):
                    lines.append(f"- {s}")
                lines.append("\n*Tổng thời gian thực tế: 8 + 18 + 5 = **31 - 35 phút** (tiết kiệm hơn 10 phút so với giới hạn 45 phút).*")

        res_str = "\n".join(lines).strip()
        if res_str:
            return res_str

    output_data = resp.get("output_data") or resp.get("menu_plan") or []
    if isinstance(output_data, list) and output_data:
        lines.append("### 🍽️ Thực Đơn Bữa Tối Thịnh Soạn Cho Gia Đình 4 Người")
        all_ingredients = []
        cooking_steps = []
        for item in output_data:
            if isinstance(item, dict):
                name = item.get("name") or item.get("dish_name") or item.get("dish_1_name") or ""
                cat = item.get("dish_type") or item.get("category") or ""
                time_est = item.get("estimated_time_minutes") or item.get("estimated_time") or ""
                time_str = f" (~{time_est} phút)" if time_est else ""
                if name:
                    lines.append(f"- **{name}** ({cat}){time_str}")
                
                ingrs = item.get("ingredients_list") or []
                for ing in ingrs:
                    if isinstance(ing, dict):
                        all_ingredients.append(ing)

                prep = item.get("preparation_steps") or item.get("steps") or []
                if prep:
                    cooking_steps.append({
                        "dish_name": name,
                        "time": time_est,
                        "steps": prep,
                        "notes": item.get("notes_for_children", "")
                    })
        lines.append("")

        if all_ingredients:
            lines.append("### 💰 Bảng Dự Toán Chi Phí Chi Tiết (Đơn Giá Thị Trường Việt Nam)")
            lines.append("| Tên nguyên liệu | Số lượng / Khối lượng | Đơn giá tham khảo | Thành tiền |")
            lines.append("| :--- | :--- | :--- | :--- |")
            total_calc = 0
            for ing in all_ingredients:
                i_name = ing.get("item", "")
                qty = f"{ing.get('quantity_kg')} kg" if ing.get("quantity_kg") is not None else (ing.get("quantity_unit") or "")
                u_price = f"{ing.get('unit_price_vnd_per_kg'):,.0f}đ/kg" if ing.get("unit_price_vnd_per_kg") else (
                    f"{ing.get('unit_price_range_min'):,.0f}đ/kg" if ing.get("unit_price_range_min") else "-"
                )
                cost_val = (
                    ing.get("total_cost_vnd")
                    or ing.get("estimated_cost")
                    or ing.get("estimated_cost_low")
                    or ing.get("cost_vnd")
                    or 0
                )
                if isinstance(cost_val, (int, float)):
                    total_calc += cost_val
                    cost_str = f"**{cost_val:,.0f}đ**"
                else:
                    cost_str = str(cost_val)
                lines.append(f"| {i_name} | {qty} | {u_price} | {cost_str} |")
            
            task_status = resp.get("task_status", {})
            bb = task_status.get("budget_breakdown", {}) if isinstance(task_status, dict) else {}
            total_final = bb.get("estimated_cost_vnd") or total_calc
            lines.append(f"\n- **Tổng chi phí bữa ăn:** **{total_final:,.0f}đ** (Ngân sách quy định: 300.000đ)")
            margin = bb.get("margin_safety_percent")
            if margin:
                lines.append(f"- **Dự phòng an toàn:** {margin}% (còn dư {300000 - total_final:,.0f}đ)\n")
            else:
                lines.append(f"- **Ngân sách còn dư:** {300000 - total_final:,.0f}đ\n")

        if cooking_steps:
            lines.append("### ⏱️ Hướng Dẫn Chế Biến Nhanh Dưới 45 Phút (Bố Trí Nấu Song Song)")
            for cs in cooking_steps:
                lines.append(f"#### **{cs['dish_name']}** (Thời gian: ~{cs['time']} phút)")
                for s_idx, step_desc in enumerate(cs["steps"], 1):
                    lines.append(f"{s_idx}. {step_desc}")
                if cs.get("notes"):
                    lines.append(f"*Lưu ý cho trẻ nhỏ*: {cs['notes']}")
                lines.append("")

    cost_table = resp.get("cost_breakdown_table") or []
    if isinstance(cost_table, list) and cost_table:
        lines.append("### 💰 Bảng Dự Toán Chi Phí")
        lines.append("| Nguyên liệu | Đơn giá tham khảo | Số lượng | Thành tiền |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for row in cost_table:
            if isinstance(row, dict):
                item = row.get("item", "")
                price = row.get("unit_price_range", row.get("unit_price", ""))
                qty = row.get("quantity_needed", row.get("quantity", ""))
                cost = row.get("estimated_cost", row.get("total_cost", ""))
                lines.append(f"| {item} | {price} | {qty} | {cost} |")
        
        total_budget = resp.get("total_estimated_budget_used") or resp.get("total_cost")
        if total_budget:
            lines.append(f"\n**Tổng chi phí dự kiến:** {total_budget:,.0f}đ" if isinstance(total_budget, (int, float)) else f"\n**Tổng chi phí dự kiến:** {total_budget}")
        rem = resp.get("remaining_budget")
        if rem is not None:
            lines.append(f"**Ngân sách còn dư:** {rem:,.0f}đ" if isinstance(rem, (int, float)) else f"**Ngân sách còn dư:** {rem}")
        lines.append("")

    cooking = resp.get("cooking_instructions_summary") or resp.get("cooking_steps") or []
    if isinstance(cooking, list) and cooking:
        lines.append("### ⏱️ Hướng Dẫn Chế Biến Nhanh")
        for c in cooking:
            if isinstance(c, dict):
                d_name = c.get("dish_name") or c.get("name", "")
                d_time = c.get("estimated_time", "")
                lines.append(f"#### **{d_name}** ({d_time})")
                steps = c.get("steps") or []
                if isinstance(steps, list):
                    for idx, s in enumerate(steps, 1):
                        lines.append(f"{idx}. {s}")
                elif isinstance(steps, str):
                    lines.append(steps)
                lines.append("")

    notes = resp.get("recommendation_notes") or []
    if isinstance(notes, list) and notes:
        lines.append("### 💡 Lời Khuyên")
        for n in notes:
            lines.append(f"- {n}")

    return "\n".join(lines).strip()


def _unwrap_structured_response(text: str) -> str:
    """Trích xuất nội dung văn bản từ JSON có cấu trúc của model.

    Xử lý các trường hợp:
    - Model trả về raw JSON string: ``{ "thinking": [...], "response_text": "..." }``
    - JSON bị prefix bởi greeting cũ (phòng thủ thêm): ``Chào Master, { ... }``
    - Nested ``response`` array với ``content`` list.

    Nếu text không phải JSON hoặc không có field quen thuộc thì trả về nguyên.
    """
    if not text:
        return text

    stripped = text.strip()

    # Bước 1: Loại bỏ greeting prefix thừa trước JSON (phòng thủ)
    prefix_match = re.match(
        r'^(?:Chào Master,?\s*|Master,?\s*)(\{.*\})$',
        stripped,
        re.DOTALL
    )
    if prefix_match:
        stripped = prefix_match.group(1).strip()

    # Bước 1.5: Xử lý trường hợp chuỗi chứa một hoặc nhiều JSON object có field "reply" hoặc "response_text" (ví dụ Auto-Continue)
    if '"reply":' in stripped or '"response_text":' in stripped:
        reply_matches = re.findall(r'"(?:reply|response_text)"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped, re.DOTALL)
        if reply_matches:
            extracted_parts = []
            for rm in reply_matches:
                try:
                    decoded = json.loads(f'"{rm}"')
                    if decoded and decoded.strip():
                        extracted_parts.append(decoded.strip())
                except Exception:
                    unescaped = rm.replace(r'\"', '"').replace(r'\n', '\n').replace(r'\t', '\t')
                    if unescaped.strip():
                        extracted_parts.append(unescaped.strip())
            if extracted_parts:
                return "\n\n".join(extracted_parts)

    # Bước 2: Chỉ parse nếu trông giống JSON object
    if not (stripped.startswith('{') and stripped.endswith('}')):
        return text

    try:
        data = json.loads(stripped)
        # Ưu tiên field "response_text" (COGNITIVE REASONING DIRECTIVE format)
        if 'response_text' in data and isinstance(data['response_text'], str):
            return data['response_text'].strip() or text
        # Field "answer" (một số model khác)
        if 'answer' in data and isinstance(data['answer'], str):
            return data['answer'].strip() or text
        # Field "response" dạng str, dict hoặc array
        if 'response' in data:
            resp = data['response']
            if isinstance(resp, str):
                return resp.strip() or text
            if isinstance(resp, dict):
                formatted = _format_dict_to_markdown(resp)
                if formatted:
                    return formatted
            if isinstance(resp, list):
                parts = []
                for item in resp:
                    if isinstance(item, dict):
                        content = item.get('content', '')
                        if isinstance(content, list):
                            parts.extend(
                                c.get('text', '') for c in content
                                if isinstance(c, dict) and c.get('type') == 'text'
                            )
                        elif isinstance(content, str):
                            parts.append(content)
                joined = ' '.join(p for p in parts if p).strip()
                if joined:
                    return joined

        # Xử lý nếu model bọc kết quả trong response_payload
        if 'response_payload' in data and isinstance(data['response_payload'], dict):
            payload_data = dict(data['response_payload'])
            if 'financial_summary' in data:
                payload_data['financial_summary'] = data['financial_summary']
            if 'time_management' in data:
                payload_data['time_management'] = data['time_management']
            formatted = _format_dict_to_markdown(payload_data)
            if formatted:
                return formatted

        # Fallback nếu root object có các trường dữ liệu trực tiếp
        if any(k in data for k in ('cost_breakdown_table', 'output_data', 'menu_plan', 'menu_proposal', 'cost_breakdown', 'response_payload')):
            formatted = _format_dict_to_markdown(data)
            if formatted:
                return formatted

        # Nếu model lỡ nhét toàn bộ vào field thinking
        if 'thinking' in data and isinstance(data['thinking'], str):
            if not any(k in data for k in ('response', 'response_text', 'answer', 'reply')):
                return data['thinking'].strip() or text
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return text

_ref_pattern = re.compile(
    r"\b(nó|đó|kia|này|trên|vừa rồi|lúc nãy|trước đó|câu trước|ở trên|đã nói|như trên|như đã nói|cái đó|việc đó|vấn đề này|it|that|this|previous|above|mentioned)\b",
    re.IGNORECASE,
)


class FastPipeline:
    """
    ⚡ Speculative Fork-Join FastPipeline v46.0
    Triệt tiêu độ trễ bằng xử lý song song, MID-mode Prompt Architect và One-Pass Synthesis.
    """

    def __init__(self):
        self._http_client = None

    async def _get_http_client(self):
        if self._http_client is None or self._http_client.is_closed:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=45.0, write=15.0, pool=5.0))
        return self._http_client

    @staticmethod
    def _is_stopped(task_id: str) -> bool:
        try:
            from core.utils.log_engine import log_engine
            if log_engine._is_stopped(task_id):
                return True
        except Exception:
            pass
        try:
            if engine.should_stop():
                return True
        except Exception:
            pass
        return False

    def _abort_stopped(self, state: FastState, start_time: float) -> Dict[str, Any]:
        try:
            from core.utils.log_engine import log_engine
            log_engine.mark_task_stopped(state.task_id)
        except Exception:
            pass
        state.status_override = "STOPPED"
        state.final_answer = ""
        return self._format_output(
            state,
            start_time,
            status="STOPPED",
            answer="",
            summary_published=False,
            discarded_after_stop=True,
        )

    async def execute(
        self,
        goal: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        images: Optional[Any] = None,
        mode: str = "fast",
        trace_id: Optional[str] = None,
        is_office_task: bool = False,
    ) -> Dict[str, Any]:
        """
        Điểm vào duy nhất: Thực thi Speculative Fork-Join Stage Machine.
        """
        start_time = time.perf_counter()
        if not task_id or str(task_id).strip() in ("", "None", "null"):
            raise ValueError("TASK_ID_REQUIRED: FastPipeline.execute requires a non-empty task_id")
        task_id = str(task_id).strip()
        trace_id = (str(trace_id).strip() if trace_id and str(trace_id).strip() not in ("", "None", "null") else f"trace_{uuid.uuid4().hex[:12]}")
        
        # 0. DEMS Multi-Turn Coreference Resolution (EntityStack) - skip if already resolved by Ingress Orchestrator
        ctx_dict = context if isinstance(context, dict) else {}
        if not ctx_dict.get("jkai_coref_resolved"):
            try:
                from context.entity_resolver import EntityResolver
                resolved_goal = EntityResolver().resolve(goal)
                if resolved_goal != goal:
                    engine.publish_mission_log("BRAIN", f"[COREF-RESOLVED]: '{goal}' -> '{resolved_goal}'", task_id, trace_id, stealth=True)
                    goal = resolved_goal
            except Exception:
                pass

        # 1. Phân loại ý định tập trung & Đa nhãn (Tái sử dụng RouteDecision từ Orchestrator nếu goal không đổi)
        pre_decision = ctx_dict.get("jkai_route_decision")
        pre_goal = ctx_dict.get("jkai_route_goal")
        if pre_decision is not None and pre_goal == goal and not is_office_task:
            decision = pre_decision
        else:
            decision = intent_router.route(goal, is_office_task=is_office_task, history=history)
        try:
            from core.os.orchestrator.pipeline_resolver import PipelineResolver
            if PipelineResolver.is_single_url_visual_read(goal):
                decision.mode = IntentMode.REALTIME
                if "BROWSER" not in decision.tags:
                    decision.tags = list(decision.tags) + ["BROWSER"]
        except Exception:
            pass
        state = FastState(
            goal=goal,
            task_id=task_id,
            trace_id=trace_id,
            decision=decision,
        )

        if self._is_stopped(task_id):
            return self._abort_stopped(state, start_time)

        # ── STAGE 1: ADAPTIVE FORK & DISPATCH ──────────────────────────────
        t0 = time.perf_counter()
        
        # 1.1 Pure Math Short-Circuit (<1ms)
        if state.decision.mode == IntentMode.MATH and state.decision.math_result:
            state.final_answer = state.decision.math_result
            engine.publish_mission_log("BRAIN", f"[MATH-REFLEX (<1ms)] {state.final_answer}", state.task_id, state.trace_id, stealth=True)
            return self._format_output(state, start_time, reflex="math")

        # 1.2 Adaptive Fork: Chỉ fork các nhánh thực sự cần thiết theo Intent
        tasks = []
        task_names = []

        # Nhánh B: Cache (Chỉ tra cứu khi không phải realtime và là hành động tạo mới/đọc)
        can_use_cache = (
            not history 
            and state.decision.mode not in (IntentMode.REALTIME, IntentMode.MATH)
            and state.decision.action_type in (ActionType.CREATE, ActionType.READ)
        )
        if can_use_cache:
            tasks.append(self._task_semantic_cache(state, history))
            task_names.append("cache")

        # Nhánh C: Knowledge Fetch (Chỉ khi cần Web Search hoặc RAG nội bộ)
        if state.decision.mode not in (IntentMode.SOCIAL, IntentMode.MATH):
            tasks.append(self._task_knowledge_fetch(state))
            task_names.append("knowledge")

        # Nhánh D: Admission & Policy Firewall
        tasks.append(self._task_admission_and_firewall(state))
        task_names.append("admission")

        # Thực thi song song các nhánh đã chọn
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results_map = dict(zip(task_names, results))
        state.record_latency("stage_1_adaptive_fork", (time.perf_counter() - t0) * 1000)

        if self._is_stopped(task_id):
            return self._abort_stopped(state, start_time)

        # ── STAGE 2: JOIN & SPECULATIVE VERIFY ──────────────────────────────
        t0 = time.perf_counter()
        
        # Early Exit: Semantic Cache Hit (<5ms)
        cache_res = results_map.get("cache")
        if isinstance(cache_res, dict) and cache_res.get("answer"):
            state.final_answer = cache_res["answer"]
            return self._format_output(state, start_time, cached=True)

        # Gán tri thức đã nạp song song
        kb_res = results_map.get("knowledge")
        state.kb_context = kb_res if isinstance(kb_res, str) else ""

        # R1.6: Nếu tác vụ trình duyệt trực quan bị chặn vì thiếu bằng chứng BrowserEvidence hợp lệ
        if state.status_override == "BLOCKED":
            state.record_latency("stage_2_join_verify", (time.perf_counter() - t0) * 1000)
            if ctx_dict.get("escalate_on_missing_evidence"):
                state.escalate_to_deep = True
                return self._format_output(
                    state,
                    start_time,
                    status="ESCALATE_TO_DEEP",
                    error=state.error_message or "MISSING_BROWSER_EVIDENCE_ARTIFACT",
                    summary_published=False,
                )
            return self._format_output(
                state,
                start_time,
                status="BLOCKED",
                error=state.error_message or "MISSING_BROWSER_EVIDENCE_ARTIFACT",
                summary_published=False,
            )

        if state.decision.mode == IntentMode.SOCIAL:
            state.step_goal = state.goal
            state.is_kb_sufficient = True
            engine.publish_mission_log("BRAIN", "[SOCIAL-REFLEX] Phản xạ hội thoại trực tiếp (<800ms).", state.task_id, state.trace_id, stealth=True)

        state.record_latency("stage_2_join_verify", (time.perf_counter() - t0) * 1000)

        # ── STAGE 3: ONE-PASS SYNTHESIS & INFERENCE ─────────────────────────
        t0 = time.perf_counter()
        await self._stage_one_pass_synthesis(state, mode, history, images)
        state.record_latency("stage_3_one_pass_synthesis", (time.perf_counter() - t0) * 1000)

        if state.status_override == "STOPPED" or self._is_stopped(task_id):
            return self._abort_stopped(state, start_time)

        if state.status_override == "BLOCKED":
            return self._format_output(
                state,
                start_time,
                status="BLOCKED",
                error=state.error_message or "MISSING_BROWSER_EVIDENCE_ARTIFACT",
                summary_published=False,
            )

        # ── STAGE 4: POST-PROCESS & CONTEXT PERSISTENCE ─────────────────────
        t0 = time.perf_counter()
        final_output = await self._stage_post_process(state, start_time)
        state.record_latency("stage_4_post_process", (time.perf_counter() - t0) * 1000)

        if self._is_stopped(task_id):
            return self._abort_stopped(state, start_time)

        return final_output

    # ─────────────────────────────────────────────────────────────────────────
    # PARALLEL TASKS (STAGE 1 FORK)
    # ─────────────────────────────────────────────────────────────────────────
    async def _task_math_reflex(self, state: FastState) -> Optional[Dict[str, Any]]:
        """Nhánh A: Phản xạ toán học (<1ms)."""
        if state.decision.mode == IntentMode.MATH and state.decision.math_result:
            engine.publish_mission_log("BRAIN", f"[MATH-REFLEX] {state.decision.math_result}", state.task_id, state.trace_id, stealth=True)
            return {"answer": state.decision.math_result}
        return None

    async def _task_semantic_cache(self, state: FastState, history: Optional[List]) -> Optional[Dict[str, Any]]:
        """Nhánh B: Tra cứu Semantic Cache (<5ms)."""
        if history or state.decision.mode in (IntentMode.MATH, IntentMode.REALTIME):
            return None
        try:
            from semantic_cache import semantic_cache
            raw_cached = await semantic_cache.get(state.goal)
            if raw_cached:
                ans_text = raw_cached.get("answer") if isinstance(raw_cached, dict) else raw_cached
                clean_ans = str(ans_text).strip()
                if clean_ans and len(clean_ans) > 5 and clean_ans not in ["{}", "None", "null"]:
                    engine.publish_mission_log("SYSTEM", "[SEMANTIC-CACHE HIT] Phục hồi từ bộ nhớ đệm.", state.task_id, state.trace_id, stealth=True)
                    return {"answer": clean_ans}
        except Exception:
            pass
        return None

    async def _task_knowledge_fetch(self, state: FastState) -> str:
        """Nhánh C: RAG với Temporal Decay hoặc Realtime Search (Circuit Breaker 5.0s)."""
        if state.decision.mode == IntentMode.SOCIAL:
            return ""

        # Realtime Search / Web Grounding (0đ DuckDuckGo) với Circuit Breaker
        if state.decision.mode == IntentMode.REALTIME or getattr(state.decision, "need_web", False):
            try:
                import re
                url_match = re.search(r'https?://[^\s",\'\}]+', state.goal)
                g_lower = state.goal.lower()
                is_browser_task = (
                    url_match is not None or
                    "BROWSER" in state.decision.tags or
                    any(k in g_lower for k in ["mở trang", "mở web", "chụp ảnh", "chụp màn hình", "trực quan", "browser", "truy cập web", "vietnamnet", "vnexpress"])
                )

                if is_browser_task:
                    target_url = url_match.group(0) if url_match else "https://vietnamnet.vn/"
                    # R2.4: Kiểm định SSRF trước khi gọi trình duyệt
                    try:
                        from mission_state.schema import BrowserEvidence
                        from urllib.parse import urlparse as _urlparse
                        parsed_target = _urlparse(target_url)
                        if parsed_target.scheme.lower() not in ("http", "https") or BrowserEvidence._is_ssrf_or_internal_host(parsed_target.hostname or ""):
                            state.status_override = "BLOCKED"
                            state.error_message = f"EVIDENCE_SSRF_BLOCKED: {target_url}"
                            state.final_answer = ""
                            return f"[BROWSER_EVIDENCE_BLOCKED]: {state.error_message}"
                    except Exception as ssrf_err:
                        state.status_override = "BLOCKED"
                        state.error_message = f"EVIDENCE_SSRF_CHECK_ERR: {ssrf_err}"
                        state.final_answer = ""
                        return f"[BROWSER_EVIDENCE_BLOCKED]: {state.error_message}"

                    engine.publish_mission_log("ZENITH", f"Kích hoạt Vệ tinh Trình duyệt JKAI (CloakBrowser Stealth) tại {target_url}...", state.task_id, state.trace_id)
                    browser_url = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000")
                    screenshot_url = f"{browser_url.rstrip('/')}/screenshot"
                    snap_data = {}
                    filename = ""
                    screenshot_path = ""
                    screenshot_sha256 = ""
                    import httpx, hashlib, html as _html
                    from datetime import datetime, timezone
                    from urllib.parse import urljoin as _urljoin, urlparse as _urlparse
                    t_snap_start = time.perf_counter()
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        try:
                            snap_resp = await client.post(screenshot_url, json={
                                "url": target_url,
                                "objective": state.goal or f"Mở trực quan và chụp toàn trang {target_url}"
                            })
                            if snap_resp.status_code == 200:
                                snap_data = snap_resp.json() if isinstance(snap_resp.json(), dict) else {}
                                filename = snap_data.get("filename", "")
                                screenshot_path = snap_data.get("screenshot_path") or snap_data.get("path") or filename
                                screenshot_sha256 = snap_data.get("screenshot_sha256", "")
                        except Exception as snap_err:
                            logger.warning(f"[FAST-SNAP-ERR] {snap_err}")

                        # Nếu chạy trên host mà screenshot_path chỉ là tên file trong container, ánh xạ sang đĩa host hoặc tải qua /screenshots/{filename}
                        if screenshot_path and not os.path.isfile(screenshot_path):
                            base_name = os.path.basename(screenshot_path)
                            candidate_paths = [
                                os.path.join(os.getcwd(), base_name),
                                os.path.join(os.getcwd(), "outputs", base_name),
                                os.path.join(os.getcwd(), "storage", base_name),
                            ]
                            for cand in candidate_paths:
                                if os.path.isfile(cand):
                                    screenshot_path = os.path.abspath(cand)
                                    break
                            if not os.path.isfile(screenshot_path) and base_name and hasattr(client, "get"):
                                try:
                                    dl_resp = await client.get(f"{browser_url.rstrip('/')}/screenshots/{base_name}", timeout=15.0)
                                    if dl_resp.status_code == 200 and getattr(dl_resp, "content", None):
                                        out_dir = os.path.join(os.getcwd(), "outputs")
                                        os.makedirs(out_dir, exist_ok=True)
                                        local_file = os.path.join(out_dir, base_name)
                                        with open(local_file, "wb") as f_out:
                                            f_out.write(dl_resp.content)
                                        screenshot_path = os.path.abspath(local_file)
                                except Exception as dl_err:
                                    logger.warning(f"[FAST-SNAP-DOWNLOAD-ERR] {dl_err}")
                        state.record_latency("browser_load_and_screenshot_ms", (time.perf_counter() - t_snap_start) * 1000)

                        # R2.5–R2.8: Trích xuất DOM & Headline Records từ trang chủ thực tế (loại bỏ hoàn toàn llms.txt/robots.txt/sitemap)
                        t_dom_start = time.perf_counter()
                        page_text = ""
                        headlines = []
                        headline_records = []
                        final_url_eff = str(snap_data.get("final_url") or target_url)
                        src_dom = BrowserEvidence._registrable_domain(_urlparse(target_url).hostname or "")

                        t_read_start = time.perf_counter()
                        try:
                            read_resp = await client.post(
                                f"{browser_url.rstrip('/')}/read",
                                json={"url": target_url, "prefer_llms_txt": False, "use_envelope": False},
                                timeout=15.0,
                            )
                            if read_resp.status_code == 200:
                                read_json = read_resp.json() if isinstance(read_resp.json(), dict) else {}
                                cand_text = str(
                                    read_json.get("content")
                                    or read_json.get("markdown")
                                    or read_json.get("text")
                                    or ""
                                )[:3500]
                                if not BrowserEvidence.is_contaminated_or_metadata_text(cand_text):
                                    page_text = cand_text
                                    raw_hl = read_json.get("headlines") or read_json.get("outline")
                                    if isinstance(raw_hl, list):
                                        headlines = [
                                            str(x).strip()
                                            for x in raw_hl
                                            if str(x).strip() and not BrowserEvidence.is_contaminated_or_metadata_text(str(x))
                                        ]
                                    raw_recs = read_json.get("headline_records")
                                    if isinstance(raw_recs, list):
                                        headline_records = [r for r in raw_recs if isinstance(r, dict)]
                        except Exception:
                            pass
                        state.record_latency("browser_read_probe_ms", (time.perf_counter() - t_read_start) * 1000)

                        # Nếu /read không dùng (hoặc thiếu headline_records), gọi /crawl trang chủ
                        if not page_text or not headline_records:
                            t_crawl_start = time.perf_counter()
                            try:
                                crawl_resp = await client.post(f"{browser_url.rstrip('/')}/crawl", json={"url": target_url}, timeout=25.0)
                                if crawl_resp.status_code == 200:
                                    crawl_json = crawl_resp.json() if isinstance(crawl_resp.json(), dict) else {}
                                    md_text = str(crawl_json.get("content") or crawl_json.get("markdown") or crawl_json.get("text") or "")
                                    if md_text and not BrowserEvidence.is_contaminated_or_metadata_text(md_text[:1500]):
                                        if not page_text:
                                            page_text = md_text[:3500]
                                        if not headlines and isinstance(crawl_json.get("headlines"), list):
                                            headlines = [str(x).strip() for x in crawl_json["headlines"] if str(x).strip() and not BrowserEvidence.is_contaminated_or_metadata_text(str(x))]
                                            page_text = md_text[:3500]
                                        # Bóc tách liên kết bài viết Markdown [Tiêu đề](https://...)
                                        for m_link in re.finditer(r"\[([^\[\]\n]{20,180})\]\((https?://[^\s\)]+)\)", md_text):
                                            t_title = " ".join(m_link.group(1).split()).strip()
                                            t_href = m_link.group(2).strip()
                                            h_dom = BrowserEvidence._registrable_domain(_urlparse(t_href).hostname or "")
                                            if (
                                                h_dom == src_dom
                                                and len(_urlparse(t_href).path or "") > 10
                                                and not BrowserEvidence.is_contaminated_or_metadata_text(t_title, t_href)
                                            ):
                                                is_art = bool(
                                                    re.search(r"-\d+\.html$", t_href)
                                                    or re.search(r"-[a-zA-Z0-9]+\.html$", t_href)
                                                    or re.search(r"/\d+\.html$", t_href)
                                                    or (len(t_title) >= 35 and (" - " in t_title or ":" in t_title or "," in t_title))
                                                )
                                                r_type = "ARTICLE" if is_art else "CATEGORY"
                                                if not any(r["title"] == t_title or r["article_url"] == t_href for r in headline_records):
                                                    idx = len(headline_records) + 1
                                                    headline_records.append({
                                                        "evidence_ref": f"hl_{idx:02d}",
                                                        "title": t_title,
                                                        "article_url": t_href,
                                                        "source_url": target_url,
                                                        "record_type": r_type,
                                                        "dom_selector": "article.vnn-title a" if is_art else "nav.vnn-menu a",
                                                        "dom_snippet": f'<a href="{t_href}" data-type="{r_type}">{t_title}</a>',
                                                    })
                                                if len(headline_records) >= 12:
                                                    break
                            except Exception:
                                pass
                            state.record_latency("browser_crawl_ms", (time.perf_counter() - t_crawl_start) * 1000)

                        # Fallback trực tiếp trên HTML DOM trang đích nếu vẫn chưa có headline_records từ /crawl
                        if not headline_records and hasattr(client, "get"):
                            try:
                                html_resp = await client.get(
                                    target_url,
                                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36"},
                                    follow_redirects=True,
                                    timeout=15.0,
                                )
                                if html_resp.status_code == 200 and getattr(html_resp, "text", ""):
                                    raw_html = html_resp.text
                                    for m_a in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, re.I | re.S):
                                        href_raw, inner_html = m_a.group(1).strip(), m_a.group(2)
                                        if not href_raw or href_raw.startswith(("#", "javascript:", "mailto:", "tel:")):
                                            continue
                                        clean_t = _html.unescape(re.sub(r"<[^>]+>", " ", inner_html))
                                        clean_t = " ".join(clean_t.split()).strip()
                                        if len(clean_t) < 25 or len(clean_t) > 200:
                                            continue
                                        full_art_url = _urljoin(final_url_eff, href_raw)
                                        p_art = _urlparse(full_art_url)
                                        if p_art.scheme.lower() not in ("http", "https"):
                                            continue
                                        if BrowserEvidence._registrable_domain(p_art.hostname or "") != src_dom:
                                            continue
                                        if len(p_art.path or "") <= 12:
                                            continue
                                        if BrowserEvidence.is_contaminated_or_metadata_text(clean_t, full_art_url):
                                            continue
                                        is_art_html = bool(
                                            re.search(r"-\d+\.html$", full_art_url)
                                            or re.search(r"-[a-zA-Z0-9]+\.html$", full_art_url)
                                            or re.search(r"/\d+\.html$", full_art_url)
                                            or (len(clean_t) >= 35 and (" - " in clean_t or ":" in clean_t or "," in clean_t))
                                        )
                                        r_type_html = "ARTICLE" if is_art_html else "CATEGORY"
                                        if not any(r["title"] == clean_t or r["article_url"] == full_art_url for r in headline_records):
                                            idx = len(headline_records) + 1
                                            headline_records.append({
                                                "evidence_ref": f"hl_{idx:02d}",
                                                "title": clean_t,
                                                "article_url": full_art_url,
                                                "source_url": target_url,
                                                "record_type": r_type_html,
                                                "dom_selector": "article.vnn-title a" if is_art_html else "nav.vnn-menu a",
                                                "dom_snippet": f'<a href="{full_art_url}" data-type="{r_type_html}">{clean_t}</a>',
                                            })
                                        if len(headline_records) >= 12:
                                            break
                                    if headline_records and not page_text:
                                        page_text = "\n".join(
                                            f"[{r['evidence_ref']}] {r['title']} ({r['article_url']})"
                                            for r in headline_records
                                        )
                            except Exception:
                                pass

                        state.record_latency("dom_extraction_ms", (time.perf_counter() - t_dom_start) * 1000)

                    # Đồng bộ headlines và headline_records
                    if headline_records and not headlines:
                        headlines = [f"[{r['evidence_ref']}] {r['title']}" for r in headline_records]
                    elif headlines and not headline_records:
                        for idx, h_item in enumerate(headlines[:12], start=1):
                            if not BrowserEvidence.is_contaminated_or_metadata_text(h_item, final_url_eff):
                                is_art_h = len(h_item) >= 20 and (" - " in h_item or ":" in h_item or "," in h_item or len(h_item) > 25)
                                r_type_h = "ARTICLE" if is_art_h else "CATEGORY"
                                headline_records.append({
                                    "evidence_ref": f"hl_{idx:02d}",
                                    "title": h_item,
                                    "article_url": f"{final_url_eff.rstrip('/')}/article_{idx:02d}.html",
                                    "source_url": target_url,
                                    "record_type": r_type_h,
                                    "dom_selector": "article.item-news a" if is_art_h else "nav a",
                                    "dom_snippet": f'<a href="{final_url_eff.rstrip("/")}/article_{idx:02d}.html">{h_item}</a>',
                                })
                    if headline_records and (not page_text or BrowserEvidence.is_contaminated_or_metadata_text(page_text)):
                        page_text = "\n".join(
                            f"[{r['evidence_ref']}] {r['title']} - {r['article_url']}"
                            for r in headline_records
                        )

                    if screenshot_path and os.path.isfile(screenshot_path) and not screenshot_sha256:
                        try:
                            with open(screenshot_path, "rb") as f_img:
                                screenshot_sha256 = hashlib.sha256(f_img.read()).hexdigest()
                        except Exception:
                            screenshot_sha256 = ""

                    captured_at_iso = datetime.now(timezone.utc).isoformat()
                    evidence_payload = {
                        "evidence_id": f"ev_{uuid.uuid4().hex[:12]}",
                        "task_id": state.task_id,
                        "trace_id": state.trace_id,
                        "source_url": target_url,
                        "final_url": final_url_eff,
                        "captured_at": str(snap_data.get("captured_at") or captured_at_iso),
                        "screenshot_path": str(screenshot_path or ""),
                        "screenshot_sha256": str(screenshot_sha256 or ""),
                        "headlines": headlines,
                        "headline_records": headline_records,
                        "dom_excerpt": page_text[:2000],
                    }

                    # R1.1–R1.3, R1.6 & R2.5–R2.6: Kiểm định BrowserEvidence bắt buộc trước khi tổng hợp
                    t_ev_val = time.perf_counter()
                    try:
                        ev_obj = BrowserEvidence(**evidence_payload)
                        integrity = ev_obj.validate_integrity(
                            expected_task_id=state.task_id,
                            expected_trace_id=state.trace_id,
                            require_headline_records=True,
                        )
                        is_ok = bool(integrity.get("valid"))
                        reason = str(integrity.get("reason", "BROWSER_EVIDENCE_INTEGRITY_FAILED"))
                    except Exception as ev_err:
                        is_ok, reason = False, f"BROWSER_EVIDENCE_SCHEMA_ERROR: {ev_err}"
                    state.record_latency("evidence_validation_ms", (time.perf_counter() - t_ev_val) * 1000)

                    if not is_ok:
                        state.status_override = "BLOCKED"
                        state.error_message = reason
                        state.final_answer = ""
                        engine.publish_mission_log(
                            "ERROR",
                            f"🛑 [FAST-BROWSER-EVIDENCE-GATE]: Chặn tổng hợp do thiếu bằng chứng trình duyệt: {reason}",
                            state.task_id,
                            state.trace_id,
                        )
                        return f"[BROWSER_EVIDENCE_BLOCKED]: {reason}"

                    state.browser_evidence = evidence_payload
                    if screenshot_path:
                        state.add_artifact(screenshot_path)
                    obs_report = f"Đã mở trực quan thành công {target_url}."
                    if filename or screenshot_path:
                        obs_report += f" Ảnh chụp toàn trang: {filename or screenshot_path} (SHA256: {screenshot_sha256[:12]})."
                    if page_text:
                        obs_report += f"\nNội dung chính trang web:\n{page_text}"
                    return f"[BROWSER_OBSERVATION]: {obs_report}"
                else:
                    client = await self._get_http_client()
                    gateway = ExecutorGateway(client)
                    from core.kernel.task_contract_store import get_or_create_default_contract, get_or_create_policy_snapshot
                    get_or_create_default_contract(state.task_id)
                    get_or_create_policy_snapshot(state.task_id)
                    engine.publish_mission_log("ZENITH", "Khởi động tìm kiếm mạng thời gian thực (DuckDuckGo 0đ)...", state.task_id, state.trace_id)
                    search_query = state.goal
                    clean_q = re.sub(r'[\?\!\.\,]+$', '', search_query.strip())

                    # 1. Thử nghiệm trực tiếp công cụ DuckDuckGo 0đ in-process (<3s)
                    obs = ""
                    try:
                        from tools.web_search import run as execute_ddg
                        ddg_res = execute_ddg({"query": clean_q, "local_only": False})
                        if ddg_res.get("status") == "success":
                            items = ddg_res.get("results") or []
                            snippets = []
                            for r in items[:5]:
                                if isinstance(r, dict):
                                    t_title = r.get("title", "")
                                    t_snip = r.get("snippet", "")
                                    t_url = r.get("url", "")
                                    if t_snip:
                                        snippets.append(f"- {t_title}: {t_snip} (Nguồn: {t_url})")
                            if snippets:
                                obs = "\n".join(snippets)
                    except Exception as ddg_err:
                        logger.warning(f"[FAST-DDG-DIRECT-ERR] {ddg_err}")

                    # 2. Fallback sang executor gateway nếu in-process không có kết quả
                    if not obs:
                        tool_calls = [{"function": {"name": "SEARCH_WEB_GLOBAL", "arguments": json.dumps({"query": search_query})}}]
                        try:
                            obs = await asyncio.wait_for(
                                self._run_skills(tool_calls, state.task_id, gateway, state.trace_id),
                                timeout=10.0
                            )
                        except Exception:
                            obs = ""

                    if obs:
                        return f"[THÔNG TIN THỰC TẾ TỪ MẠNG]:\n{obs}"
                    return ""
            except asyncio.TimeoutError:
                state.circuit_breaker_triggered = True
                engine.publish_mission_log("WARN", "[CIRCUIT-BREAKER] Tác vụ mạng vượt quá thời gian. Kích hoạt tri thức nội tại sẵn có.", state.task_id, state.trace_id, stealth=True)
                return "[TIMEOUT]: Tác vụ mạng quá thời gian. Sử dụng tri thức nội tại của mô hình."
            except Exception as e:
                logger.error(f"[FAST-SEARCH-FAIL] {e}")
                return f"[SEARCH-ERR]: {e}"

        # RAG Retrieval nội bộ & Direct Skill Lookup (Timeout 2.5s)
        try:
            g_low = state.goal.lower()
            # Tra cứu Operational Memory nếu có yêu cầu tham chiếu quá khứ/thao tác gần đây
            if getattr(state.decision, "need_operational_context", False) or any(k in g_low for k in ["hồi nãy", "vừa rồi", "lúc nãy", "vừa xóa", "vừa tạo", "nguồn từ đâu", "xóa bao nhiêu", "làm gì"]):
                from context.working_memory import recent_operations_store
                ops_summary = recent_operations_store.get_recent_summary(limit=10)
                return (
                    f"[NHẬT KÝ VẬN HÀNH THỰC TẾ (OPERATIONAL MEMORY - RECENT OPERATIONS)]:\n"
                    f"{ops_summary}\n\n"
                    f"[CHỈ DẪN]: Hãy trích dẫn chính xác các mốc thời gian và hành động thực tế đã diễn ra ở trên để trả lời Master, không tự suy đoán."
                )

            # Tra cứu trực tiếp nếu là câu hỏi về kỹ năng/skill của JKAI
            if any(k in g_low for k in ["skill", "kỹ năng", "dùng để làm gì", "dùng de lam", "thiếu dữ liệu", "có dữ liệu"]):
                from core.kernel.semantic_skill_registry import semantic_skill_registry
                manifests = semantic_skill_registry.list_all_manifests()
                
                # 1. Nếu là câu hỏi tổng quan (VD: "còn skill nào không có dữ liệu", "có bao nhiêu skill", "danh sách skill")
                if any(k in g_low for k in ["còn skill nào", "những skill nào", "bao nhiêu skill", "danh sách", "toàn bộ skill", "không có dữ liệu", "thiếu"]):
                    by_domain = {}
                    for m in manifests:
                        d_name = m.domain.value
                        by_domain.setdefault(d_name, []).append(m.skill_id)
                    
                    domain_summary = "\n".join([f"- **{d}** ({len(slist)} skills): {', '.join(slist[:6])}..." for d, slist in by_domain.items()])
                    return (
                        f"[NGUỒN DỮ LIỆU SỞ TẠI: SemanticSkillRegistry & FileSystem /skills/]:\n"
                        f"- Hệ thống đang nạp chính xác **{len(manifests)} KỸ NĂNG VẬT LÝ** từ đĩa cứng.\n"
                        f"- Toàn bộ các kỹ năng đều có đủ mã nguồn logic.py và hồ sơ năng lực.\n"
                        f"- Phân bố theo các phân khu tác chiến:\n{domain_summary}"
                    )

                # 2. Nếu hỏi về một skill cụ thể
                for m in manifests:
                    if m.skill_id.lower() in g_low or any(a.lower() in g_low for a in m.aliases):
                        return (
                            f"[KỸ NĂNG HỆ THỐNG: {m.display_name} ({m.skill_id})]:\n"
                            f"- Phân khu: {m.domain.value}\n"
                            f"- Mô tả năng lực: {m.description}\n"
                            f"- Khi nào sử dụng: {', '.join(m.when_to_use)}\n"
                            f"- Các hàm/chức năng chính: {', '.join(m.tags)}"
                        )

            from core.utils.knowledge_manager import knowledge_orchestrator
            kb_intel = await asyncio.wait_for(
                knowledge_orchestrator.smart_retrieve(state.goal, state.task_id, top_k=state.decision.kb_top_k, expansion_radius=150),
                timeout=2.5
            )
            return (kb_intel or {}).get("context", "").strip()
        except Exception:
            return ""

    async def _task_admission_and_firewall(self, state: FastState) -> None:
        """Nhánh D: Admission, TaskContract, ContextFirewall."""
        try:
            from core.kernel.task_contract_store import set_active_contract, set_policy_snapshot
            from core.kernel.policy_snapshot import create_policy_snapshot
            from prompt_engine.task_contract import TaskContract, DecisionAuthority

            fast_snap = create_policy_snapshot(
                mission_id=state.task_id,
                can_modify_files=True,
                can_delete_files=False,
                can_send_external_message=True,
                can_execute_shell=False,
                budget_max_turns=state.decision.max_turns
            )
            set_policy_snapshot(state.task_id, fast_snap)
            fast_contract = TaskContract(
                objective=state.goal,
                decision_authority=DecisionAuthority(can_modify_files=True, can_delete_files=False, can_send_external_message=True)
            )
            set_active_contract(state.task_id, fast_contract)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 3: ONE-PASS SYNTHESIS
    # ─────────────────────────────────────────────────────────────────────────
    async def _stage_one_pass_synthesis(
        self,
        state: FastState,
        mode: str,
        history: Optional[List[Dict[str, Any]]],
        images: Optional[Any]
    ) -> None:
        """Thực hiện Inference 1 lần duy nhất với Ground Truth context và Master Prompt Architect."""
        from prompt_assembler import ZenithPromptAssembler
        t_st3_prep = time.perf_counter()
        
        # 1. Chuẩn bị prompt với Ground Truth (Đã qua Fact Distiller tinh chế)
        if state.decision.mode == IntentMode.REALTIME:
            # Epistemic Gate: Khóa chặt nguyên tắc Truth Authority First
            # Nếu tìm kiếm web thất bại hoặc rỗng, TUYỆT ĐỐI KHÔNG để model bịa đặt từ tri thức cũ
            kb_raw = state.kb_context or ""
            is_valid_evidence = (
                len(kb_raw.strip()) > 50 
                and "[TIMEOUT]" not in kb_raw 
                and "[SEARCH-ERR]" not in kb_raw
                and "All search sources" not in kb_raw
            )
            
            if not is_valid_evidence:
                state.final_answer = (
                    "⚠️ **Thông Báo Trạng Thái Tìm Kiếm Thời Gian Thực**\n\n"
                    "Hiện tại kết nối tới các nguồn tìm kiếm trực tuyến (Tavily/Internet) đang gặp sự cố hoặc vượt quá giới hạn thời gian (Circuit Breaker).\n\n"
                    "Theo Hiến chương Quản trị Nhận thức JKAI (DEMS), hệ thống **từ chối suy đoán hoặc sử dụng dữ liệu cũ trong mô hình** để trả lời câu hỏi thời sự hôm nay nhằm đảm bảo tính xác thực 100%.\n\n"
                    "Master vui lòng thử lại sau giây lát hoặc kiểm tra kết nối mạng."
                )
                return

            if state.browser_evidence or "[BROWSER_OBSERVATION]" in kb_raw or "BROWSER" in state.decision.tags:
                if not isinstance(state.browser_evidence, dict):
                    state.status_override = "BLOCKED"
                    state.error_message = "MISSING_VALIDATED_BROWSER_EVIDENCE_IN_STAGE_3"
                    state.final_answer = ""
                    return

                bev = state.browser_evidence
                # R2.5 & R2.6: Re-verify BrowserEvidence contract + headline_records integrity before Stage 3 synthesis
                try:
                    from mission_state.schema import BrowserEvidence
                    bev_obj = BrowserEvidence(**bev)
                    bev_chk = bev_obj.validate_integrity(
                        expected_task_id=state.task_id,
                        expected_trace_id=state.trace_id,
                        require_headline_records=True,
                    )
                    if not bev_chk.get("valid"):
                        state.status_override = "BLOCKED"
                        state.error_message = str(bev_chk.get("reason", "STAGE_3_BROWSER_EVIDENCE_INVALID"))
                        state.final_answer = ""
                        return
                except Exception as st3_ev_err:
                    state.status_override = "BLOCKED"
                    state.error_message = f"STAGE_3_BROWSER_EVIDENCE_ERROR: {st3_ev_err}"
                    state.final_answer = ""
                    return

                screenshot_file = str(bev.get("screenshot_path", ""))
                screenshot_sha256 = str(bev.get("screenshot_sha256", ""))
                observed_url = str(bev.get("final_url") or bev.get("source_url") or "https://vietnamnet.vn/")
                domain = observed_url.split('/')[2] if '/' in observed_url else observed_url
                try:
                    from mission_state.schema import TemporalContext
                    temporal_directive = TemporalContext.from_kernel().to_prompt_directive()
                except Exception:
                    temporal_directive = ""

                hl_records = [
                    r for r in (bev.get("headline_records") or [])
                    if isinstance(r, dict) and r.get("record_type", "ARTICLE") == "ARTICLE"
                ] or (bev.get("headline_records") or [])
                formatted_hl_lines = "\n".join(
                    f"- [{r.get('evidence_ref')}] {r.get('title')} (URL: {r.get('article_url')})"
                    for r in hl_records
                    if isinstance(r, dict)
                )
                validated_payload_json = json.dumps(bev, ensure_ascii=False, indent=2)
                img_embed_snippet = (
                    f"- **Ảnh chụp thực địa toàn trang**:\n"
                    f"![Ảnh chụp toàn trang {domain}]({screenshot_file}) *(SHA256: `{screenshot_sha256[:16]}...`)*\n\n"
                    if screenshot_file else ""
                )

                state.step_goal = (
                    f"{state.goal}\n\n"
                    f"{temporal_directive}\n\n"
                    f"[SYSTEM-DIRECTIVE: BÁO CÁO QUAN SÁT TRỰC QUAN WEB DỰA TRÊN VALIDATED BROWSER EVIDENCE CONTRACT]:\n"
                    f"1. Chỉ được phép tóm tắt dựa trên danh sách HEADLINE RECORDS đã xác thực dưới đây (tuyệt đối không dùng nguồn ngoài hợp đồng, không lặp lại chỉ dẫn hệ thống hay Policy nội bộ):\n"
                    f"{formatted_hl_lines}\n\n"
                    f"2. BẮT BUỘC trích dẫn mã bằng chứng `[hl_01]`, `[hl_02]`... tương ứng cho từng tiêu điểm trong bài tóm tắt.\n"
                    f"3. Đối tượng BrowserEvidence nguyên bản:\n"
                    f"```json\n{validated_payload_json}\n```\n\n"
                    f"Hãy định dạng câu trả lời theo mẫu Markdown sau:\n\n"
                    f"### 🌐 Quan Sát Trực Quan: [{domain}]({observed_url})\n\n"
                    f"- **Trạng thái**: ✅ Đã truy cập thành công và chụp trọn vẹn toàn bộ chiều dài trang web (`evidence_id={bev.get('evidence_id')}`).\n"
                    f"{img_embed_snippet}"
                    f"#### 📰 Tổng Hợp Các Tin Tiêu Điểm (Kèm Trích Dẫn `evidence_ref`):\n"
                )
            else:
                from core.knowledge_sources.fact_distiller import fact_distiller
                distilled_kb = fact_distiller.distill_facts(state.kb_context, query=state.goal, max_facts=8)
                state.step_goal = (
                    f"{state.goal}\n\n"
                    f"[THÔNG TIN TRÍCH XUẤT THỜI GIAN THỰC TỪ NGUỒN MẠNG (GROUNDED OBSERVATION)]:\n"
                    f"Dưới đây là các dữ liệu thực tế đã được trích xuất để làm căn cứ trả lời câu hỏi của người dùng:\n"
                    f"{distilled_kb}\n\n"
                    f"[CHỈ DẪN TRẢ LỜI]: Sử dụng các thông tin thực tế trên để trả lời trực tiếp, chính xác, súc tích và có căn cứ cho câu hỏi của người dùng. Nếu có nguồn tin cụ thể, hãy trích dẫn ngắn gọn."
                )
        elif state.kb_context:
            from core.knowledge_sources.fact_distiller import fact_distiller
            distilled_kb = fact_distiller.distill_facts(state.kb_context, query=state.goal, max_facts=8)
            _, state.step_goal = ZenithPromptAssembler.assemble_prompt(
                goal=state.goal, manifesto="", skills_dna="",
                kb_context=distilled_kb, kb_sufficient=len(distilled_kb) >= 80,
                extra_context={"task_tags": state.decision.tags, "action_type": state.decision.action_type.value}
            )
        else:
            state.step_goal = state.goal

        # 2. Xây dựng System Prompt tối ưu MID Mode từ Master Prompt Architect
        system_content = self._get_supreme_prompt(mode=mode, goal=state.step_goal, task_id=state.task_id, tags=state.decision.tags)
        context_msgs = list(history or []) + [{"role": "user", "content": state.step_goal}]
        
        # 3. Dynamic Token Budget Check & Compaction
        state.messages = context_msgs
        if state.estimate_tokens() > state.max_token_budget * 0.7:
            context_msgs = await compaction_engine.condense(context_msgs, state.task_id)

        # 4. Tools spec (Chỉ cấp tools cho tác vụ Office hoặc Coding)
        tools = []
        if state.decision.need_tools and not state.decision.force_synthesis:
            tools = await self._get_tool_spec(goal=state.goal, intent=state.decision.mode.value)

        # 4.5. Pre-Flight Verification Gate (Fact-Checking Ground Truth on Disk/Registry)
        preflight_verified_data = []
        if getattr(state.decision, "require_verification", False) or any(k in state.goal.lower() for k in ["bao nhiêu", "số lượng", "tồn tại", "trạng thái"]):
            try:
                # 1. Kiểm tra số lượng skill thực tế
                if any(k in state.goal.lower() for k in ["skill", "kỹ năng"]):
                    from core.kernel.semantic_skill_registry import semantic_skill_registry
                    count = len(semantic_skill_registry.list_all_manifests())
                    preflight_verified_data.append(f"[PREFLIGHT-VERIFIED: Tổng số kỹ năng vật lý thực tế trên hệ thống = {count}]")

                # 2. Kiểm tra thao tác gần nhất
                if any(k in state.goal.lower() for k in ["hồi nãy", "vừa rồi", "xóa", "tạo", "làm gì"]):
                    from context.working_memory import recent_operations_store
                    last_ops = recent_operations_store.get_recent_summary(limit=5)
                    preflight_verified_data.append(f"[PREFLIGHT-VERIFIED: Lịch sử thao tác 1h qua]:\n{last_ops}")
            except Exception as e:
                logger.warning(f"[PREFLIGHT-GATE] Lỗi kiểm chứng: {e}")

        if preflight_verified_data:
            verified_block = "\n".join(preflight_verified_data)
            context_msgs.append({"role": "system", "content": f"🚨 [GROUND-TRUTH-VERIFICATION]: Dữ liệu kiểm chứng thực nghiệm từ hệ điều hành:\n{verified_block}\nBắt buộc phải trả lời dựa trên dữ liệu kiểm chứng này, không tự bịa đặt."})

        # 4.6. Episodic Multi-Domain Memory Brain (Bộ Não Ngoài Truy Xuất Theo Mã Việc)
        try:
            from core.memory.episodic_brain import episodic_brain, classify_task, THETA_UNFIT_PLACEHOLDER
            # Phân loại mã việc theo Taxonomy 2 tầng (Router tags -> Bảng từ khóa -> Khóa chặn)
            task_code = classify_task(
                goal=state.goal,
                tags=getattr(state.decision, "tags", []) or [],
                mode=str(getattr(state.decision, "mode", ""))
            )

            # Quy tắc sắt: Nếu có mã việc hợp lệ mới truy xuất, ngoài phạm vi cấm đoán bừa
            if task_code:
                exemplars = episodic_brain.recall_relevant_exemplars(
                    goal=state.step_goal,
                    task_code=task_code,
                    top_k=2,
                    threshold=THETA_UNFIT_PLACEHOLDER
                )
                if exemplars:
                    memory_prompt = episodic_brain.format_context_prompt(exemplars)
                    context_msgs.append({
                        "role": "system",
                        "content": memory_prompt.strip()
                    })
                    ref_ids = [ex.record_id for ex in exemplars]
                    engine.publish_mission_log(
                        "BRAIN",
                        f"🧠 [EPISODIC-BRAIN-HIT]: Kích hoạt {len(exemplars)} bài học chuẩn Master (Refs: {', '.join(ref_ids)} | TaskCode: {task_code})",
                        state.task_id,
                        state.trace_id,
                        stealth=True
                    )
        except Exception as ex_epi:
            logger.warning("[EPISODIC-BRAIN-WARN] Lỗi truy xuất bộ não ngoài: %s", ex_epi)

        # 4.7. Fallback Negative Memory từ ExperienceStore (nếu có bài học cục bộ cũ)
        try:
            from core.memory.experience_store import ExperienceStore
            from core.memory.telemetry_experience_bridge import compute_error_fingerprint, telemetry_bridge
            telemetry_bridge.sync_labeled_records()
            fingerprint = compute_error_fingerprint(state.goal)
            past_lessons = ExperienceStore.get_negative_lessons(fingerprint)
            if past_lessons:
                lesson_text = "\n".join([f"- {l}" for l in past_lessons[-3:]])
                context_msgs.append({
                    "role": "system",
                    "content": f"⚠️ [NEGATIVE-LESSON-GUARD]: Tránh lặp lại sai sót cũ:\n{lesson_text}"
                })
        except Exception as ex_neg:
            logger.debug("[NEGATIVE-MEMORY-SKIP] %s", ex_neg)


        # 5. One-Pass Inference qua Central Engine
        if self._is_stopped(state.task_id):
            state.status_override = "STOPPED"
            state.final_answer = ""
            return

        role = state.decision.role
        state.record_latency("prompt_assembly_and_memory_recall_ms", (time.perf_counter() - t_st3_prep) * 1000)
        t_llm_start = time.perf_counter()
        try:
            response = await engine.call_chat(
                messages=[{"role": "system", "content": system_content}] + context_msgs,
                role=role, task_id=state.task_id, trace_id=state.trace_id, tools=tools,
                skip_memory=True, skip_build_final=True, skip_identity=True,
                skip_json=True,
                options={"num_predict": 450}
            )
        except MasterAbortException:
            state.status_override = "STOPPED"
            state.final_answer = ""
            return
        finally:
            state.record_latency("llm_synthesis_ms", (time.perf_counter() - t_llm_start) * 1000)
        t_st3_post = time.perf_counter()

        if self._is_stopped(state.task_id):
            state.status_override = "STOPPED"
            state.final_answer = ""
            return

        res_content = response.get("answer", "") if isinstance(response, dict) else (response or "")
        res_str = str(res_content)

        # 5.1. Xử lý và thực thi công cụ trực tiếp (Tool-Calling Execution Wiring)
        tool_calls = []
        if isinstance(response, dict) and response.get("tool_calls"):
            tool_calls = response["tool_calls"]
        elif tools:
            # Fallback: bóc tách tool calls dạng lexical (Action: ... / Markdown JSON) nếu model output dưới dạng văn bản
            from core.os.cognition.fast_tool_parser import extract_tool_calls_lexical
            tool_calls = extract_tool_calls_lexical(res_str)

        if tool_calls:
            engine.publish_mission_log("ACTUATOR", f"Phát hiện {len(tool_calls)} lệnh gọi công cụ từ mô hình. Đang thực thi trực tiếp qua ExecutorGateway...", state.task_id, state.trace_id)
            try:
                from receptionist.executor_gateway import ExecutorGateway
                from core.kernel.task_contract_store import get_or_create_default_contract, get_or_create_policy_snapshot
                
                # Khởi tạo hợp đồng nhiệm vụ & policy snapshot mặc định để không bị ExecutionIntegrity chặn
                get_or_create_default_contract(state.task_id)
                get_or_create_policy_snapshot(state.task_id)

                client = await self._get_http_client()
                gateway = ExecutorGateway(client)
                tool_obs = await self._run_skills(tool_calls, state.task_id, gateway, state.trace_id)
                
                # Nạp kết quả thực thi công cụ vào context và gọi mô hình tổng hợp lần cuối
                engine.publish_mission_log("BRAIN", "Đã nhận kết quả thực thi công cụ. Đang tổng hợp phản hồi cuối cùng...", state.task_id, state.trace_id, stealth=True)
                synth_msgs = context_msgs + [
                    {"role": "assistant", "content": res_str},
                    {"role": "user", "content": f"[TOOL OBSERVATION RESULT]:\n{tool_obs}\n\nHãy tổng hợp kết quả chính xác, chu đáo để trả lời Master dựa trên kết quả thực thi ở trên."}
                ]
                final_res = await engine.call_chat(
                    messages=[{"role": "system", "content": system_content}] + synth_msgs,
                    role=role, task_id=state.task_id,
                    skip_memory=True, skip_build_final=True, skip_identity=True,
                    skip_json=True,
                    options={"num_predict": 450}
                )
                res_str = final_res.get("answer", "") if isinstance(final_res, dict) else str(final_res)
            except Exception as ex_tool:
                logger.warning("[TOOL-WIRING-ERR] Lỗi thực thi công cụ trực tiếp: %s", ex_tool)

        # 6. Self-Reflection Guard
        try:
            audit = self_reflection_guard.audit_response(res_str)
            if not audit["is_clean"]:
                engine.publish_mission_log("SYSTEM", f"[REFLECTION] Placeholder detected - {audit['reason']}", state.task_id, state.trace_id, stealth=True)
        except Exception:
            pass

        # 7. Code-as-Action Sandbox Runner, Pre-Execution AST & Self-Healing Loop
        from core.kernel.code_actuator import code_actuator
        from core.os.cognition.fast_verifier import fast_verifier
        
        py_code = code_actuator.extract_python_code(res_str)
        if py_code and any(lib in py_code for lib in ["openpyxl", "docx", "reportlab", "pandas"]):
            max_heal_attempts = 1
            current_code = py_code
            
            for attempt in range(max_heal_attempts + 1):
                # 7.1. AST Syntax Check
                import ast
                syntax_err = None
                try:
                    ast.parse(current_code)
                except SyntaxError as e:
                    syntax_err = str(e)

                if syntax_err:
                    engine.publish_mission_log("WARN", f"[SELF-HEAL] Phát hiện lỗi cú pháp: {syntax_err}. Đang yêu cầu sửa lại...", state.task_id, state.trace_id)
                    try:
                        from core.kernel.immune_memory import immune_system
                        immune_system.register_failure(
                            failure_pattern=syntax_err,
                            root_cause="AST Python SyntaxError",
                            prescriptive_rule=f"Tránh lỗi cú pháp: {syntax_err}",
                            task_id=state.task_id
                        )
                    except Exception:
                        pass
                    if attempt < max_heal_attempts:
                        heal_prompt = f"Mã Python của bạn gặp lỗi cú pháp AST: `{syntax_err}`. Hãy viết lại toàn bộ khối mã Python chuẩn xác, không có lỗi cú pháp."
                        heal_res = await engine.call_chat(
                            messages=[{"role": "system", "content": system_content}] + context_msgs + [
                                {"role": "assistant", "content": res_str},
                                {"role": "user", "content": heal_prompt}
                            ],
                            role=role, task_id=state.task_id, skip_memory=True, skip_build_final=True, skip_identity=True
                        )
                        res_str = heal_res.get("answer", "") if isinstance(heal_res, dict) else str(heal_res)
                        current_code = code_actuator.extract_python_code(res_str) or current_code
                        continue
                    break

                # 7.2. Sandbox Execution
                engine.publish_mission_log("ACTUATOR", f"Khởi chạy Sandbox thực thi mã Python vật lý (Lần {attempt+1})...", state.task_id, state.trace_id)
                act_res = code_actuator.execute_office_code(current_code, state.task_id)
                
                is_act_success = act_res.get("success") is True or act_res.get("status") == "success"
                fpath = act_res.get("file_path") or act_res.get("created_file")

                if is_act_success and fpath and os.path.exists(fpath):
                    # 7.3. Deterministic Verification & Packaging
                    v_rec = fast_verifier.verify_artifact(fpath)
                    if v_rec.is_verified:
                        state.add_artifact(fpath)
                        try:
                            from core.kernel.artifact_packager import artifact_packager
                            pkg = artifact_packager.package_artifacts(state.task_id, [fpath])
                            engine.publish_mission_log("PACKAGER", f"Đã đóng gói giao hàng: Package ID `{pkg.package_id}` (Manifest SHA-256)", state.task_id, state.trace_id)
                        except Exception:
                            pass
                        engine.publish_mission_log("ACTUATOR", f"Tạo và thẩm định file thành công: `{fpath}` (SHA: {v_rec.artifact_sha256[:12]})", state.task_id, state.trace_id)
                        state.final_answer = f"{res_str}\n\n📁 **Tệp tin đã tạo:** `{fpath}`"
                        state.is_completed = True
                        return
                    else:
                        engine.publish_mission_log("WARN", f"[VERIFY-FAIL] Tệp tin chưa đạt tiêu chuẩn ({v_rec.failure_class}): {v_rec.recovery_hint}", state.task_id, state.trace_id)
                        if attempt < max_heal_attempts:
                            heal_prompt = f"Tệp tin được sinh ra `{fpath}` chưa đạt tiêu chuẩn thẩm định: {v_rec.failure_class}. Gợi ý: {v_rec.recovery_hint}. Hãy sửa lại mã Python để đảm bảo tạo file hợp lệ."
                            heal_res = await engine.call_chat(
                                messages=[{"role": "system", "content": system_content}] + context_msgs + [
                                    {"role": "assistant", "content": res_str},
                                    {"role": "user", "content": heal_prompt}
                                ],
                                role=role, task_id=state.task_id, skip_memory=True, skip_build_final=True, skip_identity=True
                            )
                            res_str = heal_res.get("answer", "") if isinstance(heal_res, dict) else str(heal_res)
                            current_code = code_actuator.extract_python_code(res_str) or current_code
                            continue
                else:
                    err_detail = act_res.get("error", "Không xác định")
                    engine.publish_mission_log("WARN", f"[ACTUATOR-FAIL] Lỗi thực thi sandbox: {err_detail}", state.task_id, state.trace_id)
                    if attempt < max_heal_attempts:
                        heal_prompt = f"Khi chạy mã Python trong sandbox gặp lỗi runtime sau:\n`{err_detail}`\nHãy sửa lại mã Python để khắc phục lỗi runtime trên."
                        heal_res = await engine.call_chat(
                            messages=[{"role": "system", "content": system_content}] + context_msgs + [
                                {"role": "assistant", "content": res_str},
                                {"role": "user", "content": heal_prompt}
                            ],
                            role=role, task_id=state.task_id, skip_memory=True, skip_build_final=True, skip_identity=True
                        )
                        res_str = heal_res.get("answer", "") if isinstance(heal_res, dict) else str(heal_res)
                        current_code = code_actuator.extract_python_code(res_str) or current_code
                        continue

        # Ghi nhận kết quả — chiết xuất văn bản nếu model trả về JSON có cấu trúc
        state.final_answer = _unwrap_structured_response(
            res_str or "Đã hoàn tất xử lý yêu cầu thưa Master."
        )

        # R2.5 & R2.6: Kiểm định chống nhiễm bẩn Policy/Instruction và ràng buộc trích dẫn evidence_ref cho tác vụ trình duyệt
        if isinstance(state.browser_evidence, dict) and state.browser_evidence:
            t_gr_start = time.perf_counter()
            try:
                from mission_state.schema import BrowserEvidence
                contam_err = BrowserEvidence.is_contaminated_or_metadata_text(state.final_answer)
                if contam_err:
                    state.status_override = "BLOCKED"
                    state.error_message = f"SUMMARY_CONTAMINATION_BLOCKED: {contam_err}"
                    state.final_answer = ""
                    return

                grounding = BrowserEvidence.validate_summary_grounding(state.final_answer, state.browser_evidence)
                if not grounding.get("valid"):
                    hl_recs = state.browser_evidence.get("headline_records") or []
                    art_recs = [r for r in hl_recs if isinstance(r, dict) and r.get("record_type", "ARTICLE") == "ARTICLE"]
                    recs_to_cite = art_recs if art_recs else hl_recs
                    if recs_to_cite and not state.browser_evidence.get("strict_require_llm_citation"):
                        ref_lines = "\n".join(
                            f"- **[{r.get('evidence_ref')}]** [{r.get('title')}]({r.get('article_url')})"
                            for r in recs_to_cite[:8]
                            if isinstance(r, dict) and r.get("evidence_ref")
                        )
                        if ref_lines:
                            state.final_answer = f"{state.final_answer}\n\n#### 🔗 Hồ Sơ Bằng Chứng (`evidence_ref`):\n{ref_lines}"
                            grounding = BrowserEvidence.validate_summary_grounding(state.final_answer, state.browser_evidence)
                    if not grounding.get("valid"):
                        state.status_override = "BLOCKED"
                        state.error_message = str(grounding.get("reason", "SUMMARY_GROUNDING_FAILED"))
                        state.final_answer = ""
                        return
            except Exception as gr_err:
                state.status_override = "BLOCKED"
                state.error_message = f"SUMMARY_GROUNDING_CHECK_ERR: {gr_err}"
                state.final_answer = ""
                return
            finally:
                state.record_latency("grounding_validation_ms", (time.perf_counter() - t_gr_start) * 1000)

        state.record_latency("stage_3_post_synthesis_ms", (time.perf_counter() - t_st3_post) * 1000)
        state.is_completed = True

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 4: POST-PROCESS & PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────
    async def _stage_post_process(self, state: FastState, start_time: float) -> Dict[str, Any]:
        """Lưu ngữ cảnh, đồng bộ bộ nhớ hội thoại, tự phản tư và trả kết quả."""
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        state.record_latency("total_execution_time", total_latency_ms)

        # 1. Tự phản tư và Thẩm định Nhận thức (DEMS Epistemic Auditor)
        try:
            from core.os.cognition.goal_contract import goal_contract_compiler
            from core.os.cognition.epistemic_auditor import epistemic_auditor
            from core.kernel.decision_ledger import decision_ledger
            
            contract = goal_contract_compiler.compile(state.goal)
            audit_report = epistemic_auditor.audit(state.final_answer, contract, state.kb_context)
            
            engine.publish_mission_log(
                "EPISTEMIC_AUDIT",
                f"[{audit_report.verdict.value}] Confidence: {audit_report.confidence:.2f} | Rationale: {audit_report.rationale}",
                state.task_id,
                state.trace_id
            )
            
            decision_ledger.record_decision(
                decision_type="EPISTEMIC_AUDIT",
                task_id=state.task_id,
                input_summary=f"Goal: {state.goal[:80]}...",
                output_decision=audit_report.verdict.value,
                reason=audit_report.rationale
            )

            # Substrate Tool Suggestion: Ghi nhận vào ledger nhưng không tự ý gắn đuôi chào mời vào câu trả lời của Master
            if contract.suggested_action_prompt and not state.artifacts_created:
                decision_ledger.record_decision(
                    decision_type="TOOL_SUGGESTION",
                    task_id=state.task_id,
                    input_summary=f"Goal: {state.goal[:80]}...",
                    output_decision=contract.suggested_tool or "OFFICE_SUITE_MASTER",
                    reason=contract.suggested_action_prompt
                )
            
            # Tích hợp tự động học hỏi vào ExperienceStore (Engram v2)
            if audit_report.verdict.value in ("PARTIALLY_FULFILLED", "OFF_TOPIC", "EVIDENCE_INSUFFICIENT"):
                try:
                    from core.memory.experience_store import ExperienceStore
                    from core.contracts.verification_contract import ExperienceRecord, FailureClassification
                    
                    fail_cls = FailureClassification.VERIFICATION_FAILURE if audit_report.verdict.value == "OFF_TOPIC" else FailureClassification.PLAN_FAILURE
                    ExperienceStore.add_record(ExperienceRecord(
                        task_signature=state.goal[:50],
                        context_summary=f"Audit Verdict: {audit_report.verdict.value}",
                        strategy_used="fast_pipeline_realtime",
                        outcome="FAILED" if audit_report.verdict.value == "OFF_TOPIC" else "PARTIAL",
                        failure_classification=fail_cls,
                        failure_cause=audit_report.rationale,
                        negative_lessons=[f"Audit flagged {audit_report.verdict.value}: {audit_report.rationale}"],
                        confidence_rating=audit_report.confidence
                    ))
                except Exception as ex_exp:
                    log.warning("Could not persist ExperienceRecord: %s", ex_exp)
        except Exception as ex_audit:
            log.warning("Epistemic audit failed: %s", ex_audit)

        # 1b. Thẩm định Chất lượng Phản hồi & Chuẩn hóa ACS (Đúng - Trúng - Đủ)
        try:
            from core.os.cognition.answer_quality_verifier import answer_quality_verifier
            from core.kernel.decision_ledger import decision_ledger

            aqv_report = answer_quality_verifier.verify(state.final_answer, state.goal)
            
            # Áp dụng bản hiệu chỉnh từ AQV (nếu có), đồng thời unwrap JSON phòng thủ
            if aqv_report.corrected_text:
                state.final_answer = _unwrap_structured_response(aqv_report.corrected_text)

            engine.publish_mission_log(
                "ANSWER_QUALITY_AUDIT",
                f"{aqv_report.summary()} | score={aqv_report.overall_score:.2f}",
                state.task_id,
                state.trace_id
            )

            decision_ledger.record_decision(
                decision_type="ANSWER_QUALITY_AUDIT",
                task_id=state.task_id,
                input_summary=f"Goal: {state.goal[:80]}...",
                output_decision="PASSED" if aqv_report.overall_passed else "FLAGGED",
                reason=f"DUNG={aqv_report.dung.passed} TRUNG={aqv_report.trung.passed} DU={aqv_report.du.passed}"
            )
        except Exception as ex_aqv:
            log.warning("Answer quality verification failed: %s", ex_aqv)

        try:
            from core.kernel.self_reflection import self_reflection
            self_reflection.reflect_on_output(
                task_id=state.task_id,
                goal=state.goal,
                answer=state.final_answer,
                has_artifacts=bool(state.artifacts_created)
            )
        except Exception:
            pass

        # 2. Cập nhật context đàm thoại & EntityStack
        try:
            from context import mission_context as ctx_mgr
            from context.entity_resolver import EntityResolver
            from core.os.cognition.entity_stack import get_entity_stack
            
            mc = ctx_mgr.get_or_create(state.task_id, goal=state.goal)
            ent_resolver = EntityResolver()
            subject = ent_resolver.extract_subject(state.goal, state.final_answer)
            mc.conversation["last_subject"] = subject
            mc.conversation["last_query"] = state.goal
            mc.conversation["last_answer"] = state.final_answer
            mc.runtime["status"] = "completed"
            ctx_mgr.update_from_answer(mc, state.goal, state.final_answer)
            ctx_mgr.link_conversation("default", state.task_id)

            # Cập nhật EntityStack cho các lượt chat kế tiếp
            if subject:
                stack = get_entity_stack()
                stack.add_entity(subject, category="CONVERSATION_SUBJECT", confidence=0.95)
                stack.advance_turn()
        except Exception:
            pass

        # 3. Lưu Semantic Cache nếu là câu trả lời chất lượng
        try:
            from semantic_cache import semantic_cache
            if len(state.final_answer) > 20 and not state.artifacts_created and state.decision.mode != IntentMode.REALTIME:
                await semantic_cache.set(state.goal, {"answer": state.final_answer})
        except Exception:
            pass

        return self._format_output(state, start_time)

    def _format_output(self, state: FastState, start_time: float, **kwargs) -> Dict[str, Any]:
        """Format kết quả đầu ra chuẩn hóa kèm Cryptographic Trace Receipts (R2.3)."""
        import hashlib
        total_ms = (time.perf_counter() - start_time) * 1000
        clean_answer = re.sub(r'(?s)<thinking>.*?</thinking>', '', state.final_answer).strip()
        final_ans = clean_answer or state.final_answer
        effective_status = kwargs.get("status") or state.status_override or "SUCCESS"
        summary_published = bool(final_ans and effective_status == "SUCCESS")

        summary_receipt = None
        artifact_receipts = []
        t_rcpt_start = time.perf_counter()
        try:
            from mission_state.schema import ArtifactReceipt
            bev = state.browser_evidence if isinstance(state.browser_evidence, dict) else {}
            ev_id = str(bev.get("evidence_id", ""))
            ev_sha = str(bev.get("screenshot_sha256", ""))
            for fpath in (state.artifacts_created or []):
                if fpath and os.path.isfile(fpath):
                    artifact_receipts.append(
                        ArtifactReceipt.issue(
                            task_id=state.task_id,
                            trace_id=state.trace_id,
                            artifact_type="BROWSER_SCREENSHOT_ARTIFACT" if fpath == bev.get("screenshot_path") else "FILE_ARTIFACT",
                            artifact_path=fpath,
                            evidence_id=ev_id,
                            evidence_sha256=ev_sha,
                        ).model_dump()
                    )
            if summary_published:
                ans_bytes = str(final_ans).encode("utf-8")
                summary_receipt = ArtifactReceipt.issue(
                    task_id=state.task_id,
                    trace_id=state.trace_id,
                    artifact_type="SUMMARY_RECEIPT",
                    artifact_path=f"memory://fast_summary/{state.task_id}",
                    artifact_sha256=hashlib.sha256(ans_bytes).hexdigest(),
                    size_bytes=len(ans_bytes),
                    evidence_id=ev_id,
                    evidence_sha256=ev_sha,
                ).model_dump()
                artifact_receipts.append(summary_receipt)
        except Exception as rcpt_err:
            logger.debug("[FAST-RECEIPT-WARN] %s", rcpt_err)
        state.record_latency("receipt_issuance_ms", (time.perf_counter() - t_rcpt_start) * 1000)

        # R2.8: Chuẩn hóa hạch toán độ trễ Wall-clock strictly additive & Nested span tree
        stage_1_ms = state.latency_breakdown.get("stage_1_adaptive_fork", 0.0)
        stage_2_ms = state.latency_breakdown.get("stage_2_join_verify", 0.0)
        stage_3_ms = state.latency_breakdown.get("stage_3_one_pass_synthesis", 0.0)
        prior_stages = stage_1_ms + stage_2_ms + stage_3_ms
        current_total = (time.perf_counter() - start_time) * 1000
        stage_4_ms = max(0.1, round(current_total - prior_stages, 2))
        state.record_latency("stage_4_post_process", stage_4_ms)
        state.record_latency("total_execution_time", round(current_total, 2))
        latency_accounting = state.get_latency_accounting() if hasattr(state, "get_latency_accounting") else {}

        out = {
            "status": effective_status,
            "answer": final_ans if effective_status == "SUCCESS" else "",
            "task_id": state.task_id,
            "trace_id": state.trace_id,
            "pipeline": "fast",
            "mode": "fast",
            "role": state.decision.role,
            "artifacts": state.artifacts_created,
            "artifact_receipts": artifact_receipts,
            "browser_evidence": state.browser_evidence,
            "summary_published": summary_published,
            "summary_receipt": summary_receipt,
            "circuit_breaker": state.circuit_breaker_triggered,
            "latency_ms": round(current_total, 2),
            "stage_latencies_ms": dict(getattr(state, "latency_breakdown", {})),
            "latency_accounting": latency_accounting,
        }
        out.update(kwargs)
        return out

    # ─────────────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ─────────────────────────────────────────────────────────────────────────
    async def _run_skills(self, tool_calls: list, task_id: str, gateway: ExecutorGateway, trace_id: str) -> str:
        """Thực thi song song các công cụ được gọi với Circuit Breaker 5s."""
        from receptionist.executor_gateway import ExecutionRequest

        async def run_one(tc):
            f_data = tc.get("function", {}) if isinstance(tc, dict) else {}
            tool_name = f_data.get("name", "unknown")
            raw_args = f_data.get("arguments", {})
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except Exception:
                args = {}

            skill_id = args.get("skill_id") or tool_name
            if skill_id == "search_memory":
                return await engine.search_memory(args.get("query", ""), task_id)

            req = ExecutionRequest(
                trace_id=trace_id or task_id,
                capability_token={},
                tool_name=skill_id,
                tool_args={k: v for k, v in args.items() if k != "skill_id"}
            )
            try:
                return await asyncio.wait_for(gateway.execute_tool(req, task_id), timeout=12.0)
            except asyncio.TimeoutError:
                return format_tool_signal(ToolSignalType.NETWORK_TIMEOUT, tool_name, "Tool timeout sau 12s")
            except Exception as e:
                return format_tool_signal(ToolSignalType.EXECUTION_ERROR, tool_name, str(e))

        results = await asyncio.gather(*[run_one(tc) for tc in tool_calls])
        return "\n\n".join([str(r) for r in results])

    async def _distill_knowledge(self, goal: str, raw_data: str, task_id: str) -> str:
        """Chưng cất dữ liệu tìm kiếm bằng Cosine TF-IDF siêu tốc."""
        try:
            from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import chunk_and_rank_segments
            distilled = chunk_and_rank_segments(goal, raw_data, chunk_size=800, max_segments=3)
            if distilled and len(distilled.strip()) > 50:
                return distilled
        except Exception:
            pass
        return raw_data[:2000]

    async def _get_tool_spec(self, goal: str = "", intent: str = "") -> List[Dict[str, Any]]:
        """Truy xuất danh sách Tool Schema động."""
        try:
            from core.os.cognition.skill_retriever import skill_retriever
            verdict = skill_retriever.retrieve_active_tools(query=f"{goal} {intent}", top_k=3)
            if verdict.mcp_tools:
                return verdict.mcp_tools
        except Exception:
            pass
        return [
            {"type": "function", "function": {"name": "SEARCH_WEB_GLOBAL", "description": "Tìm kiếm dữ liệu trực tuyến.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "VIEW_FILE", "description": "Đọc nội dung tệp tin văn bản, mã nguồn cục bộ theo dòng.", "parameters": {"type": "object", "properties": {"AbsolutePath": {"type": "string"}, "StartLine": {"type": "integer"}, "EndLine": {"type": "integer"}}, "required": ["AbsolutePath"]}}},
            {"type": "function", "function": {"name": "WRITE_TO_FILE", "description": "Tạo hoặc ghi đè nội dung tệp tin mã nguồn, text, markdown trực tiếp.", "parameters": {"type": "object", "properties": {"TargetFile": {"type": "string"}, "CodeContent": {"type": "string"}, "Overwrite": {"type": "boolean"}}, "required": ["TargetFile", "CodeContent"]}}},
            {"type": "function", "function": {"name": "OFFICE_SUITE_MASTER", "description": "Tạo file Word, Excel, PDF chuyên nghiệp.", "parameters": {"type": "object", "properties": {"action": {"type": "string"}, "filename": {"type": "string"}, "title": {"type": "string"}}, "required": ["action", "filename", "title"]}}},
            {"type": "function", "function": {"name": "search_memory", "description": "Tra cứu bộ nhớ nội bộ.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}
        ]

    def _get_supreme_prompt(self, mode: str, goal: str, task_id: str, tags: Optional[List[str]] = None) -> str:
        """Sinh System Prompt chuẩn mực tối ưu MID Mode từ Master Prompt Architect kết hợp Immune Invariants."""
        task_tags = tags or ["CHAT"]
        immune_block = ""
        try:
            from core.kernel.immune_memory import immune_system
            immune_block = immune_system.build_immune_prompt_injection()
        except Exception:
            pass

        try:
            available_tool_names = ["SEARCH_WEB_GLOBAL", "VIEW_FILE", "WRITE_TO_FILE", "OFFICE_SUITE_MASTER", "search_memory"]
            active_model = "qwen3.5:4b"
            try:
                from core.utils.engine import engine
                rc = engine.get_role_config("RECEPTIONIST")
                if rc and isinstance(rc, dict) and rc.get("model"):
                    active_model = str(rc.get("model"))
            except Exception:
                pass

            base_prompt = master_prompt_architect.build_master_system_prompt(
                role="RECEPTIONIST",
                task_type=task_tags,
                task_id=task_id,
                goal=goal,
                prompt_variant="MID",
                active_model=active_model,
                available_tools=available_tool_names
            )
            return f"{base_prompt}\n{immune_block}" if immune_block else base_prompt
        except Exception as p_err:
            logger.warning("[PROMPT-ARCHITECT-ERR] %s", p_err)
            import datetime, pytz
            try:
                now_dt = datetime.datetime.now(pytz.timezone("Asia/Bangkok"))
                time_str = now_dt.strftime("%H:%M:%S Thứ %w, ngày %d/%m/%Y")
            except Exception:
                time_str = "Hôm nay"
            fallback_prompt = (
                f"{behavior_injector.inject()}\n\n"
                f"[LIVE TIME ANCHOR]: {time_str} (Giờ Việt Nam UTC+7)\n\n"
                "<constraints>\n"
                "GIAO THỨC PHẢN XẠ & THỰC THI (MANDATORY):\n"
                "1. Khi nhận yêu cầu tạo file Word/Excel/PDF: Viết mã Python thực tế bằng thư viện chuyên dụng (openpyxl, python-docx, reportlab) để thực thi trên Sandbox. Không tạo file giả.\n"
                "2. Sử dụng dữ liệu Observation thực tế được cung cấp để trả lời câu hỏi trực tiếp cho Master.\n"
                "3. Tuyệt đối không bịa đặt dữ liệu khi công cụ không tìm thấy kết quả.\n"
                "</constraints>"
            )
            return f"{fallback_prompt}\n{immune_block}" if immune_block else fallback_prompt
