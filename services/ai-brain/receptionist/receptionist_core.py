import re
import json
import asyncio
from core.utils.engine import engine
from dispatcher import Dispatcher
from core.utils.policy_engine import PolicyEngine
from receptionist.executor_gateway import ExecutionRequest

class Receptionist:
    """
    ⚡ JKAI Zenith: RECEPTIONIST SOUL (THIN ORCHESTRATOR)
    Phiên bản kiến trúc Composition - Zero Trust Kernel.
    """
    def __init__(self, container, critic=None, assimilator=None):
        self.container = container
        self.critic = critic
        self.assimilator = assimilator
        self.dispatcher = Dispatcher()

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    async def handle_task(self, goal, task_id, agent_soul="agent_receptionist.md", assigned_skills=None, images=None, history=None, mode="fast"):
        """🧠 [SUPREME-STRATEGIST]: Xử lý tác vụ với kiến trúc Gateway Composition thưa Master."""
        pipeline_mode = "FAST_PIPELINE" if mode.lower() in ["fast", "auto"] else "DEEP_PIPELINE"
        self._log("ZENITH", f"🧠 📡 Đang phân tích chỉ thị với chế độ [{pipeline_mode}] (Input mode: {mode.upper()})...", task_id)

        clean_goal = re.sub(r'\s*\((Web|Tele|Manual|API)\)$', '', goal.strip())

        # 1. 🛡️ BẢO MẬT & ĐÁNH CHẶN CẤP ĐỘ CAO
        auth_res = await self.container.auth_interceptor.check_sovereign_intercept(clean_goal, task_id)
        if auth_res: return auth_res

        validation = await self.container.auth_interceptor.preflight_validation(clean_goal, task_id)
        if not validation["valid"]:
            self._log("ZENITH", f"⚠️ [PRE-FLIGHT REJECTED]: {validation['reason']}", task_id)
            return {"answer": validation["reason"], "task_id": task_id, "sensitive": False}

        # 2. ⚡ GIAO THỨC SIÊU LỆNH (COMMAND INTERCEPTOR)
        if clean_goal.startswith("/"):
            parts = clean_goal.split()
            cmd = parts[0]
            args = " ".join(parts[1:])
            return await self.container.command_router.process_command(cmd, args, task_id)

        # 3. 👁️ GIAO THỨC THỊ GIÁC (Tạm thời bỏ qua hoặc tích hợp sau)
        visual_input = ""
        
        # 4. 🧠 BỘ NÃO TRUNG TÂM (DISPATCHER) & MÔ HÌNH ZERO-TRUST (POLICY ENGINE)
        manifest = await self.dispatcher.dispatch(clean_goal, task_id)
        
        context = {"source": "web"}
        policy_res = PolicyEngine.evaluate(manifest, context)
        
        # Ghi log Cognitive Trace
        trace = {
            "intent": manifest.intent,
            "action_type": manifest.action_type.name,
            "confidence": manifest.confidence,
            "risk": manifest.risk,
            "planner": manifest.requires_planner,
            "reasoning": manifest.reasoning
        }
        self._log("COGNITIVE TRACE", json.dumps(trace), task_id)

        if isinstance(policy_res, dict) and policy_res.get("action") == "DENY":
            self._log("ZENITH", f"🛡️ [POLICY DENIED]: {policy_res.get('reason')}", task_id)
            return {"answer": f"⛔ Yêu cầu bị từ chối: {policy_res.get('reason')}", "task_id": task_id, "sensitive": True}
        
        cap_token = policy_res
        if not cap_token.verify():
            return {"answer": "⛔ Token xác thực bị làm giả hoặc hết hạn.", "task_id": task_id, "sensitive": True}

        # 5. ĐIỀU HƯỚNG TỚI GATEWAY TƯƠNG ỨNG
        if manifest.requires_planner:
            res = await self.container.planner_gateway.request_plan(goal, images, history, task_id, cap_token.__dict__)
            return {"answer": res["msg"], "task_id": task_id}
            
        elif manifest.skill and manifest.intent != "GREETING" and manifest.confidence >= 0.70:
            self._log("ZENITH", f"⚡ [REFLEX-MATCH]: Auto execute `{manifest.skill}`. Bypass Planner.", task_id)
            req = ExecutionRequest(
                trace_id=manifest.trace_id,
                capability_token=cap_token.__dict__,
                tool_name=manifest.skill,
                tool_args={"query": clean_goal}
            )
            # Thực thi qua Executor Gateway
            obs = await self.container.executor_gateway.execute_tool(req, task_id)
            
            # Tóm tắt kết quả
            self._log("SUMMARIZER", "📝 [T6]: Ban Thư Ký đang soạn Báo cáo từ phản xạ...", task_id)
            
            summary_prompt = (
                f"[MISSION DATA]\n"
                f"Objective: {goal}\n"
                f"Observation: {obs}\n\n"
                "══════════════════════════════════════════\n"
                "Bạn là Elite Secretary của JKAI Zenith. Viết báo cáo rõ ràng, chuyên nghiệp bằng tiếng Việt từ dữ liệu trên.\n"
                "- Dùng gạch đầu dòng và in đậm từ khóa.\n"
                "- Tránh văn mẫu sáo rỗng.\n"
                "- Trả lời trực tiếp vào trọng tâm."
            )
            
            try:
                final_answer = await engine.call_chat(
                    messages=[{"role": "system", "content": "Bạn là Thư ký Zenith."}, {"role": "user", "content": summary_prompt}],
                    role="SUMMARIZER",
                    task_id=task_id
                )
                if isinstance(final_answer, dict) and "answer" in final_answer:
                    final_answer = final_answer["answer"]
            except Exception as e:
                self._log("ERROR", f"Lỗi tóm tắt: {e}", task_id)
                final_answer = f"✅ [FAST_PIPELINE]: Kích hoạt phản xạ với kỹ năng `{manifest.skill}` hoàn tất.\n\nKết quả thô:\n{str(obs)[:1000]}"

            return {
                "answer": final_answer,
                "task_id": task_id,
                "sensitive": False,
                "mode": "fast"
            }

        elif manifest.requires_llm or manifest.confidence < 0.65 or manifest.intent == "UNKNOWN":
            self._log("ZENITH", f"🧠 [AGENTIC-LOOP]: Kích hoạt Não Bộ Tự Trị (ReAct Loop) với Native Tool Calling.", task_id)
            
            # Khởi tạo ngữ cảnh kỹ năng cho LLM
            skills_context = await self.dispatcher._get_skills_context()
            
            system_prompt = (
                "# 🧠 JKAI ZENITH: GIAO THỨC ĐẶC VỤ TỰ TRỊ (AUTONOMOUS GATEWAY)\n\n"
                "Bạn là JKAI Zenith - Quản gia Tối thượng của Master LeeTrung.\n"
                "Nhiệm vụ của bạn là suy nghĩ, phân tích và giải quyết triệt để yêu cầu của Master.\n"
                "QUY TẮC SỬ DỤNG CÔNG CỤ (ReAct Loop):\n"
                "1. Ưu tiên hàng đầu: Tự dùng công cụ (ví dụ tra IP để lấy vị trí, tra thư mục để tìm file) thay vì lười biếng hỏi lại Master.\n"
                "2. Hãy gọi công cụ `execute_skill` liên tục cho đến khi tìm ra đáp án cuối cùng.\n"
                "3. Khi đã có đủ thông tin, hãy tổng hợp và báo cáo mạch lạc cho Master bằng tiếng Việt chuyên nghiệp.\n"
                "4. [BƯỚC 5 - FALLBACK]: NẾU VÀ CHỈ NẾU tất cả các công cụ đều thất bại, hoặc bạn thực sự không có cách nào tự suy luận ra thông tin bị thiếu, hãy dùng cú pháp `[CLARIFY]: <câu hỏi>` để hỏi lại Master một cách tinh tế.\n\n"
                f"DANH SÁCH KỸ NĂNG KHẢ DỤNG:\n{skills_context[:4000]}"
            )
            
            session_id = self.container.memory_gateway.get_session_id(task_id)
            if not history:
                history = self.container.memory_gateway.load_history(task_id)
                
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(self.container.memory_gateway.clean_history(history))
            messages.append({"role": "user", "content": goal})
            
            execute_skill_tool = {
                "type": "function",
                "function": {
                    "name": "execute_skill",
                    "description": "Thực thi một kỹ năng từ hệ thống. Trích xuất tất cả các tham số hoặc chuỗi truy vấn cần thiết.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_id": {"type": "string", "description": "Tên hoặc ID của kỹ năng (Ví dụ: 'skill_weather', '27', ...)"},
                            "extracted_params": {"type": "string", "description": "Câu lệnh truy vấn hoặc JSON chứa tham số cho kỹ năng (VD: 'Tìm tin tức AI mới nhất' hoặc '{\"location\": \"Hanoi\"}')"}
                        },
                        "required": ["skill_id", "extracted_params"]
                    }
                }
            }
            
            loop_count = 0
            MAX_LOOPS = 5
            final_answer = ""
            
            while loop_count < MAX_LOOPS:
                loop_count += 1
                self._log("ZENITH", f"🔄 [ReAct-Loop] Vòng lặp suy nghĩ thứ {loop_count}...", task_id, stealth=True)
                
                response = await engine.call_chat(
                    messages=messages,
                    role="RECEPTIONIST",
                    task_id=task_id,
                    tools=[execute_skill_tool]
                )
                
                if not isinstance(response, dict):
                    final_answer = str(response)
                    break
                    
                if "tool_calls" in response and response["tool_calls"]:
                    # Model decided to call tools!
                    tool_calls = response["tool_calls"]
                    messages.append({"role": "assistant", "content": response.get("answer", ""), "tool_calls": tool_calls})
                    
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        func_name = func.get("name")
                        args_str = func.get("arguments", "{}")
                        try:
                            args = json.loads(args_str)
                        except:
                            args = {"extracted_params": args_str}
                            
                        if func_name == "execute_skill":
                            skill_id = args.get("skill_id", "UNKNOWN")
                            params = args.get("extracted_params", "")
                            
                            self._log("ZENITH", f"⚙️ Đang kích hoạt kỹ năng [{skill_id}] với tham số: {params}", task_id)
                            
                            req = ExecutionRequest(
                                trace_id=manifest.trace_id,
                                capability_token=cap_token.__dict__,
                                tool_name=skill_id,
                                tool_args={"query": params}
                            )
                            obs = await self.container.executor_gateway.execute_tool(req, task_id)
                            
                            # Cắt bớt Observation nếu quá dài
                            obs_str = str(obs)
                            if len(obs_str) > 2000: obs_str = obs_str[:2000] + "...[TRUNCATED]"
                            
                            messages.append({
                                "role": "tool",
                                "name": func_name,
                                "content": obs_str,
                                "tool_call_id": tc.get("id", "call_xyz")
                            })
                else:
                    # No tool calls, we have the final answer!
                    final_answer = response.get("answer", "")
                    break
                    
            if not final_answer:
                final_answer = "Thưa Master, tôi đã cố gắng tra cứu công cụ nhưng xảy ra lỗi nội bộ ở vòng lặp suy nghĩ."
                
            return {"answer": final_answer, "task_id": task_id, "sensitive": False}

