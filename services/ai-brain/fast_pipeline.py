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
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        
        # 0. DEMS Multi-Turn Coreference Resolution (EntityStack)
        try:
            from context.entity_resolver import EntityResolver
            resolved_goal = EntityResolver().resolve(goal)
            if resolved_goal != goal:
                engine.publish_mission_log("BRAIN", f"🧠 [COREF-RESOLVED]: '{goal}' ➔ '{resolved_goal}'", task_id, trace_id, stealth=True)
                goal = resolved_goal
        except Exception:
            pass

        # 1. Phân loại ý định tập trung & Đa nhãn
        decision = intent_router.route(goal, is_office_task=is_office_task, history=history)
        state = FastState(
            goal=goal,
            task_id=task_id,
            trace_id=trace_id,
            decision=decision,
        )

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

        if state.decision.mode == IntentMode.SOCIAL:
            state.step_goal = state.goal
            state.is_kb_sufficient = True
            engine.publish_mission_log("BRAIN", "[SOCIAL-REFLEX] Phản xạ hội thoại trực tiếp (<800ms).", state.task_id, state.trace_id, stealth=True)

        state.record_latency("stage_2_join_verify", (time.perf_counter() - t0) * 1000)

        # ── STAGE 3: ONE-PASS SYNTHESIS & INFERENCE ─────────────────────────
        t0 = time.perf_counter()
        await self._stage_one_pass_synthesis(state, mode, history, images)
        state.record_latency("stage_3_one_pass_synthesis", (time.perf_counter() - t0) * 1000)

        # ── STAGE 4: POST-PROCESS & CONTEXT PERSISTENCE ─────────────────────
        t0 = time.perf_counter()
        final_output = await self._stage_post_process(state, start_time)
        state.record_latency("stage_4_post_process", (time.perf_counter() - t0) * 1000)

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

        # Realtime Search với Circuit Breaker 5s
        if state.decision.mode == IntentMode.REALTIME:
            try:
                engine.publish_mission_log("ZENITH", "Khởi động tìm kiếm mạng thời gian thực (Circuit Breaker 5s)...", state.task_id, state.trace_id)
                client = await self._get_http_client()
                gateway = ExecutorGateway(client)
                
                search_query = state.goal
                if not any(k in search_query.lower() for k in ["hôm nay", "mới nhất", "2026"]):
                    search_query = f"{state.goal} hôm nay mới nhất"

                tool_calls = [{"function": {"name": "SEARCH_WEB_GLOBAL", "arguments": json.dumps({"query": search_query})}}]
                
                obs = await asyncio.wait_for(
                    self._run_skills(tool_calls, state.task_id, gateway, state.trace_id),
                    timeout=12.0
                )
                if obs and len(obs) > 1500:
                    distilled = await self._distill_knowledge(state.goal, obs, state.task_id)
                    return f"[DISTILLED_TRUTH]: {distilled}\n\n[NOTE]: Nguồn tin đã xếp hạng thời gian thực."
                return obs or ""
            except asyncio.TimeoutError:
                state.circuit_breaker_triggered = True
                engine.publish_mission_log("WARN", "[CIRCUIT-BREAKER] Tìm kiếm mạng vượt quá 12s. Kích hoạt tri thức nội tại sẵn có.", state.task_id, state.trace_id, stealth=True)
                return "[TIMEOUT]: Tìm kiếm mạng quá 12s. Sử dụng tri thức nội tại của mô hình."
            except Exception as e:
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

            from core.knowledge_sources.fact_distiller import fact_distiller
            distilled_kb = fact_distiller.distill_facts(state.kb_context, query=state.goal, max_facts=8)
            state.step_goal = (
                f"{state.goal}\n\n"
                f"[SYSTEM-DIRECTIVE: BẢN TIN THỜI SỰ CHUYÊN NGHIỆP]:\n"
                f"1. Dữ liệu thực tế từ web đã được trích xuất thành công dưới đây.\n"
                f"2. Hãy tổng hợp thành một bản tin thời sự quốc tế đầy đủ, mạch lạc, phân loại rõ ràng theo các chủ đề:\n"
                f"   - 📌 **Chính trị - Quân sự & Địa chính trị Quốc tế** (VD: Xung đột Nga - Ukraine, Trung Đông, v.v.)\n"
                f"   - 📌 **Kinh tế - Tài chính & Thị trường** (VD: Giá vàng thế giới/trong nước, dầu mỏ, Fed, tỷ giá, v.v.)\n"
                f"3. TUYỆT ĐỐI KHÔNG đưa các thông tin bói toán, tử vi, cung hoàng đạo vào bản tin thời sự.\n"
                f"4. Báo cáo trung thực, ghi rõ nguồn tin tham chiếu (VOV, Vietnamnet, Reuters, v.v.).\n\n"
                f"[DISTILLED FACTS OBSERVATION]:\n{distilled_kb}"
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

        # 5. One-Pass Inference qua Central Engine
        role = state.decision.role
        response = await engine.call_chat(
            messages=[{"role": "system", "content": system_content}] + context_msgs,
            role=role, task_id=state.task_id, tools=tools,
            skip_memory=True, skip_build_final=True, skip_identity=True
        )

        res_content = response.get("answer", "") if isinstance(response, dict) else (response or "")
        res_str = str(res_content)

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

        # Ghi nhận kết quả
        state.final_answer = res_str or "Đã hoàn tất xử lý yêu cầu thưa Master."
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

            # Substrate Tool Suggestion: Tự động đề xuất xuất file khi người dùng có nhu cầu tổng hợp
            if contract.suggested_action_prompt and not state.artifacts_created:
                if contract.suggested_action_prompt not in state.final_answer:
                    state.final_answer = f"{state.final_answer}\n\n💡 *{contract.suggested_action_prompt}*"
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
        """Format kết quả đầu ra chuẩn hóa."""
        total_ms = (time.perf_counter() - start_time) * 1000
        clean_answer = re.sub(r'(?s)<thinking>.*?</thinking>', '', state.final_answer).strip()
        out = {
            "answer": clean_answer or state.final_answer,
            "task_id": state.task_id,
            "pipeline": "fast",
            "mode": "fast",
            "role": state.decision.role,
            "artifacts": state.artifacts_created,
            "circuit_breaker": state.circuit_breaker_triggered,
            "latency_ms": round(total_ms, 2)
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
            {"type": "function", "function": {"name": "OFFICE_SUITE_MASTER", "description": "Tạo file Word, Excel, PDF.", "parameters": {"type": "object", "properties": {"action": {"type": "string"}, "filename": {"type": "string"}}, "required": ["action", "filename"]}}},
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
            base_prompt = master_prompt_architect.build_master_system_prompt(
                role="RECEPTIONIST",
                task_type=task_tags,
                task_id=task_id,
                goal=goal,
                prompt_variant="MID"
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
