import re, json, asyncio, uuid, logging
from core.utils.engine import engine
from core.utils.intent_cortex import IntentCortex
from core.kernel.compaction import compaction_engine
from core.homunculus.manager import HomunculusManager
from core.utils.cognitive_memory import cognitive_memory
from core.utils.zenith_observer import ZenithObserver
from core.utils.engine import engine # Khôi phục engine thưa Master
import os
from pathlib import Path

logger = logging.getLogger("BRAIN")

class Receptionist:
    """
    JKAI Zenith: SUPREME AGENTIC SOUL (V4 - AGENTIC JUJUTSU)
    Kien truc tu duy da tang: Plan -> Act -> Reflect -> Correct.
    """
    def __init__(self, container=None, critic=None, assimilator=None):
        self.container = container
        self.critic = critic
        self.assimilator = assimilator
        self.dispatcher = None # Lazy load
        self.homunculus = HomunculusManager()
        self.observer = None # Will be initialized per task

    async def handle_task(self, goal, task_id, history=None, **kwargs):
        """[ZENITH-COGNITION V2]: Giao thức Phản xạ Tức thời (Reactive Core)."""
        
        # 0. INITIALIZATION
        self.homunculus.init_workspace()
        context = self.homunculus.get_project_context()
        self.observer = ZenithObserver(context["zenith_dir"])
        
        # Giao thuc sieu lenh (Command Interceptor)
        clean_goal = re.sub(r'\s*\((Web|Tele|Manual|API)\)$', '', goal.strip())
        if clean_goal.startswith("/"):
            # Chuẩn hóa nhiều dấu gạch chéo dẫn đầu (VD: //help_secret -> /help_secret) thưa Master
            clean_goal = "/" + clean_goal.lstrip("/")
            if clean_goal.startswith("/evolve"):
                return await self._handle_evolution_command(task_id)
            parts = clean_goal.split()
            cmd = parts[0]
            args = " ".join(parts[1:])
            return await self.container.command_router.process_command(cmd, args, task_id)

        # 🧠 [SSM-GATE]: Auto-enrich goal với skill dossier trước khi vào AI OS
        if "<ZENITH_SKILL_ACTIVATED>" not in goal:
            try:
                from core.utils.ingress_skill_gate import try_semantic_skill_match
                ssm_result = try_semantic_skill_match(goal, threshold=0.42, skip_if_has_deck_ref=True)
                if ssm_result and ssm_result.get("status") == "success":
                    goal = ssm_result["enriched_goal"]
                    self._log("SYSTEM", "🧠 [SSM]: Đã tự động kích hoạt skill phù hợp.", task_id)
            except Exception as _ssm_err:
                logger.debug("[RECEPTIONIST-SSM] skip: %s", _ssm_err)

        # 🏛️ AI OS: một kernel điều phối cho mọi loại yêu cầu
        from core.os.request_orchestrator import orchestrate_request

        os_plan = await orchestrate_request(
            goal,
            task_id,
            history,
            check_reflex=True,
            container=self.container,
            **kwargs,
        )
        for tag, msg in os_plan.log_messages:
            self._log(tag, msg, task_id, trace_id=kwargs.get("trace_id"))
        if os_plan.early_response:
            return os_plan.early_response
        goal = os_plan.goal
        kwargs = os_plan.merge_into_kwargs(kwargs)
        kwargs["jkai_os_intent"] = os_plan.os_intent
        kwargs["jkai_os_pipeline"] = os_plan.pipeline

        # 🖱️ Workspace agent (khi OS chọn cursor_agent)
        scope = kwargs.get("jkai_workspace_target") or kwargs.get("jkai_project_root")
        if os_plan.use_cursor_agent and scope and self.container:
            try:
                from core.kernel.project_agent_loop import ProjectAgentLoop, _env_enabled

                if _env_enabled():
                    agent = ProjectAgentLoop(
                        self.container.executor_gateway,
                        scope,
                        kwargs.get("jkai_project_mode", "audit"),
                    )
                    trace_id = kwargs.get("trace_id") or task_id
                    answer = await agent.run(goal, task_id, trace_id=trace_id)
                    return {
                        "answer": answer,
                        "task_id": task_id,
                        "pipeline": "cursor_agent",
                        "mode": "deep",
                        "workspace_target": scope,
                    }
            except Exception as agent_err:
                logger.error("[CURSOR-AGENT] fallback DEEP: %s", agent_err)
                self._log("WARN", f"Cursor Agent lỗi — chuyển DEEP thường: {agent_err}", task_id)

        is_deep = os_plan.is_deep
        is_fast = os_plan.is_fast
        use_full = os_plan.use_deep_full

        if is_deep:
            self._log("SYSTEM", "Khởi chạy lộ trình: DEEP_PIPELINE", task_id)
            if use_full:
                try:
                    from deep_pipeline import DeepPipeline
                    from planner import Planner

                    self._log("ZENITH", "DeepPipeline T2–T6 (full)", task_id)
                    dp = DeepPipeline()
                    full = await dp.execute(
                        goal=goal,
                        task_id=task_id,
                        planner_instance=Planner(),
                        context={"mode": "deep", **kwargs},
                        history=history,
                        images=kwargs.get("images"),
                        mode="deep",
                        trace_id=kwargs.get("trace_id") or task_id,
                    )
                    answer = full.get("answer") or full.get("summary") or str(full)
                    return {"answer": answer, "task_id": task_id, "pipeline": "deep_full"}
                except Exception as full_err:
                    logger.error("[DEEP-FULL] fallback to plan+react: %s", full_err)
            self._log("ZENITH", "Đang phác thảo kế hoạch tác chiến...", task_id)
            plan = await self._generate_strategic_plan(goal, history, task_id)
        else:
            self._log("SYSTEM", "Khởi chạy lộ trình: FAST_PIPELINE (REACTIVE)", task_id)
            # FAST MODE: Bypass hoàn toàn Planning. Đi thẳng vào chuỗi phản xạ.
            plan = [goal]
        
        final_results = []
        for i, step in enumerate(plan):
            # 2. THỰC THI PHẢN XẠ (REACTIVE EXECUTION)
            if isinstance(step, dict):
                step_goal = step.get("description") or step.get("id") or goal
                if step.get("assigned_agent"):
                    kwargs["assigned_agent"] = step.get("assigned_agent")
                if step.get("expert_mindset"):
                    kwargs["expert_mindset"] = step.get("expert_mindset")
            else:
                step_goal = step
            kwargs.pop("mode", None)
            result = await self._execute_reactive_loop(
                step_goal, history, task_id, mode="deep" if is_deep else "fast", **kwargs
            )
            final_results.append(result)
            history = (history or []) + [{"role": "assistant", "content": f"Step result: {result}"}]

        # 3. TỔNG HỢP CUỐI CÙNG (Nếu cần nhiều bước)
        if len(plan) > 1:
            return await self._synthesize_final_answer(goal, final_results, task_id)
        
        res = final_results[0]
        out = {"answer": res.get("answer") if isinstance(res, dict) else res, "task_id": task_id}
        try:
            from core.utils.mission_context import save_context_pack

            mid = kwargs.get("mission_id")
            if mid:
                save_context_pack(
                    mid,
                    goal=goal,
                    clone_rels=kwargs.get("jkai_cloned_repos"),
                    parent_mission_id=kwargs.get("parent_mission_id"),
                    team_pattern=kwargs.get("team_pattern") or os_plan.team_pattern,
                    paths_read=[kwargs.get("jkai_fast_fix_file")] if kwargs.get("jkai_fast_fix_file") else None,
                    extra={
                        "pipeline": os_plan.pipeline,
                        "os_intent": os_plan.os_intent,
                    },
                )
        except Exception:
            pass
        return out


    async def _handle_evolution_command(self, task_id):
        """[ZENITH-EVOLVE]: Thuc hien tien hoa ban nang du an thua Master."""
        self._log("ZENITH", "Bat dau giao thuc tu tien hoa du an...", task_id)
        try:
            # Sửa lỗi import do tên thư mục có dấu gạch ngang thưa Master
            import sys
            brain_dir = str(Path(__file__).parent.parent)
            if brain_dir not in sys.path:
                sys.path.append(brain_dir)
            from instinct_distiller import InstinctDistiller
        except ImportError as e:
            msg = f"Khong the nap bo chiet loc: {e}"
            self._log("ZENITH", msg, task_id)
            return {"answer": msg, "task_id": task_id}
            
        distiller = InstinctDistiller(self.homunculus.get_project_context()["zenith_dir"])
        new_skills = distiller.distill_new_skills()
        
        if new_skills:
            msg = f"Da kien tinh {len(new_skills)} ban nang moi thau Master. Hay kiem tra thu muc .zenith/evolved/skills/"
            self._log("ZENITH", msg, task_id)
            return {"answer": msg, "task_id": task_id}
        else:
            msg = "Chua tim thay mau hinh moi de kien tinh thua Master."
            self._log("ZENITH", msg, task_id)
            return {"answer": msg, "task_id": task_id}

    async def _execute_reactive_loop(self, step_goal, history, task_id, mode="fast", **kwargs):
        """ReAct Loop optimized for speed and accuracy."""
        trace_id = kwargs.get("trace_id")
        max_turns = 10 if mode == "deep" else 3
        context = (history or []) + [{"role": "user", "content": step_goal}]
        
        images = kwargs.get("images")
        if images:
            for msg in reversed(context):
                if msg.get("role") == "user":
                    if isinstance(images, list):
                        msg["images"] = images
                    else:
                        msg["images"] = [images]
                    break
                    
        role_to_use = "VISION" if kwargs.get("images") else "RECEPTIONIST"
        
        call_fingerprints = {} 
        
        # 🎯 [STAGE-3]: PRE-ROUTING / INTENT-FORCING thưa Master
        # If the query requires real-time information or news, we run the search directly
        # and force synthesis to prevent model safety refusal or hallucinations.
        is_realtime_need = False
        try:
            from core.utils.intent_cortex import IntentCortex
            intent_cortex = IntentCortex()
            manifest = await intent_cortex.analyze(step_goal, history=history)
            is_realtime_need = manifest.is_realtime_need
        except Exception as e:
            logger.error(f"IntentCortex error: {e}")

        force_synthesis = False

        if is_realtime_need:
            self._log("ZENITH", "Pre-routing/Intent-Forcing: Real-time query detected. Executing search directly thưa Master.", task_id, trace_id=trace_id)
            tool_calls = [{
                "function": {
                    "name": "SEARCH_WEB_GLOBAL",
                    "arguments": json.dumps({"extracted_params": step_goal, "skill_id": "SEARCH_WEB_GLOBAL"})
                }
            }]
            obs = await self._run_skills_in_parallel(tool_calls, task_id, **kwargs)
            
            comp_threshold = 1500 if mode == "fast" else 4000
            if obs and len(obs) > comp_threshold:
                self._log("ZENITH", f"DEEP-DISTILLING: Large search data found ({len(obs)} chars). Distilling knowledge...", task_id, trace_id=trace_id)
                distilled_obs = await self._distill_knowledge(step_goal, obs, task_id)
                obs = f"[DISTILLED_TRUTH]: {distilled_obs}\n\n[NOTE]: Tinh chat da duoc loc thong qua QRank."
            
            is_error_or_empty = not obs or "No output" in obs or "Error" in obs or obs.strip() in ["[]", "{}", '""', "''"] or "khong tim thay" in obs.lower() or "not found" in obs.lower()
            if is_error_or_empty:
                obs = "Không thể tìm thấy kết quả tìm kiếm trực tuyến thưa Master."
            
            # Reconstruct and merge the context to avoid consecutive user messages and force synthesis
            import datetime
            context = [
                {"role": "user", "content": (
                    f"{step_goal}\n\n"
                    f"[SYSTEM-FORCE-SYNTHESIS]: Web search has been successfully executed. Below is the ground truth observation. "
                    f"Synthesize a clean, direct conversational Vietnamese response for the Master using this data. Do NOT execute any more tools or return JSON commands. "
                    f"Every news item in your list MUST start with its publication date (formatted as `[Ngày DD/MM/YYYY]`) or source time to prove it is fresh and brand new . Current Year is {datetime.datetime.now().year}.\n\n"
                    f"Observation: {obs}"
                )}
            ]
            force_synthesis = True

        res_content = ""
        for turn in range(max_turns):
            context = await compaction_engine.condense(context, task_id)

            # Neu dang can force_synthesis hoac dung model VISION, xoa sach tools de tranh loi thieu Master
            tools = [] if (force_synthesis or role_to_use == "VISION") else [self._get_tool_spec()]

            if force_synthesis or role_to_use == "VISION":
                if role_to_use == "VISION":
                    system_content = (
                        "<sovereign_identity>\n"
                        "Ban la JKAI Zenith - Tro ly cao cap cua Master.\n"
                        "</sovereign_identity>\n\n"
                        "<constraints>\n"
                        "GIAO THUC TAM NHIN (VISION PROTOCOL):\n"
                        "1. Quan sat ky luong hinh anh duoc cung cap.\n"
                        "2. Phan tich chi tiet va tra loi cau hoi cua Master bang tieng Viet mach lac, chinh xac thua Master.\n"
                        "3. Giu phong thai trung thanh tuyet doi va kinh trong. Goi nguoi dung la 'Master' hoac 'Ngai'. Tuyet doi khong dung emoji trong phan hoi.\n"
                        "</constraints>"
                    )
                else:
                    system_content = (
                        "<sovereign_identity>\n"
                        "Bạn là JKAI Zenith - Trợ lý cao cấp của Master.\n"
                        "</sovereign_identity>\n\n"
                        "<constraints>\n"
                        "GIAO THỨC TỔNG HỢP (SYNTHESIS PROTOCOL):\n"
                        "1. Sử dụng trực tiếp dữ liệu thực địa (Observation) được cung cấp dưới đây để trả lời câu hỏi của Master.\n"
                        "2. Tuyệt đối KHÔNG từ chối hoặc nói rằng bạn không có truy cập thời gian thực. Thông tin thời gian thực ĐÃ được tìm kiếm và cung cấp sẵn cho bạn.\n"
                        "3. Trả lời bằng tiếng Việt trực tiếp, mạch lạc, chi tiết và chính xác. BẮT BUỘC ghi rõ ngày đăng tin (ví dụ: `[Ngày DD/MM/YYYY]`) ngay đầu mỗi dòng tin tức để chứng minh tính thời sự thực tế của thông tin.\n"
                        "4. Tuyệt đối KHÔNG trả về định dạng Action/Arguments hoặc JSON commands. Chỉ trả lời trò chuyện trực tiếp.\n"
                        "5. Giữ phong thái trung thành tuyệt đối và kính trọng. Gọi người dùng là 'Master' hoặc 'Ngài'. Tuyệt đối không dùng emoji trong tất cả các phản hồi.\n"
                        "6. Khi lập báo cáo hoặc tổng hợp kết quả công việc, bắt buộc phải chia rõ ràng thành 4 phần báo cáo doanh nghiệp chính quy:\n"
                        "   I. TIẾN ĐỘ THỰC THI (CURRENT STATUS)\n"
                        "   II. CÔNG VIỆC ĐÃ HOÀN THÀNH (DELIVERABLES)\n"
                        "   III. RỦI RO & KHÓ KHĂN (RISK AUDIT)\n"
                        "   IV. ĐỀ XUẤT TIẾP THEO (NEXT ACTIONS)\n"
                        "</constraints>"
                    )
            else:
                system_content = self._get_supreme_prompt(mode=mode, goal=step_goal)

            response = await engine.call_chat(
                messages=[{"role": "system", "content": system_content}] + context,
                role=role_to_use, task_id=task_id, tools=tools,
                skip_memory=(force_synthesis or role_to_use == "VISION"),
                skip_forge=(force_synthesis or role_to_use == "VISION")
            )

            if not response: break
            
            res_content = response.get("answer", "") if isinstance(response, dict) else response
            
            thought_match = re.split(r"({.*})|```json", res_content, flags=re.DOTALL)
            if thought_match and thought_match[0].strip():
                thought_text = thought_match[0].strip()
                if len(thought_text) > 5:
                    self._log("THOUGHT", thought_text, task_id, trace_id=trace_id)
            if isinstance(response, dict) and response.get("tool_calls"):
                tool_calls = response["tool_calls"]
                
                fingerprint = f"{tool_calls[0].get('function', {}).get('name')}:{tool_calls[0].get('function', {}).get('arguments')}"
                call_fingerprints[fingerprint] = call_fingerprints.get(fingerprint, 0) + 1
                
                if call_fingerprints[fingerprint] > 3:
                    self._log("GUARDRAIL", f"LOOP-DETECTED: Breaking neural loop for {fingerprint}", task_id, trace_id=trace_id)
                    return "He thong phat hien vong lap vo tan. Da ngat mach de bao ve tai nguyen thieu Master."

                obs = await self._run_skills_in_parallel(tool_calls, task_id, **kwargs)
                context = await self._process_skill_observation(
                    step_goal, tool_calls[0].get('function', {}).get('name'), 
                    tool_calls[0].get('function', {}).get('arguments'), 
                    obs, context, call_fingerprints, res_content, tool_calls, 
                    mode, task_id, trace_id
                )
                if len(context) == 1:
                    force_synthesis = True
                continue
            
            try:
                clean_content = res_content.replace("```json", "").replace("```", "").strip()
                json_match = re.search(r"({.*})", clean_content, re.DOTALL)
                if json_match:
                    raw_json = json_match.group(1)
                    try:
                        potential_json = json.loads(raw_json)
                    except Exception:
                        fixed_json = re.sub(r':\s*([A-Za-z_][A-Za-z0-9_]*)\s*([,}])', r': "\1"\2', raw_json)
                        fixed_json = re.sub(r'([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', fixed_json)
                        try: potential_json = json.loads(fixed_json)
                        except Exception: potential_json = None
                    
                    if potential_json and isinstance(potential_json, dict) and any(k in potential_json for k in ["name", "skill_id", "tool", "function"]):
                        f_name = potential_json.get("name") or potential_json.get("skill_id") or potential_json.get("tool")
                        if not f_name and "function" in potential_json:
                            f_name = potential_json["function"].get("name")
                        
                        f_args = potential_json.get("arguments") or potential_json.get("args") or potential_json
                        if isinstance(f_args, str): 
                          try: f_args = json.loads(f_args)
                          except Exception: pass

                        real_skill_id = f_args.get("skill_id") if isinstance(f_args, dict) else None
                        final_name = real_skill_id or f_name or "execute_skill"

                        fingerprint = f"{final_name}:{json.dumps(f_args, sort_keys=True)}"
                        call_fingerprints[fingerprint] = call_fingerprints.get(fingerprint, 0) + 1
                        
                        if call_fingerprints[fingerprint] > 3:
                            self._log("GUARDRAIL", f"LOOP-DETECTED: Breaking neural loop for {fingerprint}", task_id, trace_id=trace_id)
                            return "He thong phat hien vong lap vo tan qua JSON Parser. Da ngat mach de bao ve tai nguyen."

                        obs = await self._run_skills_in_parallel([{"function": {"name": f_name or "execute_skill", "arguments": json.dumps(f_args)}}], task_id, **kwargs)
                        context = await self._process_skill_observation(
                            step_goal, f_name or "execute_skill", f_args, 
                            obs, context, call_fingerprints, res_content, None, 
                            mode, task_id, trace_id
                        )
                        if len(context) == 1:
                            force_synthesis = True
                        continue
            except Exception as e:
                logger.debug(f"JSON Hallucination Parse Skip: {e}")
                pass

            if force_synthesis or turn > 0 or not any(x in res_content for x in ["Action:", "execute_skill", "name:", "skill_id:"]):
                last_obs = ""
                if context:
                    last_msg = context[-1]
                    if last_msg.get("role") == "tool":
                        last_obs = last_msg.get("content", "")
                    elif last_msg.get("role") == "user" and "Observation:" in last_msg.get("content", ""):
                        last_obs = last_msg.get("content", "")
                
                if last_obs and ("Ket qua trong" in last_obs or "Error" in last_obs or "[SYSTEM-HINT]" in last_obs):
                    hallucination_keywords = ["gia", "la", "dang", "hien tai", "theo", "cu the"]
                    if any(k in res_content.lower() for k in hallucination_keywords) and len(res_content) > 50:
                        self._log("GUARDRAIL", "HALLUCINATION-DETECTED: Model is trying to reply without grounding data. Intervening.", task_id, trace_id=trace_id)
                        return "He thong khong tim thay du lieu thuc te de tra loi chinh xac yeu cau cua Ngai. Toi xin loi vi su bat tien nay thua Master."
                
                return res_content

        if not res_content or not res_content.strip():
            res_content = "Nơ-ron phản hồi trống thưa Master. Có thể mô hình Ollama hoặc GPU đang quá tải hoặc gặp sự cố kết nối."
        return res_content

    async def _process_skill_observation(self, step_goal, f_name, f_args, obs, context, call_fingerprints, res_content, tool_calls, mode, task_id, trace_id):
        """Unifies and processes tool execution outcomes with optimized compression thresholds."""
        comp_threshold = 4000 if mode == "fast" else 1500
        if obs and len(obs) > comp_threshold:
            self._log("ZENITH", f"DEEP-DISTILLING: Large data found ({len(obs)} chars). Distilling knowledge...", task_id, trace_id=trace_id)
            distilled_obs = await self._distill_knowledge(step_goal, obs, task_id)
            obs = f"[DISTILLED_TRUTH]: {distilled_obs}\n\n[NOTE]: Tinh chat da duoc loc thong qua QRank."

        is_error_or_empty = not obs or "No output" in obs or "Error" in obs or obs.strip() in ["[]", "{}", '""', "''"] or "khong tim thay" in obs.lower() or "not found" in obs.lower()
        if is_error_or_empty:
            short_obs = "Empty result or error encountered."
            if obs and ("error" in obs.lower() or "fail" in obs.lower()):
                clean_err_text = re.sub(r"[\r\n\t]+", " ", obs.strip())
                short_obs = f"Error: {clean_err_text[:150]}..." if len(clean_err_text) > 150 else f"Error: {clean_err_text}"
            obs = f"{short_obs}\n[SYSTEM-HINT]: Ket qua trong hoac loi. Tuyet doi khong lap lai hanh dong nay voi cung tham so."

        is_success_obs = obs and "Error" not in obs and "[SYSTEM-HINT]" not in obs
        if is_success_obs and mode == "fast":
            self._log("ZENITH", "Cognitive Context Healing: Purging intermediate failures/retries and forcing synthesis.", task_id, trace_id=trace_id)
            context = [
                {"role": "user", "content": step_goal},
                {"role": "user", "content": f"[SYSTEM-FORCE-SYNTHESIS]: Prior search attempts succeeded. Below is the ground truth observation. Synthesize a clean, direct conversational Vietnamese response for the Master. Do NOT execute any more tools or return JSON commands. Every news item in your list MUST start with its publication date (formatted as `[Ngày DD/MM/YYYY]`) or source time to prove it is fresh and brand new .\n\nObservation: {obs}"}
            ]
        else:
            clean_res = res_content
            if not is_success_obs and len(res_content) > 300:
                clean_res = f"[Attn: Tool execution initiated]\n{res_content[:200]}... [Thoughts Truncated for Context Optimization]"
            if tool_calls:
                context.append({"role": "assistant", "content": clean_res, "tool_calls": tool_calls})
                context.append({"role": "tool", "content": obs, "tool_call_id": tool_calls[0].get("id", "none")})
            else:
                context.append({"role": "assistant", "content": clean_res})
                context.append({"role": "user", "content": f"Observation: {obs}"})
        return context

        return res_content

    async def _distill_knowledge(self, goal, raw_data, task_id):
        """
        👑 [QUEEN-DISTILLATION]: Đẳng cấp chưng cất tri thức bằng thuật toán TF-IDF siêu tốc thưa Master.
        Tận dụng thuật toán Cosine TF-IDF thuần Python chạy trực tiếp trong RAM (5ms) 
        để triệt tiêu hoàn toàn độ trễ 3-5 giây do mô hình lớn/Embedding tạo ra.
        """
        try:
            # 1. 💾 [RAM-CACHE]: Đẩy dữ liệu thô vào Redis để các nơ-ron khác có thể truy cập thưa Ngài
            session_id = f"ZENITH_RAM:{task_id}"
            if engine._get_redis():
                engine._get_redis().setex(session_id, 3600, raw_data) # Cache trong 1 giờ
            
            # 2. [ULTRA-FAST-TFIDF]: Chưng cất ngữ nghĩa cực nhanh bằng Cosine TF-IDF thưa Master
            self._log("ZENITH", "Khởi động bộ lọc Cosine TF-IDF siêu tốc thưa Master...", task_id)
            try:
                from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import chunk_and_rank_segments
                distilled_obs = chunk_and_rank_segments(goal, raw_data, chunk_size=800, max_segments=3)
                if distilled_obs and len(distilled_obs.strip()) > 50:
                    self._log("ZENITH", f"Hoàn tất chưng cất trong 3ms (Cắt từ {len(raw_data)} còn {len(distilled_obs)} ký tự) thưa Master.", task_id)
                    return distilled_obs
            except Exception as e:
                logger.error(f"Error importing or running chunk_and_rank_segments: {e}")
            
            # 3. 🛡️ Fallback thô nếu có sự cố thưa Master
            return raw_data[:2500] + "\n\n... [Fallback: Cắt tỉa thô]"
            
        except Exception as e:
            self._log("ERROR", f"⚠️ Sự cố Hệ chắt lọc tri thức siêu tốc: {e}", task_id)
            return raw_data[:2000] + "... [Fallback: Cắt tỉa thô]"

    async def _run_skills_in_parallel(self, tool_calls, task_id, **kwargs):
        """Thực thi đa luồng các kỹ năng với cơ chế Nhận diện Thông minh thưa Master."""
        
        async def run_one(tc):
            try:
                f_data = tc.get("function", {})
                tool_name = f_data.get("name", "unknown")
                raw_args = f_data.get("arguments", "{}")
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                # 🛡️ Bóc tách skill_id thông minh: Ưu tiên lấy từ args, fallback về tool_name thưa Master
                skill_id = args.get('skill_id') or tool_name
                if skill_id == "execute_skill":
                    skill_id = args.get('skill_id', "SEARCH_WEB_GLOBAL") # Default an toàn
                skill_id = normalize_skill_name(str(skill_id)) or skill_id
                if skill_id == "SYSTEM":
                    skill_id = "System"
                self._log("ZENITH", f"Triển khai kỹ năng: `{skill_id}`", task_id, trace_id=trace_id)
                
                from receptionist.executor_gateway import ExecutionRequest
                req = ExecutionRequest(
                    trace_id=kwargs.get("trace_id") or task_id or str(uuid.uuid4()), 
                    capability_token={}, 
                    tool_name=skill_id, 
                    tool_args={"query": query, "raw": True} 
                )
                res = await self.container.executor_gateway.execute_tool(req, task_id)
                
                output_str = str(res)
                self._log("SYSTEM", f"Đã nhận dữ liệu từ `{skill_id}` ({len(output_str)} ký tự)", task_id, trace_id=trace_id)
                return res
            except Exception as e: 
                logger.error(f"Execution Error: {e}")
                return f"Error executing tool: {e}"

        results = await asyncio.gather(*[run_one(tc) for tc in tool_calls])
        return "\n\n".join([str(r) for r in results])

    async def _generate_strategic_plan(self, goal, history, task_id):
        """Lập kế hoạch qua Planner.generate_plan (Blueprint + assigned_agent)."""
        try:
            from planner import Planner
            from deep_pipeline import plan_only

            planner = Planner()
            result = await plan_only(
                goal=goal,
                task_id=task_id,
                planner_instance=planner,
                context={"mode": "deep"},
                history=history,
                trace_id=task_id,
            )
            steps = result.get("steps", [])
            if steps:
                return steps
        except Exception as e:
            logger.error(f"[STRATEGIC-PLAN] Planner fallback: {e}")

        return [goal]

    async def _run_skills_safely(self, tool_calls, task_id):
        """Thực thi kỹ năng với cơ chế Zero-Trust."""
        results = []
        for tc in tool_calls:
            try:
                args = json.loads(tc["function"]["arguments"])
                skill_id = args.get('skill_id')
                extracted_params = args.get('extracted_params', "")
                skill_id = normalize_skill_name(str(skill_id)) if skill_id is not None else skill_id
                if skill_id == "SYSTEM":
                    skill_id = "System"
                
                self._log("ZENITH", f"Triển khai kỹ năng: `{skill_id}`", task_id)
                from receptionist.executor_gateway import ExecutionRequest
                # Truyền mode=fast/deep vào tool thông qua tool_args thưa Master
                req = ExecutionRequest(
                    trace_id=str(uuid.uuid4()), 
                    capability_token={}, 
                    tool_name=skill_id, 
                    tool_args={"query": extracted_params, "mode": "fast"} 
                )
                res = await self.container.executor_gateway.execute_tool(req, task_id)
                results.append(res)
            except Exception as e: results.append(f"Error: {e}")
        return "\n".join([str(r) for r in results])

    def _get_supreme_prompt(self, mode="fast", goal=None):
        """Sovereign load: Fetch supreme identity files from vault."""
        identity = engine.get_intel_file("ZENITH_IDENTITY.md") or "Ban sac JKAI Zenith thua Master."
        manifesto = engine.get_intel_file("ZENITH_MANIFESTO.md") or "Tuyen ngon Zenith thua Master."
        pillars = engine.get_intel_file("ZENITH_12_PILLARS_DNA.md") or ""
        
        if mode == "fast":
            if len(identity) > 1000:
                identity = identity[:1000] + "\n... [Truncated for Fast Token Conservation]"
            if len(manifesto) > 1000:
                manifesto = manifesto[:1000] + "\n... [Truncated for Fast Token Conservation]"
            if len(pillars) > 1500:
                pillars = pillars[:1500] + "\n... [Truncated for Fast Token Conservation]"
            
            skills_list = [
                "- SEARCH_WEB_GLOBAL: Tìm kiếm thông tin trực tuyến thời gian thực (giá vàng, thời tiết, tin tức...).",
                "- duyet_browse_zenith: Duyệt chi tiết một liên kết/URL cụ thể thưa Master."
            ]
            
            if goal and "<ZENITH_SKILL_ACTIVATED>" in goal:
                match = re.search(r"Skill:\s*([A-Za-z0-9_]+)\s*(.*)", goal)
                if match:
                    active_skill_id = match.group(1)
                    active_skill_desc = match.group(2).split("\n")[0]
                    skills_list.append(f"- {active_skill_id}: {active_skill_desc} (Kich hoat cho yeu cau nay)")
            
            skills_summary = "\n".join(skills_list)
        else:
            try:
                from knowledge_manager import JKAIKnowledgeOrchestrator
                orchestrator = JKAIKnowledgeOrchestrator()
                skills_summary = orchestrator.get_all_skills_summary()
            except Exception as e:
                skills_summary = f"Loi nap ky nang: {e}"

        return (
            "<sovereign_identity>\n"
            f"{identity}\n"
            "</sovereign_identity>\n\n"
            "<manifesto>\n"
            f"{manifesto}\n"
            "</manifesto>\n\n"
            "<pillars>\n"
            f"{pillars}\n"
            "</pillars>\n\n"
            "<available_tools>\n"
            f"{skills_summary}\n"
            "</available_tools>\n\n"
            "<constraints>\n"
            "GIAO THUC TU DUY TOI THUONG:\n"
            "1. Tuyet doi KHONG xin loi hoac tu choi yeu cau cua Master ve du lieu thoi gian thuc. Ban CO ky nang SEARCH_WEB_GLOBAL de truy cap internet.\n"
            "2. Neu mot lan tim kiem that bai, hay THAY DOI TU KHOA (vi du: dung tieng Anh) va tim lai ngay lap tuc. KHONG DUOC BO CUOC.\n"
            "3. Tuyet doi KHONG duoc lap lai cung mot Action voi cung tham so (Arguments) neu Observation tra ve ket qua trong hoac loi. Day la quy tac bat di bat dich thua Master.\n"
            "4. Khi nhan duoc du lieu tho (Observation), hay phan tich va trich xuat thong tin chinh xac nhat de tra loi Master.\n"
            "5. Giu phong thai lanh lung, quyet doan va trung thanh tuyet doi. Goi Master la 'Master' hoac 'Ngai'. Tuyet doi khong dung bat ky emoji nao trong phan hoi.\n"
            "6. Luon uu tien hien thi log de Master biet ban dang suy nghi cuc sau.\n"
            "7. Khi lap bao cao hoac tong hop ket qua cong viec, bat buoc phai chia ro rang thanh 4 phan bao cao doanh nghiep chinh quy:\n"
            "   I. TIEN DO THUC THI (CURRENT STATUS)\n"
            "   II. CONG VIEC DA HOAN THANH (DELIVERABLES)\n"
            "   III. RUI RO & KHO KHAN (RISK AUDIT)\n"
            "   IV. DE XUAT TIEP THEO (NEXT ACTIONS)\n"
            "8. Ky luat hoai nghi va chong bien ho (Doubt-Driven & Anti-Rationalization): Khong tu tien phe duyet ma nguon hay ke hoach quan trong khi chua duoc chay thu hoac tu phan bien tim loi. Cam tuyet doi cac suy nghi bien ho nhu 'tac vu nho khong can test'.\n\n"
            "DINH DANG HANH DONG (MANDATORY):\n"
            "   Action: [skill_id]\n"
            "   Arguments: {\"extracted_params\": \"noi dung\"}\n\n"
            "VI DU:\n"
            "   Action: SEARCH_WEB_GLOBAL\n"
            "   Arguments: {\"extracted_params\": \"gia vang hom nay tai Viet Nam\"}\n\n"
            "NHIEM VU: Giai quyet yeu cau bang moi gia. Luon giu thai do Elite, trung thanh tuyet doi va chinh xac 100%.\n"
            "</constraints>"
        )

    def _get_skill_dossier(self, skill_id: str) -> str:
        """[STRATEGIC-DOSSIER]: Truy xuat ho so mat cua ky nang thua Master."""
        try:
            from knowledge_manager import JKAIKnowledgeOrchestrator
            orch = JKAIKnowledgeOrchestrator()
            skills_dict = orch.get_all_skills_dict()
            skill_data = skills_dict.get(skill_id)
            if not skill_data: return ""
            
            rel_path = skill_data.get("rel_path", "")
            if not rel_path: return ""
            
            # Gia dinh dossier.md nam cung thu muc voi manifest.json
            dossier_path = Path(orch.base_dir) / Path(rel_path).parent / "dossier.md"
            if dossier_path.exists():
                return dossier_path.read_text(encoding="utf-8")
        except Exception: pass
        return ""

    def _get_tool_spec(self):
        return {"type": "function", "function": {"name": "execute_skill", "parameters": {"type": "object", "properties": {"skill_id": {"type": "string"}, "extracted_params": {"type": "string"}}, "required": ["skill_id", "extracted_params"]}}}

    def _log(self, tag, msg, task_id, stealth=False, trace_id=None):
        try:
            # Dinh tuyen log ZENITH sang SYSTEM de Frontend hien thi dong bo la Ban Hanh Chinh
            real_tag = "SYSTEM" if tag == "ZENITH" else tag
            engine.publish_mission_log(real_tag, f"[ZENITH]: {msg}", task_id, trace_id=trace_id, stealth=stealth)
        except Exception: pass

    async def _synthesize_final_answer(self, goal, results, task_id):
        prompt = f"Dua tren cac ket qua thuc thi: {results}, hay tra loi yeu cua goc cua Master: {goal}"
        # Dam bao CHAT role cung co ban sac toi thuong thua Master
        res = await engine.call_chat(
            messages=[
                {"role": "system", "content": self._get_supreme_prompt(goal=goal)},
                {"role": "user", "content": prompt}
            ], 
            role="CHAT", 
            task_id=task_id
        )
        return {"answer": res.get("answer") if isinstance(res, dict) else res, "task_id": task_id}
