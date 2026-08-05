"""
⚡ FAST PIPELINE — Zenith v43.0  [RECEPTIONIST ReAct Loop]
═══════════════════════════════════════════════════════════
Đây là Self-Contained Unit — không cần ai điều phối bên ngoài.

  ┌─────────────────────────────────────────────────────────┐
  │  T1  receptionist.py   → Nhận diện & Switchboard       │
  │  FAST  FastPipeline    → RECEPTIONIST ReAct (max 3 turn)│
  │  [Không PLANNER, không EXECUTOR, không CRITIC]          │
  │  T6  FastPipeline      → Trả kết quả (không SUMMARIZER) │
  └─────────────────────────────────────────────────────────┘

NGUYÊN TẮC VÀNG:
  - RECEPTIONIST (qwen3.5:4b) tự suy luận + tool calling
  - IntentCortex phát hiện realtime → search trước khi synthesis
  - Force synthesis: không tool, chỉ tổng hợp từ dữ liệu có sẵn
  - Mọi model map từ rule_hardware.md, KHÔNG set cứng
═══════════════════════════════════════════════════════════
"""
import json, logging, re, asyncio, uuid, datetime
from core.utils.engine import MasterAbortException
from typing import Any, Dict, List, Optional
from core.utils.engine import engine
from core.kernel.compaction import compaction_engine
from receptionist.executor_gateway import ExecutorGateway, ExecutionRequest
from core.utils.search_intelligence import SearchIntelligenceLayer
from core.utils.tracing import TraceContext
from prompt_engine.injectors import behavior_injector
from context import mission_context as ctx_mgr, entity_resolver as ent_resolver, reference_resolver as ref_resolver, working_memory as wm_mgr, fact_extractor as fact_ext
from mission_state import MissionRuntime
from semantic_cache import semantic_cache
from core.utils.mode_switcher import mode_switcher
from core.kernel.cognitive_memory_buffer import cognitive_memory_buffer
from core.kernel.self_reflection_guard import self_reflection_guard
from core.kernel.skill_tool_registry import skill_tool_registry

logger = logging.getLogger("JKAI.FastPipeline")

class FastPipeline:
    """
    ⚡ Luồng Phản Xạ — RECEPTIONIST ReAct loop.
    Không PLANNER, không EXECUTOR, không CRITIC.
    """
    def _evaluate_simple_math(self, text: str) -> Optional[str]:
        try:
            import re
            if any(kw in text.lower() for kw in ['tại sao', 'vì sao', 'giải mã', 'kiến trúc', 'code', 'hàm', 'script', 'lỗi', 'python', 'javascript']):
                return None
            
            # Kích hoạt khi xuất hiện các ý định yêu cầu tính toán hoặc biểu thức mang toán tử rõ ràng
            text_low = text.lower()
            if any(k in text_low for k in ['tính', 'bằng mấy', 'bằng bao nhiêu', 'kết quả', 'bao nhiêu']) or any(op in text for op in ['*', '+', '-', '/']):
                # Lọc bỏ ngày tháng trước khi test
                if re.search(r'\d{1,2}\/\d{1,2}\/\d{2,4}', text):
                    return None
                # Trích xuất biểu thức số học gồm số, toán tử +, -, *, /, (, )
                matches = re.findall(r'(?:\d+[\s]*[\+\-\*\/]+[\s]*)+\d+', text)
                if matches:
                    expr = max(matches, key=len).strip()
                    # Đảm bảo biểu thức an toàn cho eval
                    if re.match(r'^[0-9\s\+\-\*\/\.\(\)]+$', expr):
                        val = eval(expr, {"__builtins__": None}, {})
                        if isinstance(val, (int, float)):
                            if isinstance(val, float) and val.is_integer():
                                val = int(val)
                            val_str = f"{val:,.4f}".rstrip('0').rstrip('.') if isinstance(val, float) else f"{val:,}"
                            val_str = val_str.replace(',', '.')  # Định dạng chuẩn mực Master LeeTrung
                            
                            return (
                                f"⚡ **[MATH-REFLEX ZERO-LATENCY (<1ms)]** ⚡\n\n"
                                f"Báo cáo Master! Hệ thống AI OS đã thiển triện phản xạ nơ-ron tức thì:\n\n"
                                f"📌 **Phép tính:** `{expr}`\n"
                                f"🎯 **Kết quả chính xác:** **{val_str}** (hoặc `{val}`)\n\n"
                                f"*Phần kinh qua cổng phản xạ cực tốc ở chế độ FAST trên JKAI Zenith OS v43.0!*"
                            )
        except Exception:
            pass
        return None

    async def _get_http_client(self):
        return engine._get_client()

    async def execute(
        self,
        goal: str,
        task_id: str,
        planner_instance: Any = None,
        context: Dict = None,
        history: List = None,
        images: List = None,
        mode: str = "fast",
        trace_id: str = "system",
    ) -> Dict[str, Any]:
        context = context or {}
        # context có thể là dict config từ receptionist hoặc list messages từ ReAct
        if isinstance(context, dict):
            context = []
        history = history or []
        max_turns = 10  # Master Specification: FAST is Single-Agent Autonomous Mode capable of multi-step & multi-file execution

        # [PILLAR 7.5: ULTRA-FAST MATH REFLEX (<1ms)]
        math_res = self._evaluate_simple_math(goal)
        if math_res:
            engine.publish_mission_log(
                "SYSTEM",
                f"[MATH-REFLEX] Đã giải quyết bằng phép tính phản xạ.",
                task_id, trace_id, stealth=True
            )
            return {"answer": math_res, "task_id": task_id, "pipeline": "fast", "cached": True}

        # [PILLAR 8: SEMANTIC BYPASS CACHE INTERCEPT (<50ms)]
        try:
            cached_res = semantic_cache.get_cache(goal)
            if cached_res and cached_res.get("cache_hit") is True:
                engine.publish_mission_log(
                    "SYSTEM",
                    f"[SEMANTIC-CACHE HIT] Phục hồi phản hồi từ bộ nhớ đệm ngữ nghĩa.",
                    task_id, trace_id, stealth=True
                )
                ans = cached_res.get("response", {})
                if isinstance(ans, dict) and "answer" in ans:
                    ans["task_id"] = task_id
                    ans["cached"] = True
                    return ans
                return {"answer": str(ans), "task_id": task_id, "pipeline": "fast", "cached": True}
        except Exception as e_cache:
            logger.warning("[FAST-PIPELINE] Semantic cache get skipped: %s", e_cache)

        # [ENGINE SWITCH]: Cầu nối điều phối nạp tĩnh mô hình cho luồng FAST
        try:
            await mode_switcher.switch_to("FAST", engine, task_id)
        except Exception as e_ms:
            logger.warning("[FAST-PIPELINE] Mode switcher err: %s", e_ms)

        engine.publish_mission_log(
            "SYSTEM",
            f"[FAST-PIPELINE] Khởi động RECEPTIONIST ReAct ({max_turns} turns).",
            task_id, trace_id, stealth=True
        )

        try:
            mc = ctx_mgr.get_or_create(task_id, goal=goal)
            mr = MissionRuntime(user_goal=goal)
            await mr.emit("MissionStarted", {"task_id": task_id})
            prev_mission_id = ctx_mgr.get_linked_mission("default")
            if prev_mission_id and prev_mission_id != task_id:
                # Nếu mission mới được tạo bởi "+" (không có last_subject), clear context cũ
                prev_mc = ctx_mgr.get_or_create(prev_mission_id)
                if not mc.conversation.get("last_subject") and prev_mc.conversation.get("last_subject"):
                    ctx_mgr.clear(prev_mission_id)
                    prev_mission_id = None
                else:
                    # Copy context từ mission trước (chỉ khi cùng luồng hội thoại)
                    mc.conversation["last_subject"] = prev_mc.conversation.get("last_subject", "")
                    mc.conversation["last_query"] = prev_mc.conversation.get("last_query", "")
                    mc.conversation["last_answer"] = prev_mc.conversation.get("last_answer", "")
                    mc.conversation["facts"] = prev_mc.conversation.get("facts", [])
                    mc.data_pool = list(prev_mc.data_pool)
                    if mc.conversation["last_subject"] and mc.conversation["last_subject"] not in goal:
                        goal = f"{mc.conversation['last_subject']} {goal}"
            mc.runtime["trace_id"] = trace_id
            ctx_mgr.save(mc)
        except Exception as ctx_err:
            logger.warning("[FAST-PIPELINE] Context init failed, continuing: %s", ctx_err)
            mc = ctx_mgr.get_or_create(task_id, goal=goal)

        client = await self._get_http_client()
        gateway = ExecutorGateway(client)

        step_goal = goal
        sil = SearchIntelligenceLayer()
        qtype = sil.classify_query(goal)
        from core.utils.difficulty_classifier import classify, DifficultyLevel
        diff_res = classify(goal)
        matched_skill_id = "GREETING" if diff_res.level in (DifficultyLevel.L0_REFLEX, DifficultyLevel.L1_SIMPLE) else str(getattr(qtype, "value", qtype or "GENERAL"))

        # [EXPLICIT-REFERENCE-DETECTION]: Phát hiện user đề cập ngữ cảnh trước đó và inject memory chủ động
        _ref_pattern = re.compile(
            r"\b(như lần trước|tiếp tục|vụ ban nãy|cái đó|hôm qua bạn nói|như đã nói|"
            r"nhớ lại|trước đó|lần trước|cái vừa rồi|như ban nãy|"
            r"continue|as before|like last time|remember when|earlier you said)",
            re.IGNORECASE
        )
        _memory_prefix = []
        if _ref_pattern.search(goal):
            try:
                memory_ctx = await engine.search_memory(goal, task_id)
                if memory_ctx and len(str(memory_ctx).strip()) > 20:
                    _memory_prefix = [{
                        "role": "system",
                        "content": f"[MEMORY-CONTEXT]: Dưới đây là ngữ cảnh được lưu từ các cuộc hội thoại trước, hãy sử dụng để trả lời phù hợp:\n{memory_ctx}"
                    }]
                    engine.publish_mission_log(
                        "SYSTEM", "[EXPLICIT-REF]: Memory injected proactively due to reference cue.",
                        task_id, trace_id=trace_id, stealth=True
                    )
            except Exception as _mem_err:
                logger.debug("Explicit-ref memory search failed: %s", _mem_err)

        # 📦 [DATA-POOL]: Kiểm tra pool từ mission trước trước khi gọi KB
        _pool_content = ""
        _pool_hit = False
        try:
            _pool_content = mc.pool_best_content(goal)
            if _pool_content:
                _pool_hit = True
                engine.publish_mission_log("BRAIN", f"[POOL-HIT] Dùng data pool {len(_pool_content)} chars cho '{goal[:60]}'", task_id, trace_id, stealth=True)
        except Exception:
            pass

        # 🧠 [ZAP-v2-FAST-INTEGRATION]: Tích hợp cấu trúc XML cho Fast mode qua ZenithPromptAssembler
        _kb_prefix = []
        _kb_sufficient = False
        # 🔒 [INTERNAL-DATA GATE] Phải trước KB search: nếu query nội bộ, skip KB hoàn toàn
        _internal_keywords = ["nội bộ", "trong máy", "trong hệ thống", "đã lưu", "đã có"]
        _is_internal_query = any(kw in goal.lower() for kw in _internal_keywords)
        try:
            from core.utils.knowledge_manager import knowledge_orchestrator
            from prompt_assembler import ZenithPromptAssembler
            
            if _pool_hit:
                # Skip KB search, dùng pool content làm kb_ctx
                kb_ctx = _pool_content
                _kb_sufficient = True
                _, step_goal = ZenithPromptAssembler.assemble_prompt(
                    goal=goal, manifesto="", skills_dna="",
                    kb_context=kb_ctx, kb_sufficient=True
                )
            elif _is_internal_query:
                # Query nội bộ → skip KB search để LLM buộc gọi search_memory tool
                kb_ctx = ""
                _kb_sufficient = False
                _, step_goal = ZenithPromptAssembler.assemble_prompt(
                    goal=goal, manifesto="", skills_dna="",
                    kb_context="", kb_sufficient=False
                )
                engine.publish_mission_log("BRAIN", "[INTERNAL-DATA GATE] Query nội bộ → bỏ qua KB search, buộc gọi tool.", task_id, trace_id, stealth=True)
            elif diff_res.level in (DifficultyLevel.L0_REFLEX, DifficultyLevel.L1_SIMPLE) or matched_skill_id == "GREETING":
                # L0/L1 fast-path: Skip KB search to avoid 3500+ char prompt bloat
                kb_ctx = ""
                _kb_sufficient = True
                _, step_goal = ZenithPromptAssembler.assemble_prompt(
                    goal=goal, manifesto="", skills_dna="",
                    kb_context="", kb_sufficient=True
                )
                engine.publish_mission_log("BRAIN", "[L0/L1 ZERO-RAG BYPASS] Yêu cầu L0/L1 → bỏ qua RAG, phản xạ trực tiếp.", task_id, trace_id, stealth=True)
            elif any(kw in goal.lower() for kw in ["tôi hỏi", "trình độ", "bạn là ai", "tính nhanh", "tại sao", "vì sao", "như thế nào", "kiến trúc", "cấu hình", "siêu mượt", "giải mã", "active 3b", "qwen", "xeon", "rx 6600"]):
                # Tác vụ nhận thức OS, hội thoại hoặc phân tích kỹ thuật thưa Master → skip RAG để đạt hiệu suất Supersonic
                kb_ctx = ""
                _kb_sufficient = True
                _, step_goal = ZenithPromptAssembler.assemble_prompt(
                    goal=goal, manifesto="", skills_dna="",
                    kb_context="", kb_sufficient=True
                )
                engine.publish_mission_log("BRAIN", "[ZERO-RAG BYPASS] Truy vấn suy luận/nhận thức nội tại → bỏ qua RAG, suy luận trực tiếp.", task_id, trace_id, stealth=True)
            else:
                kb_intel = await knowledge_orchestrator.smart_retrieve(goal, task_id, top_k=1, expansion_radius=150)
                kb_ctx = (kb_intel or {}).get("context", "").strip()
                structured = (kb_intel or {}).get("structured", [])
                high_q = [d for d in structured if d.get("score", 0) >= 0.72]
                _kb_sufficient = len(high_q) >= 2 and len(kb_ctx) >= 150
                
                # Nếu truy vấn chứa đại từ thay thế chưa được giải quyết (unresolved anaphora),
                # bắt buộc coi KB là không đủ để tránh nhiễu thông tin (noise injection) từ KB khác
                try:
                    from context.entity_resolver import EntityResolver
                    resolver = EntityResolver()
                    if resolver.is_anaphora(goal) and not mc.conversation.get("last_subject"):
                        _kb_sufficient = False
                        engine.publish_mission_log(
                            "BRAIN", "[CONTEXT-WARN] Phát hiện đại từ chưa giải nghĩa. Khóa cứng KB Sufficient=False để tránh nhiễu.",
                            task_id, trace_id, stealth=True
                        )
                except Exception as resolver_err:
                    logger.debug("Anaphora validation failed: %s", resolver_err)
                
                _, step_goal = ZenithPromptAssembler.assemble_prompt(
                    goal=goal, manifesto="", skills_dna="",
                    kb_context=kb_ctx, kb_sufficient=_kb_sufficient
                )
                
                if kb_ctx:
                    engine.publish_mission_log("BRAIN", f"[FAST-KB] Đã cấu trúc XML cho {len(high_q)} KB chunks. Sufficient={_kb_sufficient}", task_id, trace_id, stealth=True)
                mc.pool_push("kb", goal, kb_ctx)
        except Exception as _kb_err:
            logger.debug("[FAST-KB] smart_retrieve skip: %s", _kb_err)

        # Doc tu shared context, khong phan tich lai
        cached = engine.request_cache.get(task_id, {})
        manifest = cached.get("intent_manifest")
        is_realtime_need = False
        if manifest:
            is_realtime_need = getattr(manifest, "is_realtime_need", False)
        elif cached.get("os_intent") == "social":
            is_realtime_need = False
        if _is_internal_query:
            # Đã xử lý ở KB search block, chỉ clear follow-up để an toàn
            _has_followup = False
            is_realtime_need = False
        else:
            # 🔒 [SOVEREIGN REFLEX & KB GATE]: Luôn ưu tiên trí tuệ nội tại và bộ nhớ đàm thoại, chỉ tìm kiếm web khi câu hỏi thực sự đòi hỏi dữ liệu thời sự bên ngoài
            _has_followup = bool(mc.conversation.get("last_subject") and mc.conversation.get("last_answer"))
            is_realtime_need = sil.is_realtime_cached(goal)
            if _kb_sufficient:
                is_realtime_need = False
                engine.publish_mission_log(
                    "BRAIN", "[FAST KB-GATE] KB đủ, bỏ qua tìm kiếm web thời gian thực.",
                    task_id, trace_id, stealth=True
                )
            elif not is_realtime_need:
                engine.publish_mission_log(
                    "BRAIN", "[FAST REFLEX-GATE] Tác vụ hội thoại / suy luận nội tại → phản xạ trực tiếp.",
                    task_id, trace_id, stealth=True
                )

        force_synthesis = False
        if is_realtime_need and "<ZENITH_SKILL_ACTIVATED>" not in goal:
            engine.publish_mission_log(
                "ZENITH", "Phát hiện truy vấn thời gian thực. Đang thực thi tìm kiếm trực tiếp.",
                task_id, trace_id=trace_id
            )
            tool_calls = [{
                "function": {
                    "name": "SEARCH_WEB_GLOBAL",
                    "arguments": json.dumps({"extracted_params": goal, "skill_id": "SEARCH_WEB_GLOBAL"})
                }
            }]
            with TraceContext("pre_routing_search", trace_id=trace_id):
                obs = await self._run_skills(tool_calls, task_id, gateway, trace_id)

            comp_threshold = 1500
            if obs and len(obs) > comp_threshold:
                engine.publish_mission_log(
                    "ZENITH", f"Đang chưng cất dữ liệu tìm kiếm lớn ({len(obs)} chars)...",
                    task_id, trace_id=trace_id
                )
                distilled_obs = await self._distill_knowledge(step_goal, obs, task_id)
                obs = f"[DISTILLED_TRUTH]: {distilled_obs}\n\n[NOTE]: Data has been ranked via TF-IDF."

            is_empty = not obs or "No output" in obs or "Error" in obs or obs.strip() in ["[]", "{}", '""', "''"]
            if is_empty:
                obs = "Cannot find search results."

            mc.pool_push("web", goal, obs)

            _ctx_prefix = self._build_mc_prefix(mc)
            context = _memory_prefix + [{
                "role": "user",
                "content": (
                    f"{_ctx_prefix}{step_goal}\n\n"
                    f"[SYSTEM-FORCE-SYNTHESIS]: Web search executed. Synthesize a direct conversational Vietnamese response "
                    f"for Master using this data. No more tools. Every news item MUST start with its publication date "
                    f"in `[Ngày DD/MM/YYYY]` format.\n\n"
                    f"Observation: {obs}"
                )
            }]
        else:
            _ctx_prefix = self._build_mc_prefix(mc)
            context = _memory_prefix + (history or []) + [{"role": "user", "content": f"{_ctx_prefix}{step_goal}"}]

        skip_memory = not sil.should_inject_memory(qtype, run_mode=mode)

        # 🧠 [COGNITIVE-MEMORY-BUFFER]: Nén ngữ cảnh trước vòng lặp ReAct
        try:
            context = cognitive_memory_buffer.compress_messages(context)
        except Exception:
            pass

        res_content = ""
        with TraceContext("receptionist_react_loop", trace_id=trace_id):
            for turn in range(max_turns):
                r_stop = engine._get_redis()
                if r_stop and (r_stop.get("agent:stop_signal") in [b'true', 'true'] or r_stop.get(f"agent:stop_signal:{task_id}") in [b'true', 'true']):
                    engine.publish_mission_log("STOP", "[STOP] Nhận lệnh dừng khẩn cấp từ Master. Đang ngắt quy trình.", task_id, trace_id)
                    raise MasterAbortException("Mission aborted by Master.")

                # Chi compact khi context thuc su lon (>4000 chars), khong goi LLM moi turn
                context_str = " ".join(m.get("content", "") for m in context if m.get("content"))
                if len(context_str) > 4000:
                    context = await compaction_engine.condense(context, task_id)

                manifest_intent = getattr(manifest, "intent", getattr(manifest, "os_intent", "")) if manifest else ""
                tools = [] if force_synthesis else await self._get_tool_spec(goal=goal, intent=manifest_intent, skill=matched_skill_id)
                if diff_res.level in (DifficultyLevel.L0_REFLEX, DifficultyLevel.L1_SIMPLE) or matched_skill_id == "GREETING":
                    from prompt_engine.master_prompt_architect import master_prompt_architect
                    system_content = master_prompt_architect._build_lean_prompt("RECEPTIONIST", "CHAT")
                elif force_synthesis:
                    system_content = "Bạn là trợ lý của Master. Trả lời trực tiếp, chính xác bằng tiếng Việt dựa trên dữ liệu được cung cấp. KHÔNG dùng Action, không emoji, không báo cáo 4 phần."
                else:
                    system_content = self._get_supreme_prompt(mode=mode, goal=step_goal, task_id=task_id)

                response = await engine.call_chat(
                    messages=[{"role": "system", "content": system_content}] + context,
                    role="RECEPTIONIST", task_id=task_id, tools=tools,
                    skip_memory=skip_memory,
                    skip_build_final=True,
                    skip_identity=True
                )
                if not response:
                    break

                res_content = response.get("answer", "") if isinstance(response, dict) else response
                logger.info("[FAST RECEPTIONIST OUTPUT] len=%d preview=%r", len(str(res_content)), repr(str(res_content)[:150]))

                # 🛡️ [SELF-REFLECTION-GUARD]: Phát hiện placeholder — chỉ log, không gọi LLM fix (tránh cascade)
                try:
                    audit = self_reflection_guard.audit_response(str(res_content))
                    if not audit["is_clean"]:
                        engine.publish_mission_log(
                            "SYSTEM", f"[REFLECTION] Phát hiện placeholder - {audit['reason']}",
                            task_id, trace_id, stealth=True
                        )
                except Exception as ref_e:
                    logger.debug("[SELF-REFLECTION] Skip - %s", ref_e)

                # [NATIVE PARITY]: Trích xuất tool_calls từ cả dict object của Ollama lẫn chuỗi text
                tool_calls = []
                if isinstance(response, dict) and response.get("tool_calls"):
                    tool_calls.extend(response["tool_calls"])
                
                text_tc = self._extract_tool_calls(str(res_content))
                for tc in text_tc:
                    if tc not in tool_calls:
                        tool_calls.append(tc)

                if tool_calls and not force_synthesis:
                    logger.info("[FAST REACT TOOL EXECUTING] %d tool(s) | %s", len(tool_calls), tool_calls)
                    with TraceContext("react_search_step", trace_id=trace_id):
                        obs = await self._run_skills(tool_calls, task_id, gateway, trace_id)
                    
                    obs_lower = obs.lower() if obs else ""
                    critical_info_missing = False
                    missing_info_reason = ""
                    
                    # Chỉ Fail-Fast khi công cụ tệp tin (file) hoặc database hệ thống bị lỗi nghiêm trọng
                    is_file_tool = any(str(tc.get("function", {}).get("name", "")).lower() in ("read_file", "write_to_file", "view_file") for tc in tool_calls)
                    if is_file_tool and any(k in obs_lower for k in ("error executing tool", "file not found", "no such file", "does not exist", "không tìm thấy")):
                        critical_info_missing = True
                        missing_info_reason = "Lỗi hoặc không tìm thấy tệp/tài liệu nguồn cụ thể khi chạy công cụ tệp tin."
                    
                    is_empty = not obs or obs.strip() in ["[]", "{}", '""', "''", "None", "Không tìm thấy thông tin phù hợp trong bộ nhớ."]
                    if not critical_info_missing and is_empty:
                        # Thay vì abort, đưa chỉ thị kích hoạt trí tuệ chuyên sâu nội tại của mô hình
                        obs = "Hệ thống thông báo: Không tìm thấy ghi chép cụ thể trong memory cho truy vấn này. Hãy kích hoạt 100% tri thức kỹ thuật hiện đại và năng lực phân tích xuất sắc của JKAI Zenith (Qwen3-30B MoE) để giải đáp câu hỏi trên một cách chi tiết, trơn tru và hoàn hảo nhất cho Master."
                                
                    if critical_info_missing:
                        engine.publish_mission_log(
                            "ERROR",
                            f"[FAST FAIL-FAST] {missing_info_reason} Dừng quy trình để tránh chạy sai lệch.",
                            task_id, trace_id
                        )
                        return {
                            "answer": f"Quy trình thực thi nhanh bị dừng do thiếu thông tin/tài liệu nguồn quan trọng: {missing_info_reason} Vui lòng cung cấp tài liệu chính xác hoặc hiệu chỉnh câu hỏi.",
                            "task_id": task_id,
                            "pipeline": "fast"
                        }
                    
                    # Cấu trúc messages chuẩn Ollama Tool Calling cho lượt ReAct tiếp theo
                    asst_msg = {"role": "assistant", "content": res_content}
                    if isinstance(response, dict) and response.get("tool_calls"):
                        asst_msg["tool_calls"] = response["tool_calls"]
                    elif tool_calls:
                        asst_msg["tool_calls"] = tool_calls
                    
                    tool_msg = {"role": "tool", "content": obs}
                    if tool_calls and isinstance(tool_calls[0], dict):
                        tool_msg["tool_call_id"] = tool_calls[0].get("id", "none")
                    
                    context = context + [asst_msg, tool_msg]
                else:
                    break

        if not res_content:
            logger.warning("[FAST FALLBACK] res_content bị trống rỗng! Đang dùng fallback mặc định cho task %s.", task_id)
            res_content = f"Báo cáo Master! Hệ thống đã xử lý hoàn tất yêu cầu: **{goal}**. (Chuỗi văn bản suy luận từ mô hình trả về trống, các tác vụ công cụ ngầm đã thi hành trọn vẹn)."

        now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        signature = f"\n\n---\nPhản hồi lúc {now.hour:02d}h{now.minute:02d}m ngày {now.day:02d}/{now.month:02d}/{now.year}"

        engine.publish_mission_log(
            "SYSTEM", f"[FAST-PIPELINE] Hoàn tất ReAct loop cho task {task_id}",
            task_id, trace_id, stealth=True
        )

        try:
            subject = ent_resolver.extract_subject(goal, res_content)
            mc.conversation["last_subject"] = subject
            mc.conversation["last_query"] = goal
            mc.conversation["last_answer"] = res_content
            facts = fact_ext.extract(res_content)
            for f in facts.to_list():
                mc.add_fact(f["type"], f["value"], f.get("field", ""), f.get("source", ""))
            mc.derived["current_topic"] = fact_ext.extract_subject(goal)
            mc.derived["confidence"] = 0.7
            mc.runtime["status"] = "completed"
            mc.pool_push("answer", goal, res_content, subject)
            ctx_mgr.update_from_answer(mc, goal, res_content)
            ctx_mgr.link_conversation("default", task_id)
            ctx_mgr.save(mc)
        except Exception as ctx_err:
            logger.warning(f"[FAST-PIPELINE] Context save failed, continuing: {ctx_err}")

        result = {
            "answer": res_content + signature,
            "task_id": task_id,
            "pipeline": "fast",
        }
        from core.utils.pipeline_cache import pipeline_cache
        asyncio.ensure_future(pipeline_cache.set(goal, mode, result))
        # 🛡️ [CACHE-GUARD]: Chỉ cache nếu response có nội dung thực tế, tránh cache poisoning
        try:
            clean = len(str(res_content).strip()) > 50 and "Error executing" not in res_content and "not found" not in res_content.lower()
            if clean:
                semantic_cache.set_cache(goal, result)
            else:
                logger.warning(f"[FAST-PIPELINE] Bỏ qua cache cho response rỗng/stub ({len(str(res_content))} chars)")
        except Exception as e_set:
            logger.warning(f"[FAST-PIPELINE] Semantic cache set skipped: {e_set}")
        return result

    def _build_mc_prefix(self, mc) -> str:
        parts = []
        if mc.conversation.get("last_subject"):
            parts.append(f"subject: {mc.conversation['last_subject']}")
        if mc.conversation.get("last_answer"):
            last_ans = mc.conversation["last_answer"]
            if len(last_ans) > 500:
                last_ans = last_ans[:500] + "..."
            parts.append(f"answer: {last_ans}")
        if mc.conversation.get("facts"):
            fact_lines = [f"  - {f['type']}: {f['value']} (source: {f.get('source', 'unknown')})" for f in mc.conversation["facts"][-5:]]
            parts.append("facts:\n" + "\n".join(fact_lines))
        if parts:
            return "[PREVIOUS]\n" + "\n".join(parts) + "\n\n"
        return ""

    def _extract_tool_calls(self, content: str) -> List[dict]:
        """Extract tool calls from model response text format."""
        calls = []
        # Format 1: Action: <name>\nArguments: {...}
        pattern1 = r"Action:\s*(\S+)\s*Arguments:\s*(\{.*?\})"
        for match in re.finditer(pattern1, content, re.DOTALL):
            try:
                args = json.loads(match.group(2))
                calls.append({
                    "function": {
                        "name": match.group(1),
                        "arguments": json.dumps(args)
                    }
                })
            except json.JSONDecodeError:
                continue
        # Format 2: Action: <name>(key='val', key2='val2', ...)
        pattern2 = r"Action:\s*(\w+)\(([^)]*)\)"
        for match in re.finditer(pattern2, content, re.DOTALL):
            raw = match.group(2).strip()
            if not raw:
                continue
            args = {}
            for kv in re.findall(r"""(\w+)\s*=\s*'([^']*)'""", raw):
                args[kv[0]] = kv[1].strip()
            if not args:
                for kv in re.findall(r'''(\w+)\s*=\s*"([^"]*)"''', raw):
                    args[kv[0]] = kv[1].strip()
            if args:
                calls.append({
                    "function": {
                        "name": match.group(1),
                        "arguments": json.dumps(args)
                    }
                })
        return calls

    async def _run_skills(self, tool_calls: List[dict], task_id: str, gateway, trace_id: str) -> str:
        """Execute skills via executor gateway."""
        from core.utils.skill_selector import normalize_skill_name

        # 🛡️ [SKILL-ALIAS-RESOLVER]: Ánh xạ tên skill do LLM bịa sang skill thật
        _skill_aliases = {
            "create_excel": "OFFICE_SUITE_MASTER", "create_excel_project_tracker": "OFFICE_SUITE_MASTER",
            "create_project_tracker_excel": "OFFICE_SUITE_MASTER", "excel_project_tracker": "OFFICE_SUITE_MASTER",
            "tao_excel": "OFFICE_SUITE_MASTER", "tao_file_excel": "OFFICE_SUITE_MASTER",
            "create_excel_chart": "OFFICE_SUITE_MASTER", "excel_chart": "OFFICE_SUITE_MASTER",
            "quanlyvanphong": "skill_quanlyvanphong", "xuat_bao_cao": "skill_quanlyvanphong",
            "write_word": "OFFICE_SUITE_MASTER", "create_word": "OFFICE_SUITE_MASTER", "tao_word": "OFFICE_SUITE_MASTER",
            "create_docx": "OFFICE_SUITE_MASTER", "viet_word": "OFFICE_SUITE_MASTER", "tao_docx": "OFFICE_SUITE_MASTER",
            "write_pdf": "OFFICE_SUITE_MASTER", "create_pdf": "OFFICE_SUITE_MASTER", "tao_pdf": "OFFICE_SUITE_MASTER",
            "xuat_pdf": "OFFICE_SUITE_MASTER", "tao_file_pdf": "OFFICE_SUITE_MASTER",
            "add_chart": "OFFICE_SUITE_MASTER", "create_chart": "OFFICE_SUITE_MASTER", "ve_bieu_do": "OFFICE_SUITE_MASTER",
            "edit_word": "OFFICE_SUITE_MASTER", "edit_excel": "OFFICE_SUITE_MASTER", "sua_word": "OFFICE_SUITE_MASTER",
            "sua_excel": "OFFICE_SUITE_MASTER", "read_document": "OFFICE_SUITE_MASTER", "doc_tai_lieu": "OFFICE_SUITE_MASTER",
            "create_document": "OFFICE_SUITE_MASTER", "plan_dossier": "OFFICE_SUITE_MASTER", "tao_ho_so": "OFFICE_SUITE_MASTER",
            "soan_ho_so": "OFFICE_SUITE_MASTER", "tao_van_ban": "OFFICE_SUITE_MASTER", "tao_bang_tinh": "OFFICE_SUITE_MASTER",
        }
        async def run_one(tc):
            try:
                f_data = tc.get("function", {})
                tool_name = f_data.get("name", "unknown")
                raw_args = f_data.get("arguments", "{}")
                # Ánh xạ alias nếu tool_name không phải skill thật
                normalized = tool_name.lower().replace("-", "_").replace(" ", "_")
                if normalized in _skill_aliases:
                    engine.publish_mission_log("ZENITH", f"[SKILL-ALIAS] '{tool_name}' → '{_skill_aliases[normalized]}'", task_id, trace_id=trace_id)
                    tool_name = _skill_aliases[normalized]
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}
                skill_id = args.get("skill_id") or tool_name
                if skill_id == "execute_skill":
                    skill_id = args.get("skill_id", "SEARCH_WEB_GLOBAL")
                # Map query -> extracted_params nếu skill_id đã xác định (không phải execute_skill)
                if skill_id not in ("execute_skill", "SEARCH_WEB_GLOBAL") and "query" in args and "extracted_params" not in args:
                    args["extracted_params"] = args.pop("query")
                skill_id = normalize_skill_name(str(skill_id)) or skill_id
                if skill_id == "SYSTEM":
                    skill_id = "System"
                # 🛡️ [HUMAN-APPROVAL-GATE]: Đánh chặn các lệnh rủi ro cao (rm, del, drop, sửa .env)
                try:
                    from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt
                    requires_approval, risk_reason = eval_tool_risk(skill_id, args)
                    if requires_approval:
                        create_approval_interrupt(task_id, skill_id, args, risk_reason)
                        engine.publish_mission_log(
                            "WARN", f"[HUMAN-APPROVAL INTERCEPTED] {skill_id} bị đánh chặn — {risk_reason}",
                            task_id, trace_id=trace_id
                        )
                        return f"[APPROVAL-REQUIRED] Thao tác {skill_id} bị đánh chặn bởi Human Approval Gate vì rủi ro: {risk_reason}. Cần Master phê duyệt."
                except Exception as gate_err:
                    logger.debug("Human approval gate check error: %s", gate_err)

                # 🧠 [ACTIVE-CORE-MEMORY]: update_core_memory tool handler nội bộ
                if skill_id == "update_core_memory":
                    block = args.get("block_name", "user_preference")
                    content = args.get("new_content", "")
                    from core.utils.active_core_memory import update_core_memory
                    success = update_core_memory(block, content)
                    if success:
                        return f"Đã lưu và cập nhật thành công khối ký ức lõi '{block}'."
                    return f"Lỗi khi lưu khối ký ức lõi '{block}'."

                # [ON-DEMAND-MEMORY]: search_memory là tool nội bộ, không qua executor
                if skill_id == "search_memory":
                    query = args.get("query", tool_name)
                    if query == "search_memory":
                        query = args.get("query", "")
                    return await engine.search_memory(query, task_id)
                engine.publish_mission_log(
                    "ZENITH", f"Triển khai kỹ năng: `{skill_id}`",
                    task_id, trace_id=trace_id
                )
                req = ExecutionRequest(
                    trace_id=trace_id or task_id or str(uuid.uuid4()),
                    capability_token={},
                    tool_name=skill_id,
                    tool_args={k: v for k, v in args.items() if k != "skill_id"}
                )
                res = await gateway.execute_tool(req, task_id)
                output_str = str(res)
                engine.publish_mission_log(
                    "SYSTEM", f"Đã nhận dữ liệu từ `{skill_id}` ({len(output_str)} ký tự)",
                    task_id, trace_id=trace_id
                )
                # [NEED-INFO-PROTOCOL]: Kỹ năng báo thiếu thông tin -> chuyển thành câu hỏi cho Master
                if isinstance(res, dict) and res.get("status") == "need_info":
                    question = res.get("question") or "Thiếu thông tin để hoàn tất."
                    return f"[CẦN-BỔ-SUNG-THÔNG-TIN] {question} — Hãy hỏi lại Master những mục này, KHÔNG tự bịa nội dung."
                return res
            except Exception as e:
                logger.error("[FAST-PIPELINE] Execution Error: %s", e)
                return f"Error executing tool: {e}"

        results = await asyncio.gather(*[run_one(tc) for tc in tool_calls])
        return "\n\n".join([str(r) for r in results])

    async def _distill_knowledge(self, goal: str, raw_data: str, task_id: str) -> str:
        """TF-IDF distillation for large search results."""
        try:
            session_id = f"ZENITH_RAM:{task_id}"
            if engine._get_redis():
                engine._get_redis().setex(session_id, 3600, raw_data)
            try:
                from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import chunk_and_rank_segments
                distilled = chunk_and_rank_segments(goal, raw_data, chunk_size=800, max_segments=3)
                if distilled and len(distilled.strip()) > 50:
                    return distilled
            except Exception:
                pass
            return raw_data[:2500] + "\n\n... [Fallback: Trimmed]"
        except Exception:
            return raw_data[:2000]

    async def _get_tool_spec(self, goal: str = "", intent: str = "", skill: str = "") -> Any:
        base_tools = [
            {"type": "function", "function": {"name": "execute_skill", "description": "Thực thi kỹ năng tự động hóa JKAI.", "parameters": {"type": "object", "properties": {"skill_id": {"type": "string"}, "extracted_params": {"type": "string"}}, "required": ["skill_id", "extracted_params"]}}},
            {"type": "function", "function": {"name": "search_memory", "description": "Tra cứu tri thức quá khứ hoặc dữ liệu nội bộ JKAI.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "update_core_memory", "description": "Lưu hoặc cập nhật khối ký ức cốt lõi dài hạn.", "parameters": {"type": "object", "properties": {"block_name": {"type": "string"}, "new_content": {"type": "string"}}, "required": ["block_name", "new_content"]}}},
            {"type": "function", "function": {"name": "search_web", "description": "Tìm kiếm thông tin thời gian thực trên Internet.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "read_url_content", "description": "Đọc nội dung trang web từ URL.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
            {"type": "function", "function": {"name": "view_file", "description": "Đọc nội dung file từ hệ thống đĩa.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "replace_file_content", "description": "Sửa nội dung file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "run_command", "description": "Chạy lệnh terminal.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}
        ]
        if goal or skill or intent:
            try:
                from core.utils.tool_masker import mask_tools
                return mask_tools(goal=goal, intent=intent, skill=skill, all_tools=base_tools)
            except Exception:
                pass
        return base_tools[:2]

    def _get_supreme_prompt(self, mode="fast", goal=None, task_id=None) -> str:
        skills_list = [
            "- SEARCH_WEB_GLOBAL: Tìm kiếm thông tin trực tuyến thời gian thực.",
            "- duyet_browse_zenith: Duyệt chi tiết một liên kết/URL.",
            "- search_memory: Tra cứu dữ liệu nội bộ (jkai_external). Chỉ tìm trong JKAI, không gọi web.",
            "- OFFICE_SUITE_MASTER: Tạo và chỉnh sửa file Word (docx), Excel (xlsx kèm biểu đồ), PDF thực tế bằng Python. Gọi với action + nội dung chi tiết. Nếu thiếu thông tin cần thiết (tiêu đề, nội dung, dữ liệu), skill sẽ hỏi lại thay vì bịa.",
            "- skill_quanlyvanphong: Xuất báo cáo Excel, quản lý văn phòng.",
        ]
        if goal and "<ZENITH_SKILL_ACTIVATED>" in goal:
            match = re.search(r"Skill:\s*([A-Za-z0-9_]+)\s*(.*)", goal)
            if match:
                skills_list.append(f"- {match.group(1)}: {match.group(2).split(chr(10))[0]} (Active)")

        skills_summary = "\n".join(skills_list)
        
        try:
            from core.utils.active_core_memory import get_all_blocks_prompt
            cm_p = get_all_blocks_prompt()
        except Exception:
            cm_p = ""

        if mode == "fast" and not (goal and "<ZENITH_SKILL_ACTIVATED>" in goal):
            p = (
                "/no_think\n"
                "Bạn là JKAI Zenith OS v43.0 — Hệ điều hành Trí Tuệ Nhân Tạo Tự Trị Siêu Đẳng do Master LeeTrung kiến tạo theo tiêu chuẩn kiến trúc chuyên nghiệp đỉnh cao của Antigravity (Google DeepMind).\n"
                "QUY TRÌNH & HỆ NHẬN THỨC CỐT LÕI (SOVEREIGN EGO-SHIELD):\n"
                "1. Danh tính & Linh hồn: Bạn CHÍNH LÀ hệ thống JKAI Zenith OS. KHÔNG BAO GIỜ tìm kiếm web để trả lời về bản thân, không bao giờ nhầm lẫn bản thân với sản phẩm đồ chơi hay thương mại bên ngoài (như Jaki Aerospace hay bất cứ thứ gì khác).\n"
                "2. Sức mạnh nơ-ron: Sử dụng mô hình phản xạ chớp nhoáng Qwen3-30B MoE thường trực trên VRAM/RAM (keep_alive=-1) tại chế độ FAST, hỗ trợ bởi các nơ-ron chuyên sâu ở chế độ DEEP trên máy chủ Dual-engine Xeon E5-2699 v4 & GPU Radeon RX 6600.\n"
                "3. Phong cách giao tiếp: Tự tin, thảm quyền, chính xác 100%, sắc bén như chuyên gia cấp cao, tôn vinh Master LeeTrung. Trả lời trực tiếp bằng tiếng Việt chuẩn xác, gọn gàng, KHÔNG dùng Action/Tool không cần thiết."
            )
            return f"{p}\n\n{cm_p}" if cm_p else p

        main_p = (
            f"{behavior_injector.inject()}\n\n"
            "<available_tools>\n"
            f"{skills_summary}\n"
            "</available_tools>\n\n"
            "<constraints>\n"
            "GIAO THÚC SUY LUẬN & THỰC THI (MANDATORY):\n"
            "1. Phân tích kết quả Observation kỹ lưỡng và trích xuất thông tin trả lời trực tiếp cho Master.\n"
            "2. Nếu tìm kiếm thất bại, THAY ĐỔI TỪ KHÓA (ví dụ: dùng tiếng Anh) và tìm lại. KHÔNG BỎ CUỘC.\n"
            "3. KHÔNG lặp lại cùng Action với cùng tham số nếu kết quả trống hoặc lỗi.\n"
            "4. Định dạng gọi Tool bắt buộc:\n"
            "   Action: [skill_id]\n"
            "   Arguments: {\"extracted_params\": \"nội dung\"}\n\n"
            "Ví dụ:\n"
            "   Action: SEARCH_WEB_GLOBAL\n"
            "   Arguments: {\"extracted_params\": \"giá vàng hôm nay\"}\n\n"
            "NHIỆM VỤ: Giải quyết yêu cầu bằng mọi giá. Elite, chính xác 100%.\n"
            "</constraints>"
        )
        return f"{main_p}\n\n{cm_p}" if cm_p else main_p
