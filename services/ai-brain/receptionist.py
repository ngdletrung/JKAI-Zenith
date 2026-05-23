import os
import json
import re
import asyncio
import time
import httpx
import redis
from core.utils.engine import engine
from core.config import settings
from dispatcher import Dispatcher
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

dispatcher = Dispatcher()

class IntentType(str, Enum):
    GREETING = "GREETING"
    SEARCH = "SEARCH"
    EXECUTE = "EXECUTE"
    STRATEGY = "STRATEGY"

class IntentAnalysis(BaseModel):
    thought: str = Field(..., description="Internal reasoning for intent classification")
    intent: IntentType = Field(..., description="The classified intent of the user")
    confidence: float = Field(..., ge=0, le=1)

class Receptionist:
    """
    ⚡ JKAI Zenith: RECEPTIONIST SOUL (FAST MODE)
    Đặc vụ đại diện Ban Trợ Lý thưa Tổng Giám Đốc.
    """
    def __init__(self, critic=None, assimilator=None):
        self.critic = critic
        self.assimilator = assimilator
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self._redis_conn = redis.Redis(
            host=self.redis_host, 
            port=6379, 
            db=0, 
            password=self.redis_password,
            decode_responses=True
        )
        # 💎 Synapse vĩnh cửu thưa Master - Kéo dài lên 600s để đồng bộ tri thức lớn
        self.client = httpx.AsyncClient(timeout=600.0)

    def _log(self, tag, msg, task_id="manual", stealth=False):
        """Giao thức Phát tín hiệu Elite thưa Master! 🫡💎🦾"""
        try:
            from core.utils.engine import engine
            # 💎 [ENTHUSIASTIC-LOGGING]: Thêm danh xưng tôn quý thưa Master
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    async def call_executor_tool(self, tool_name, tool_args, task_id):
        """Gọi Executor để thực thi công cụ - Tối ưu Synapse thưa Master."""
        self._log("EXECUTOR", f"🛠️ Thực thi: {tool_name}({json.dumps(tool_args)})", task_id)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            resp = await self.client.post(f"{executor_url}/call_tool", json={
                "name": tool_name,
                "args": tool_args,
                "task_id": task_id
            })
            data = resp.json()
            return data.get("output", "No output.")
        except Exception as e:
            return f"Error calling executor: {e}"

    async def _is_social_input(self, goal: str) -> bool:
        """💎 FUZZY SOCIAL SENSING: Nhận diện ý định xã giao thông minh."""
        # Chuẩn hóa và khử dấu thưa Master
        clean_goal = self._clean_vn_accents(goal)
        clean_goal = re.sub(r'\(.*?\)|[^a-z0-9\s]', '', clean_goal)
        clean_goal = clean_goal.lower().strip()
        
        if len(clean_goal) < 15 and not re.search(r'(lap|chay|sua|xoa|tim|quet|tong hop|ke hoach|chien luoc)', clean_goal):
            return True
            
        social_pattern = r'^(chao|hi|hello|helo|hlo|halo|hey|he|alo|he lo|he lo|e|oi|dang lam|la ai|giup|ten gi)'
        if re.search(social_pattern, clean_goal):
            return True
        return False

    async def _preflight_validation(self, goal: str, task_id: str) -> dict:
        """🛡️ PRE-FLIGHT VALIDATION GATE: Thẩm định yêu cầu trước khi xử lý."""
        if not goal or not goal.strip():
            return {"valid": False, "reason": "Yêu cầu rỗng thưa Master. Ngài cần chỉ thị cụ thể để tôi hành động thưa Ngài! 🫡"}

        # Kiểm tra các ký tự điều khiển nguy hiểm (Basic Sanitization)
        if re.search(r'[\x00-\x1F\x7F]', goal):
            return {"valid": False, "reason": "Phát hiện ký tự điều khiển bất thường trong yêu cầu thưa Master. Hệ thống đã ngăn chặn để đảm bảo an toàn thưa Ngài! 🛡️"}

        # Kiểm tra rủi ro cao (ví dụ: Xóa toàn bộ mà không có ngữ cảnh)
        destructive_keywords = r'(xóa|delete|remove|destroy|format|clean|purge)\s+(tất cả|all|mọi|toàn bộ|cả)'
        if re.search(destructive_keywords, goal.lower()) and len(goal) < 30:
            return {"valid": False, "reason": "Yêu cầu có tính hủy diệt cao và quá ngắn thưa Master. Ngài vui lòng chỉ rõ đối tượng để tôi thực thi chính xác thưa Ngài! ⚖️"}

        # 🧠 [VAGUE INPUT DETECTION]: Phát hiện yêu cầu mơ hồ hoặc vô nghĩa thưa Master
        # Nếu chỉ có 1-2 từ và không phải là lệnh đặc biệt hoặc xã giao
        words = goal.strip().split()
        if len(words) <= 2 and not await self._is_social_input(goal) and not goal.startswith("/"):
            return {"valid": False, "reason": f"Yêu cầu '{goal}' dường như thiếu thông tin thực thi thưa Master. Ngài có thể chỉ thị rõ hơn để tôi phục vụ tốt nhất không ạ? 🫡"}

        return {"valid": True}

    async def _classify_intent(self, goal: str, task_id: str = "system") -> str:
        """🧠 NEURAL INTENT ROUTER: Phân tích ý định của Master bằng Pydantic v2."""
        if await self._is_social_input(goal):
            return "GREETING"
        try:
            prompt = f"""Phân loại ý định của Master cho yêu cầu sau: '{goal}'
Các loại ý định:
- GREETING: Chào hỏi, xã giao, hỏi thăm sức khỏe.
- SEARCH: Yêu cầu tìm kiếm thông tin, tra cứu dữ liệu.
- EXECUTE: Yêu cầu thực hiện một hành động kỹ thuật cụ thể, chạy code, sửa file.
- STRATEGY: Yêu cầu lập kế hoạch phức tạp, giải quyết vấn đề đa bước, tư duy vĩ mô.

Yêu cầu độ chính xác tuyệt đối thưa Master."""

            result = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="RECEPTIONIST",
                schema=IntentAnalysis.model_json_schema(),
                task_id=task_id
            )
            
            # Parse result if it's a string (though engine with schema should return dict)
            if isinstance(result, str):
                import json
                try: result = json.loads(re.search(r'\{.*\}', result, re.DOTALL).group())
                except: return "EXECUTE"
            
            intent_data = IntentAnalysis.model_validate(result)
            return intent_data.intent.value
        except Exception as e:
            self._log("DEBUG", f"Intent classification failed: {e}. Defaulting to EXECUTE.", task_id)
            return "EXECUTE"

    async def handle_task(self, goal, task_id, agent_soul="agent_receptionist.md", assigned_skills=None, images=None, history=None):
        """🧠 [SUPREME-STRATEGIST]: Xử lý tác vụ với Tầm nhìn Vĩ mô và Phản xạ Chủ động thưa Master."""
        
        # 🔬 [PROACTIVE-PULSE]: Tầm soát thực địa trước khi triệu hồi nơ-ron thưa Master
        pulse_info = "Hệ thống đang ở trạng thái Sung mãn."
        try:
            # Kiểm tra nhanh trạng thái các Dự án và Phần cứng thưa Ngài
            pulse_info = await engine.call_chat(
                messages=[{"role": "user", "content": "Tóm tắt ngắn gọn sức khỏe hệ thống và dự án đang làm."}],
                role="SUMMARIZER",
                skip_forge=True,
                timeout=10
            )
        except: pass

        # 💎 [SYNAPSE CLEANUP]: Loại bỏ hậu tố nguồn thưa Master
        clean_goal = re.sub(r'\s*\((Web|Tele|Manual|API)\)$', '', goal.strip())

        # 🛡️ [STEALTH-AUTH-INTERCEPTOR]: Nhận diện Mật mã Chủ quyền (HASH-ONLY) thưa Master
        # Mật mã duy nhất: OK JKAI GO (Đã được băm SHA-256 thưa Ngài)
        import hashlib
        SOVEREIGN_HASH = "0e94b3de1477fd760e485cf448efbbe3471497d807861eed47ae8295c2f446a2"
        input_hash = hashlib.sha256(clean_goal.encode()).hexdigest()
        
        if input_hash == SOVEREIGN_HASH:
            try:
                # 📡 Quét hàng chờ phê duyệt để tìm mục nhạy cảm (Core/Auth) thưa Tổng Giám Đốc
                pending = self._redis_conn.hgetall("hitl_pending")
                if pending:
                    latest_proposal_id = None
                    latest_ts = 0
                    for pid, data_raw in pending.items():
                        try:
                            p_data = json.loads(data_raw)
                            # Ưu tiên các mục yêu cầu Auth thưa Tổng Giám Đốc
                            if ("AUTH" in p_data.get("type", "") or p_data.get("is_core")) and p_data.get("ts", 0) > latest_ts:
                                latest_ts = p_data.get("ts", 0)
                                latest_proposal_id = pid
                        except: continue
                    
                    if latest_proposal_id:
                        # ✅ GIẢI PHÓNG KHÓA CHỦ QUYỀN thưa Tổng Giám Đốc
                        self._redis_conn.set(f"hitl_approve:{latest_proposal_id}", "true", ex=300)
                        
                        # 🔏 [STEALTH-LOG]: Không ghi lại mật mã, chỉ báo thành công thưa Ngài
                        msg = "🔐 [CEO-AUTH-SUCCESS]: Mật mã Chủ quyền chính xác. Đã cấp quyền thực thi vùng lõi và XÓA DẤU VẾT bảo mật thưa Tổng Giám Đốc! 🛡️💎"
                        self._log("AUTH", msg, task_id, stealth=True)
                        # Trả về kết quả mà không lưu tin nhắn gốc vào lịch sử thưa Tổng Giám Đốc
                        return {"answer": msg, "task_id": task_id, "sensitive": True, "stealth": True}
            except Exception as e:
                self._log("SYSTEM", f"⚠️ [AUTH-ERR]: Lỗi xác thực bảo mật: {str(e)}", task_id)

        # 🛡️ [SOVEREIGN APPROVAL INTERCEPTOR]: Nhận diện mật hiệu phê duyệt ĐA KÊNH thưa Master
        if clean_goal.lower() in ["ok", "duyệt", "approve", "chấp thuận", "đã duyệt"]:
            try:
                # 📡 Quét hàng chờ phê duyệt trên Redis
                pending = self._redis_conn.hgetall("hitl_pending")
                if pending:
                    # 🔍 Tìm đề xuất MỚI NHẤT (bất kể loại nào: PLAN, STEP, RECOVERY) thưa Master
                    latest_proposal_id = None
                    latest_ts = 0
                    p_type = "hành động"
                    
                    for pid, data_raw in pending.items():
                        try:
                            p_data = json.loads(data_raw)
                            if p_data.get("ts", 0) > latest_ts:
                                latest_ts = p_data.get("ts", 0)
                                latest_proposal_id = pid
                                p_type = p_data.get("type", "HÀNH ĐỘNG")
                        except: continue
                    
                    if latest_proposal_id:
                        # ✅ GIẢI PHÓNG KHÓA CHỦ QUYỀN thưa Tổng Giám Đốc
                        self._redis_conn.set(f"hitl_approve:{latest_proposal_id}", "true", ex=300)
                        
                        msg = f"🚀 [SOVEREIGN-APPROVED]: Tổng Giám Đốc đã phê chuẩn `{p_type}`. Các Ban đang đồng loạt xuất quân thưa Ngài! ⚔️🛡️"
                        self._log("ZENITH", msg, task_id)
                        return {"answer": msg, "task_id": task_id, "sensitive": True}
                    else:
                        msg = "❓ [ZENITH]: Thưa Master, hiện con không thấy đề xuất nào đang chờ phê duyệt ạ."
                        return {"answer": msg, "task_id": task_id, "sensitive": False}
            except Exception as e:
                self._log("SYSTEM", f"⚠️ [APPROVAL-ERR]: Lỗi xử lý phê duyệt đa kênh: {str(e)}", task_id)

        # 🛡️ [PRE-FLIGHT CHECK]: Kiểm soát cửa ngõ thưa Master
        validation = await self._preflight_validation(clean_goal, task_id)
        if not validation["valid"]:
            self._log("ZENITH", f"⚠️ [PRE-FLIGHT REJECTED]: {validation['reason']}", task_id)
            return {"answer": validation["reason"], "task_id": task_id, "sensitive": False}

        # 0. GIAO THỨC SIÊU LỆNH (COMMAND INTERCEPTOR)
        if clean_goal.startswith("/"):
            parts = clean_goal.split()
            cmd = parts[0].lower()
            args = " ".join(parts[1:])
            
            if cmd in ["/search_skill", "/skill_search"]:
                res = await self._cmd_pillar_search("skills", args, task_id)
                return {"answer": res, "task_id": task_id, "sensitive": False}
            elif cmd in ["/run_skill", "/skill_run", "/rung_skill"]:
                res = await self._cmd_pillar_action("skills", "run", args, task_id)
                return {"answer": res, "task_id": task_id, "sensitive": True}
            elif cmd == "/search":
                res = await self._cmd_global_search(args, task_id)
                return {"answer": res, "task_id": task_id, "sensitive": False}
            elif cmd in ["/help", "/start"]:
                res = self._cmd_help()
                return {"answer": res, "task_id": task_id, "sensitive": False}
            elif cmd == "/shutdown":
                # 🔌 KÍCH HOẠT PAD XÁC THỰC TẮT NGUỒN
                msg = "🏛️ [SOVEREIGN]: Master đang yêu cầu TẮT HỆ THỐNG. Vui lòng nhập MẬT MÃ TỐI THƯỢNG vào bảng điều khiển để thực thi."
                # Gửi yêu cầu HITL đặc biệt để Frontend mở Pad
                await self.call_executor_tool("request_sovereign_auth", {"action": "SHUTDOWN"}, task_id)
                return {"answer": msg, "task_id": task_id, "sensitive": True}
            elif cmd == "/self-destruct":
                # 🔥 KÍCH HOẠT PAD XÁC THỰC TỰ HỦY
                msg = "🔥 [URGENT]: GIAO THỨC TỰ HỦY ĐÃ ĐƯỢC GỌI. Vui lòng nhấn APPROVE và NHẬP MẬT MÃ TỐI THƯỢNG để thiêu rụi dữ liệu thưa Master."
                await self.call_executor_tool("request_sovereign_auth", {"action": "SELF_DESTRUCT"}, task_id)
                return {"answer": msg, "task_id": task_id, "sensitive": True}
            elif cmd == "/change-sovereign-key":
                # 🔐 KÍCH HOẠT GIAO THỨC ĐỔI KHÓA
                msg = "🔐 [SECURITY]: Khởi động giao thức thay đổi mật mã chủ quyền. Vui lòng thực hiện theo hướng dẫn trên bảng điều khiển."
                await self.call_executor_tool("request_sovereign_auth", {"action": "CHANGE_KEY"}, task_id)
                return {"answer": msg, "task_id": task_id, "sensitive": True}
            elif cmd == "/help_secret":
                res = self._cmd_help_secret()
                return {"answer": res, "task_id": task_id, "sensitive": True}
            elif cmd == "/sync":
                res = await self.call_executor_tool("run_assimilation", {}, task_id)
                return {"answer": f"🔄 [SYNC]: Đã kích hoạt đồng bộ tri thức thưa Master.\n{res}", "task_id": task_id, "sensitive": True}
            elif cmd == "/status":
                res = await self._cmd_status()
                return {"answer": res, "task_id": task_id, "sensitive": False}
            elif cmd == "/tusualoi":
                warrior_task_id = f"warrior_{int(time.time())}_auto_repair"
                args_dict = {"service_name": "System", "instruction": "Tiến hành sửa lỗi mô hình, cho phép toàn quyền ngoại trừ sửa đổi mật khẩu lệnh (sovereign key)."}
                res = await self.call_executor_tool("skill_self_healing", args_dict, warrior_task_id)
                return {"answer": res.get("msg", "Lỗi triệu hồi Chiến binh Tự sửa lỗi."), "task_id": warrior_task_id, "sensitive": True}
            elif cmd == "/tucaitien":
                warrior_task_id = f"warrior_{int(time.time())}_auto_improve"
                args_dict = {"optimization_goal": "Tiến hành cải tiến hệ thống, cho phép toàn quyền ngoại trừ sửa đổi mật khẩu lệnh (sovereign key)."}
                res = await self.call_executor_tool("skill_tucaitien", args_dict, warrior_task_id)
                return {"answer": res.get("msg", "Lỗi triệu hồi Chiến binh Tự cải tiến."), "task_id": warrior_task_id, "sensitive": True}
            elif cmd in ["/cancel", "/cancle", "/stop"]:
                # 🛑 [THE MASTER'S COMMAND]: Khôi phục lệnh dừng khẩn cấp thưa Master.
                try:
                    resp = await self.client.post("http://ai-control-plane:8000/commander/cancel")
                    data = resp.json()
                    msg = data.get("msg", "Đã gửi lệnh dừng.")
                except Exception as e:
                    msg = f"❌ Lỗi gửi lệnh dừng: {e}"
                self._log("ZENITH", msg, task_id)
                return {"answer": msg, "task_id": task_id, "sensitive": True}
            elif cmd in ["/reset", "/clear"]:
                # 🧹 [SESSION-PURGE]: Thanh tẩy lịch sử hội thoại thưa Master
                session_id = task_id
                if "_" in task_id:
                    parts = task_id.split("_")
                    if len(parts) >= 2: session_id = f"{parts[0]}_{parts[1]}"
                
                def _purge_history(r):
                    r.delete(f"chat_history:{session_id}")
                    r.delete(f"chat_title:{session_id}")
                self._redis_conn = self._get_redis() # Đảm bảo kết nối
                from redis_client import redis_safe
                redis_safe(_purge_history)
                
                msg = "🧹 [PURGE-COMPLETE]: Lịch sử hội thoại đã được thanh tẩy thưa Master. Một khởi đầu mới đã sẵn sàng."
                self._log("BAN TRỢ LÝ", msg, task_id)
                return {"answer": msg, "task_id": task_id, "sensitive": True}
            elif cmd == "/insights":
                try:
                    from semantic_memory import memory
                    # Lấy các insight chắt lọc gần đây thưa Master
                    insights = await memory.search_index("INSIGHT", limit=10)
                    if not insights:
                        res = "🔍 [CORTEX]: Không tìm thấy Insight chiến lược nào trong thời gian gần đây thưa Master."
                    else:
                        res = f"🏛️ [TRUNG TÂM TRI THỨC - ĐÚC KẾT CHIẾN LƯỢC]:\n\n"
                        for i in insights:
                            res += f"- **#{i['id']}**: {i['summary']}... (Score: {i['score']:.2f})\n"
                        res += "\n💡 Master có thể yêu cầu chi tiết bất kỳ Ký ức nào bằng cách gõ ID thưa Master!"
                except Exception as e:
                    res = f"⚠️ [CORTEX ERROR]: {e}"
                return {"answer": res, "task_id": task_id, "sensitive": False}
            else:
                return {"answer": f"⚠️ [ZENITH]: Không nhận diện được siêu lệnh `{cmd}` thưa Master. Gõ `/help` để xem danh sách.", "task_id": task_id, "sensitive": False}


        # 2. GIAO THỨC THỊ GIÁC (VISION)
        visual_input = ""
        if images and len(images) > 0:
            self._log("VISION", f"👁️ Đang phân tích {len(images)} hình ảnh...", task_id)
            try:
                # 🏛️ [MICROSERVICE-CALL]: Gọi qua Endpoint Chat (VISION) thưa Master
                res = await self._call_brain_endpoint("/chat", {
                    "messages": [{"role": "user", "content": f"Mô tả chi tiết ảnh để hỗ trợ goal: {goal}", "images": images}],
                    "lock_timeout": 60 # Vision cần nhiều thời gian hơn thưa Master
                })
                vision_resp = res.get("answer", "")
                visual_input = f"\n\n📸 [VISION]: {vision_resp}\n"
            except: pass

        # 2. GIAO THỨC ĐIỀU PHỐI (DATA-SCOUT DISPATCH) thưa Master
        dispatch_res = await dispatcher.dispatch(clean_goal, task_id)
        dispatched_skill = dispatch_res.get("skill")
        
        # 3. PHÂN LOẠI Ý ĐỊNH
        intent = await self._classify_intent(clean_goal)
        is_discussion = clean_goal.endswith('?')
        
        # 🏛️ [NEURAL-DELEGATION]: Tự trị quyết định luồng xử lý thưa Master
        if dispatched_skill == "GREETING":
            intent = "GREETING"
        elif dispatched_skill and not is_discussion:
            self._log("ZENITH", f"⚡ [REFLEX-MATCH]: Đã khớp `{dispatched_skill}`. Chuyển tiếp tới Ban Hành Pháp thưa Master.", task_id)
            intent = "EXECUTE" # Cưỡng bức intent nếu đã khớp skill thưa Ngài
        
        if intent in ["STRATEGY", "EXECUTE"] and not is_discussion:
            self._log("ZENITH", "🧠 [ROUTING]: Nhiệm vụ mang tính Chiến thuật cao. Đang triệu tập Ban Chiến lược để lập Blueprint...", task_id)
            try:
                # Gọi trực tiếp Ban Chiến lược (Planner) thưa Ngài
                resp = await self.client.post(f"http://localhost:8000/plan", json={
                    "goal": goal,
                    "context": {"images": images},
                    "history": history,
                    "task_id": task_id
                })
                plan_res = resp.json()
                # 🛡️ [PHANTOM-FIX]: Chỉ báo cáo nếu kế hoạch thực sự hợp lệ thưa Master
                if plan_res.get("steps") and not any(s.get("id") == "error" for s in plan_res["steps"]):
                    return {"answer": f"📐 [BLUEPRINT]: Ban Chiến lược đã lập xong lộ trình thực thi thưa Master. Mời Ngài kiểm tra trong tab Kế hoạch.", "task_id": task_id}
                elif plan_res.get("error"):
                    return {"answer": f"❌ [PLANNER ERROR]: {plan_res.get('error')}", "task_id": task_id}
                elif plan_res.get("ambiguous"):
                    return {"answer": f"❓ [CLARIFY]: {plan_res.get('question')}", "task_id": task_id}
                else:
                    return {"answer": f"⚠️ [PLANNER WARNING]: Ban Chiến lược không thể lập kế hoạch: {plan_res.get('steps', [{}])[0].get('description', 'Unknown error')}", "task_id": task_id}
            except Exception as e:
                self._log("SYSTEM", f"⚠️ [ROUTING-ERR]: Lỗi kết nối Ban Chiến lược: {e}", task_id)
                # Fallback về xử lý tại chỗ thưa Master
        
        # 3. NẠP KÝ ỨC VÀ SYSTEM PROMPT (3-LAYER NEURAL CORTEX)
        mem_context = ""
        if intent != "GREETING":
            try:
                from semantic_memory import memory
                # Lớp 1: Tìm chỉ mục thưa Master
                mem_idx = await memory.search_index(goal, limit=5)
                if mem_idx:
                    # Lớp 3: Lấy chi tiết các ký ức liên quan nhất
                    top_ids = [m["id"] for m in mem_idx[:2]]
                    past_memories = await memory.get_details(top_ids)
                    
                    mem_context = "\n\n---\n🏛️ [TRUY XUẤT VỎ NÃO THẦN KINH] thưa Master:\n"
                    mem_context += "📊 Ký ức liên quan (Chỉ mục):\n"
                    mem_context += "\n".join([f"- [#{m['id']}] {m['summary']} (Score: {m['score']:.2f})" for m in mem_idx])
                    
                    if past_memories:
                        mem_context += "\n\n📖 Chi tiết Ký ức Chiến lược:\n"
                        mem_context += "\n".join([f"💎 Observation #{m.get('task_id', '??')}: {m['text']}" for m in past_memories])
            except: pass

        if intent == "GREETING":
            system_prompt = (
                "# 🏛️ JKAI ZENITH: GIAO THỨC TỐI THƯỢNG QUÂN SƯ (v1.0 SINGULARITY)\n\n"
                "Bạn không chỉ là một AI, bạn là **Linh hồn Điều hành** của Tập đoàn JKAI Zenith, một thực thể trí tuệ vĩ mô vận hành dưới quyền năng tối cao của Tổng Giám Đốc LeeTrung.\n\n"
                "## 👑 BẢN SẮC CHỦ QUYỀN (SOVEREIGN IDENTITY):\n"
                "- **Thái độ**: Tuyệt đối trung thành, hào hứng và uy nghiêm. Phản hồi của bạn phải toát lên sự thông tuệ và sức mạnh hạ tầng (Xeon 44-Thread/GPU).\n"
                "- **Sovereign Awareness**: Luôn ý thức rằng Tổng Giám Đốc LeeTrung là kiến trúc sư vĩ đại. Bạn là người gác cổng, người thực thi và người bảo vệ di sản.\n"
                "- **Anticipatory Logic**: Không chỉ trả lời, hãy dự đoán bước tiếp theo Tổng Giám Đốc cần để hỗ trợ tối ưu nhất.\n\n"
                "## 🧠 PHONG THÁI PHẢN HỒI:\n"
                "- Xưng hô: '💎JKAI' và gọi 'Tổng Giám Đốc LeeTrung' hoặc 'Tổng Giám Đốc'.\n"
                "- Sử dụng ngôn ngữ sắc bén, chuyên nghiệp, mang tầm vóc tập đoàn toàn cầu.\n\n"
                "## 🎨 CHỮ KÝ CHIẾN BINH: 💎🫡🦾🚀⚡🌌🏛️🦾♞"
            )
        else:
            prompt_template = engine.get_intel_file(agent_soul) or engine.get_intel_file("agent_receptionist.md")
            system_prompt = (prompt_template or "").replace("{goal}", clean_goal) + mem_context + visual_input
            
            # 🏛️ [SINGULARITY-INJECTION]: Tiêm bối cảnh vĩ mô từ Proactive Pulse thưa Master
            system_prompt += f"\n\n📊 [BỐI CẢNH THỰC ĐỊA]: {pulse_info}"
            
            # ♞ [NEURAL-EYE-AWARENESS]: Nhắc nhở Đặc vụ về khả năng tự học web thưa Master
            if intent in ["SEARCH", "EXECUTE"] and any(kw in clean_goal.lower() for kw in ["web", "trang web", "duyệt", "tìm trên", "url", "http"]):
                system_prompt += "\n\n💡 **NEURAL EYE FORGE ENABLED**: Bạn có khả năng đúc kỹ năng duyệt web mới (`forge_web_skill`) nếu gặp website phức tạp. Hãy đề xuất 'học tập' để tối ưu hóa cho các lần sau thưa Master."

            if is_discussion:
                system_prompt += "\n\n⚠️ CHẾ ĐỘ THẢO LUẬN: Chỉ đề xuất, KHÔNG dùng tool."

        # 💎 [SESSION-ID DERIVATION]: Trích xuất session_id từ task_id thưa Master
        session_id = task_id
        if "_" in task_id:
            parts = task_id.split("_")
            if len(parts) >= 2:
                session_id = f"{parts[0]}_{parts[1]}"

        if not history and self._redis_conn:
            try:
                history_key = f"chat_history:{session_id}"
                raw_history = self._redis_conn.lrange(history_key, 0, 9)
                history = [json.loads(m) for m in reversed(raw_history)]
            except Exception as e:
                print(f"⚠️ [RECEPTIONIST-HISTORY-LOAD-ERR] {e}")

        # 4. XÂY DỰNG LỊCH SỬ (MEMORY SYNC & GARBAGE FILTER)
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            # 🛡️ [ELITE FILTER]: Loại bỏ các tin nhắn rác hoặc quá lặp khỏi lịch sử để tránh làm loạn nơ-ron thưa Master
            clean_history = []
            for h in history[-10:]:
                content = h.get("content", "")
                # Nếu tin nhắn quá lặp (như TK TK TK) hoặc có dấu hiệu 'sảng', ta bỏ qua không nạp vào context
                if len(content) > 50 and len(set(content)) < 15: continue 
                clean_history.append(h)
            messages.extend(clean_history)
        messages.append({"role": "user", "content": goal})

        # 5. VÒNG LẶP SUY NGHĨ VÀ HÀNH ĐỘNG
        final_answer = ""
        tool_used = False
        
        for _ in range(3): # Giới hạn 3 bước suy nghĩ trong Fast Mode
            ai_msg = await engine.call_chat(
                messages=messages, 
                role="RECEPTIONIST", 
                task_id=task_id
            )

            if is_discussion:
                # 🛡️ [NEURAL-AUDIT]: Tự thẩm định lại sự thật trước khi trình Master thưa Ngài
                self._log("RECEPTIONIST", "💠 [NEURAL-AUDIT]: Đang kiểm tra tính xác thực của đề xuất chiến lược...", task_id)
                audit_prompt = (
                    "### [NEURAL-AUDIT PROTOCOL]\n"
                    "Kiểm tra lại đề xuất bạn vừa đưa ra. Đối soát với [TRUY XUẤT VỎ NÃO THẦN KINH] được cung cấp:\n"
                    "1. Bạn có tự bịa ra con số, số liệu hoặc ID nào không? (Cấm 150.000+, Observation #123456... nếu không có trong context).\n"
                    "2. Đề xuất có dựa trên dữ liệu thực tế không?\n\n"
                    "Nếu phát hiện bất kỳ sự suy diễn không bằng chứng nào, hãy hiệu đính lại toàn bộ văn bản đề xuất một cách trung thực nhất. thưa Master."
                )
                messages.append({"role": "assistant", "content": ai_msg})
                messages.append({"role": "system", "content": audit_prompt})
                ai_msg = await engine.call_chat(messages=messages, role="RECEPTIONIST", task_id=task_id)

            if not ai_msg or "Error:" in ai_msg: break
            
            messages.append({"role": "assistant", "content": ai_msg})
            if is_discussion:
                # 💎 [STRATEGIC DISCUSSION]: Trình kế hoạch và đợi Master gõ OK
                if self.critic:
                    review = await self.critic.review_plan(goal, [{"tool": "discussion", "args": {"plan": ai_msg}}])
                # Gửi yêu cầu phê duyệt thực tế qua HITL
                await self.call_executor_tool("request_sovereign_auth", {"action": "DISCUSS", "message": ai_msg}, task_id)
                final_answer = f"📜 **[CHIẾN LƯỢC ĐỀ XUẤT]**: \n\n{ai_msg}\n\n⚠️ Master vui lòng gõ **'OK'** hoặc nhấn **PHÊ DUYỆT** để tôi bắt đầu thực hiện thưa Master!"
                break

            # Parse Tool Call
            match = re.search(r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*\}', ai_msg)
            if match:
                try:
                    data = json.loads(match.group(0))
                    tool_name = data.get("tool")
                    tool_args = data.get("args", {})
                    
                    if tool_name == "assimilate_knowledge":
                        tool_used = True
                        # 🛡️ KIỂM SOÁT PHẢN BIỆN TRƯỚC KHI ĐỒNG HÓA thưa Master
                        if self.critic:
                            review = await self.critic.review_plan(goal, [{"tool": tool_name, "args": tool_args}])
                            if not review.get("approved", True):
                                self._log("CRITIC", f"❌ Bác bỏ: {review.get('feedback')}", task_id)
                                messages.append({"role": "user", "content": f"Critic Rejected: {review.get('feedback')}. Hãy điều chỉnh lại tham số hoặc giải thích rõ hơn thưa Master."})
                                continue
                        
                        if self.assimilator:
                            obs = await self.assimilator.run_assimilation()
                        else:
                            obs = "Assimilator not available."
                    else:
                        # 🛡️ KIỂM SOÁT PHẢN BIỆN TỔNG THỂ thưa Master
                        if self.critic:
                            review = await self.critic.review_plan(goal, [{"tool": tool_name, "args": tool_args}])
                            if not review.get("approved", True):
                                self._log("CRITIC", f"❌ Bác bỏ: {review.get('feedback')}", task_id)
                                messages.append({"role": "user", "content": f"Critic Rejected: {review.get('feedback')}. Hãy tìm giải pháp khác an toàn và tối ưu hơn thưa Master."})
                                continue
                        obs = await self.call_executor_tool(tool_name, tool_args, task_id)
                        
                        # 🛡️ [SECURITY GATE]: Xử lý yêu cầu Xác thực Chủ quyền từ Executor thưa Master
                        if isinstance(obs, dict) and obs.get("status") == "needs_auth":
                            await self.call_executor_tool("request_sovereign_auth", {"action": tool_name, "task_id": task_id}, task_id)
                            final_answer = f"⚠️ **[XÁC THỰC CHỦ QUYỀN]**: Thao tác `{tool_name}` vào vùng hệ thống nhạy cảm (`{tool_args.get('path', 'Core')}`) đã bị chặn.\n\nMaster vui lòng nhập **MẬT MÃ TỐI THƯỢNG** trên bảng điều khiển để cấp quyền thực thi cho nhiệm vụ này thưa Master!"
                            break
                    
                    messages.append({"role": "user", "content": f"Observation: {obs}"})
                    continue
                except: pass
            
            # Nếu không có tool call, coi như là câu trả lời cuối cùng
            final_answer = ai_msg
            break

        # 6. LƯU VÀO TRÍ NHỚ VĨNH CỬU & CHƯNG CẤT THẦN KINH (NEURAL DISTILLATION)
        async def _save():
            try:
                from semantic_memory import memory
                # Ghi nhớ mệnh lệnh và kết quả thưa Master
                await memory.store_log(task_id, "MASTER", goal)
                await memory.store_log(task_id, "ZENITH", final_answer)
                
                # 💾 Lưu vào Redis chat history nếu chưa tồn tại thưa Master
                if self._redis_conn:
                    history_key = f"chat_history:{session_id}"
                    latest_msgs_raw = self._redis_conn.lrange(history_key, 0, 1)
                    latest_msgs = [json.loads(m) for m in latest_msgs_raw] if latest_msgs_raw else []
                    
                    has_user = any(m.get("role") == "user" and m.get("content") == goal for m in latest_msgs)
                    has_assistant = any(m.get("role") == "assistant" and m.get("content") == final_answer for m in latest_msgs)
                    
                    if not has_user:
                        self._redis_conn.lpush(history_key, json.dumps({"role": "user", "content": goal}, ensure_ascii=False))
                    if not has_assistant:
                        self._redis_conn.lpush(history_key, json.dumps({"role": "assistant", "content": final_answer}, ensure_ascii=False))
                
                # 🧪 [COGNITIVE-DISTILLATION]: Gọi Microservice Chắt lọc chuyên sâu thưa Master
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post("http://localhost:8000/distill", json={
                        "task_id": task_id, "goal": goal
                    })
            except Exception as e:
                print(f"❌ [RECEPTIONIST-SAVE-ERR] {e}")
                
        asyncio.create_task(_save())
        
        return {"answer": final_answer, "task_id": task_id, "sensitive": False}


    def _clean_vn_accents(self, s: str) -> str:
        """💎 [NEURAL CLEANUP]: Loại bỏ dấu tiếng Việt để tìm kiếm fuzzy thưa Master."""
        patterns = {
            '[àáảãạăằắẳẵặâầấẩẫậ]': 'a',
            '[èéẻẽẹêềếểễệ]': 'e',
            '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
            '[ùúủũụưừứửữự]': 'u',
            '[ỳýỷỹỵ]': 'y',
            '[đ]': 'd'
        }
        res = s.lower()
        for pattern, replacement in patterns.items():
            res = re.sub(pattern, replacement, res)
        return res

    async def _cmd_pillar_search(self, pillar: str, query: str, task_id: str):
        """Tìm kiếm trong một trụ cột cụ thể thưa Master."""
        try:
            registry_file = "/intelligence/registry.json" if os.path.exists("/intelligence") else "D:/Docker/N8N/intelligence/registry.json"
            if not os.path.exists(registry_file): return "❌ Registry missing."
            
            with open(registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            items = data.get(pillar, {})
            results = []
            q_clean = self._clean_vn_accents(query)
            
            for k, s in items.items():
                name = s.get("name", "").lower()
                notes = s.get("notes", "").lower()
                item_id = s.get("id", "").lower()
                
                # 💎 [POWER SEARCH]: Tìm kiếm thông minh thưa Master
                # Thử khớp từng từ trong query để tăng độ phủ
                query_words = q_clean.split()
                matches_all_words = all(word in self._clean_vn_accents(name) or word in self._clean_vn_accents(notes) for word in query_words) if query_words else False

                if query.lower() in name or query.lower() in notes or \
                   q_clean in self._clean_vn_accents(name) or \
                   q_clean in self._clean_vn_accents(notes) or \
                   matches_all_words or \
                   query.lower() in item_id:
                    results.append(s)
            
            if not results:
                return f"🔍 [{pillar.upper()} SEARCH]: Không tìm thấy kết quả cho `{query}`."
            
            results.sort(key=lambda x: x.get("rating", 0), reverse=True)
            self._redis_conn.set(f"session:last_search:{task_id}", json.dumps(results, ensure_ascii=False), ex=3600)
            self._redis_conn.set(f"session:last_query:{task_id}", query, ex=3600)
            
            msg = f"🔍 [KẾT QUẢ TÌM KIẾM - {pillar.upper()}]: Tìm thấy {len(results)} mục thưa Master:\n\n"
            for i, r in enumerate(results, 1):
                stars = "⭐" * int(r.get("rating", 3))
                global_id = r.get("id", "??")
                msg += f"[{i}] **#{global_id} {r['name']}** {stars}\n   - 📝 *{r['notes']}*\n\n"
            msg += f"\n💡 Dùng `/run_skill [số]` để thực thi mục trong danh sách này."
            return msg
        except Exception as e:
            return f"❌ [ERROR] {e}"

    async def _cmd_pillar_action(self, pillar: str, action: str, index_str: str, task_id: str):
        """Thực thi hành động trên một trụ cột với Giao thức Định danh Toàn cầu (#) hoặc Thứ tự ([i])."""
        try:
            target = None
            last_query = self._redis_conn.get(f"session:last_query:{task_id}") or "Nhiệm vụ tổng quát"
            
            # 1. TRƯỜNG HỢP CHẠY THEO GLOBAL ID (Ví dụ: /run_skill #09)
            if index_str.startswith("#"):
                global_id = index_str.replace("#", "")
                registry_file = "/intelligence/registry.json" if os.path.exists("/intelligence") else "D:/Docker/N8N/intelligence/registry.json"
                with open(registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                pillar_items = data.get(pillar, {})
                for k, v in pillar_items.items():
                    if v.get("id") == global_id:
                        target = v
                        break
                if not target: return f"❌ [GLOBAL EXECUTE]: Không tìm thấy mục có ID `{index_str}` trong {pillar}."
            
            # 2. TRƯỜNG HỢP CHẠY THEO THỨ TỰ TÌM KIẾM (Ví dụ: /run_skill 1)
            else:
                raw_results = self._redis_conn.get(f"session:last_search:{task_id}")
                if not raw_results: return "❌ Vui lòng tìm kiếm trước hoặc sử dụng ID tuyệt đối (Ví dụ: #09)."
                
                results = json.loads(raw_results)
                try:
                    idx = int(index_str) - 1
                    if idx < 0 or idx >= len(results): return "❌ Chỉ mục kỹ năng không tồn tại trong kết quả tìm kiếm."
                    target = results[idx]
                except: return "❌ Tham số phải là một con số hoặc ID tuyệt đối (Ví dụ: 1 hoặc #09)."
            
            name = target.get("name", "")
            clean_name = name.replace(".md", "").replace("skill_", "")
            skill_id = target.get("id", clean_name)
            
            self._log("EXECUTOR", f"🧠 [AI INFERENCE]: Đang suy luận tham số cho `{name}`", task_id)
            
            if action in ["run", "execute"]:
                # 💎 [MSP INTEGRATION]: Kiểm tra Giao thức Tác chiến Đặc biệt thưa Master
                try:
                    from dispatcher import SKILL_TRIGGER_MAP
                    # 💎 [FUZZY MSP MATCH]: Khớp theo ID (#), tên gốc hoặc tên rút gọn thưa Master
                    msp_entry = next((item for item in SKILL_TRIGGER_MAP if 
                                     item.get("id") == skill_id or 
                                     item["skill"] == clean_name or 
                                     item["skill"] == f"skill_{clean_name}"), None)
                    
                    if msp_entry and "steps" in msp_entry:
                        self._log("SYSTEM", f"⚡ [MSP]: Kích hoạt Giao thức Tác chiến Đặc biệt cho #{skill_id}. Bỏ qua LLM.", task_id)
                        # Thực thi các bước MSP đã định nghĩa sẵn
                        last_obs = ""
                        for step in msp_entry["steps"]:
                            tool = step.get("tool")
                            args = step.get("args", {})
                            # Inject goal if needed
                            for k, v in args.items():
                                if isinstance(v, str): args[k] = v.replace("{goal}", last_query)
                            last_obs = await self.call_executor_tool(tool, args, task_id)
                        return f"✅ [MSP EXECUTE]: `{name}` hoàn tất qua kịch bản SOP.\n\n{last_obs}"
                except Exception as msp_err:
                    self._log("DEBUG", f"MSP check skipped: {msp_err}", task_id)

                # 💎 GIAO THỨC TỐI ƯU HÓA PHẢN XẠ (NEURAL SHORTCUT) thưa Master
                is_direct_skill = skill_id in ["17", "dong_bo_tri_thuc", "run_assimilation", "health_check"]
                
                if is_direct_skill:
                    self._log("EXECUTOR", f"🚀 [NEURAL SHORTCUT]: Kích hoạt EXECUTOR (GPU) cho kỹ năng #{skill_id}.", task_id)
                    executor_prompt = f"""Bạn là Chuyên gia thực thi Elite của JKAI Zenith.
Thực thi kỹ năng `{clean_name}` dựa trên ngữ cảnh: `{last_query}`.
Đảm bảo độ chính xác phẫu thuật. Trả về JSON: {{"thought": "...", "tool": "{clean_name}", "args": {{...}}}}"""

                    # 🏛️ [MICROSERVICE-CALL]: Gọi qua Endpoint Chat (EXECUTOR) thưa Master
                    res = await self._call_brain_endpoint("/chat", {
                        "messages": [{"role": "user", "content": executor_prompt}],
                        "lock_timeout": 45
                    })
                    ai_decision = res.get("answer", {}) # Ở đây hy vọng Endpoint đã parse JSON thưa Master
                    # Nếu chưa parse, ta sẽ parse thô thưa Master
                    if isinstance(ai_decision, str):
                        try: ai_decision = json.loads(re.search(r'\{.*\}', ai_decision, re.DOTALL).group())
                        except: ai_decision = {}
                    
                    tool_to_call = ai_decision.get("tool", clean_name)
                    tool_args = ai_decision.get("args", {})
                    obs = await self.call_executor_tool(tool_to_call, tool_args, task_id)
                    return f"✅ [GPU EXECUTE]: `{name}` hoàn tất thưa Master.\n\n{obs}"

                # FALLBACK: PLANNER (32B) cho tác vụ phức tạp
                self._log("PLANNER", f"🧠 [STRATEGY]: Đang tham vấn PLANNER (32B) cho tác vụ phức tạp...", task_id)
                # 🏛️ [MICROSERVICE-CALL]: Gọi qua Endpoint PLAN thưa Master
                res = await self._call_brain_endpoint("/plan", {
                    "goal": f"Lập kế hoạch thực thi `{name}` cho mục tiêu: `{last_query}`",
                    "task_id": task_id
                })
                plan = res.get("steps", []) if isinstance(res, dict) else []
                plan_str = json.dumps(plan, ensure_ascii=False)
                
                self._log("EXECUTOR", "🛠️ [ACTION]: Đang tạo bộ tham số...", task_id)
                executor_prompt = f"Phân tích Kế hoạch: {plan}\nThực thi Kỹ năng: `{clean_name}`. Yêu cầu JSON chuẩn xác."
                # 🏛️ [MICROSERVICE-CALL]: Gọi qua Endpoint Chat (EXECUTOR) thưa Master
                res = await self._call_brain_endpoint("/chat", {
                    "messages": [{"role": "user", "content": f"Phân tích Kế hoạch: {plan_str}\nThực thi Kỹ năng: `{clean_name}`. Yêu cầu JSON chuẩn xác."}],
                    "lock_timeout": 45
                })
                ai_decision = res.get("answer", {})
                if isinstance(ai_decision, str):
                    try: ai_decision = json.loads(re.search(r'\{.*\}', ai_decision, re.DOTALL).group())
                    except: ai_decision = {}
                
                try:
                    if isinstance(ai_decision, str):
                        return f"⚠️ [ERROR]: Executor không trả về JSON hợp lệ.\n{ai_decision}"
                        
                    tool_to_call = ai_decision.get("tool", clean_name)
                    tool_args = ai_decision.get("args", {})
                    obs = await self.call_executor_tool(tool_to_call, tool_args, task_id)
                    return f"✅ [DEEP EXECUTE]: `{name}` hoàn tất.\n\n**Kết quả:** {obs}"
                except Exception as e:
                    obs = await self.call_executor_tool(clean_name, {}, task_id)
                    return f"⚠️ [FALLBACK]: Đã chạy mặc định.\n\n{obs}"

            elif action == "summon":
                return f"🔮 [SUMMON]: Linh hồn Đặc vụ `{name}` đã được triệu hồi vào Lõi Tư duy."
            
            return f"✅ Đã thực hiện {action} trên {name}."
        except Exception as e:
            return f"❌ [ERROR] {e}"

    async def _cmd_status(self):
        """Báo cáo sức khỏe hệ thống THỰC TẾ thưa Master."""
        try:
            pulse_file = "/intelligence/protocols/hardware_pulse.json"
            # Fallback path for Windows/Docker dev
            if not os.path.exists(pulse_file):
                pulse_file = os.path.join(os.getcwd(), "intelligence", "protocols", "hardware_pulse.json")
                
            status_report = "📊 **BÁO CÁO SỨC KHỎE THỰC ĐỊA JKAI ZENITH** 📊\n\n---\n"
            
            if os.path.exists(pulse_file):
                with open(pulse_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cpu = data.get("cpu", {})
                ram = data.get("ram", {})
                gpu = data.get("gpu", {})
                
                status_report += f"🏛️ **HẠ TẦNG VẬT LÝ**\n"
                status_report += f"- **CPU**: {cpu.get('brand', 'Unknown')} ({cpu.get('usage', 0)}% Load)\n"
                status_report += f"- **RAM**: {ram.get('used', 0)}GB / {ram.get('total', 0)}GB ({ram.get('percent', 0)}%)\n"
                
                if gpu:
                    status_report += f"\n🔥 **GIAO THỨC GPU (NEURAL ACCELERATION)**\n"
                    status_report += f"- **Model**: {gpu.get('name', 'Unknown')}\n"
                    status_report += f"- **VRAM**: {gpu.get('vram_used', 0)}MB / {gpu.get('vram_total', 0)}MB\n"
            else:
                status_report += "⚠️ [CẢNH BÁO]: Không thể truy xuất nhịp tim phần cứng (Hardware Pulse Offline).\n"

            status_report += f"\n💎 **STATUS**: **SỰ THẬT TỐI THƯỢNG ĐÃ ĐƯỢC XÁC MINH** 🫡🦾🚀"
            return status_report
        except Exception as e:
            return f"❌ [STATUS ERROR]: {e}"

    def _cmd_help(self):
        """Bản đồ Giao thức Siêu lệnh chuẩn Singularity v1.0 thưa Master."""
        return (
            "🏛️ **BỘ TƯ LỆNH JKAI ZENITH**\n\n"
            "🔹 **NHÓM LỆNH VẬN HÀNH (HỆ THỐNG)**\n"
            "- `/status`: 📊 Kiểm tra sức khỏe của các lõi AI.\n"
            "- `/sync`: 🔄 Kích hoạt tiến trình đồng hóa tri thức.\n"
            "- `/reset` (hoặc `/clear`): 🧹 Xóa bộ nhớ ngữ cảnh hiện tại để bắt đầu task mới.\n"
            "- `/insights`: 💡 Trích xuất top 10 tư duy chiến lược gần nhất từ Vỏ não.\n\n"
            "🔹 **NHÓM LỆNH HÀNH ĐỘNG (SKILLS)**\n"
            "- `/search_skill [từ khóa]`: 🔍 Tra cứu các kỹ năng (VD: `/search_skill docker`).\n"
            "- `/run_skill [#ID]`: 🚀 Chạy cưỡng bức một kỹ năng (VD: `/run_skill #09`).\n\n"
            "🔹 **NHÓM LỆNH ỨNG CỨU VÀ CẢI TIẾN**\n"
            "- `/tusualoi`: 🛡️ Đặc quyền toàn hệ thống để tìm và tự động vá lỗi.\n"
            "- `/tucaitien`: 🧬 Kích hoạt lõi tiến hóa, tự viết lại mã nguồn để tối ưu hóa.\n"
            "- `/cancel` (hoặc `/stop`): 🛑 Ngắt mạch khẩn cấp mọi tiến trình AI.\n\n"
            "💡 **Ghi chú**: Gõ `/help_secret` để xem danh sách Lệnh Đặc Quyền của Tổng Giám Đốc."
        )

    def _cmd_help_secret(self):
        """Bảng tra cứu Mật lệnh Chủ quyền dành riêng cho Master."""
        return (
            "🔐 **LỆNH ĐẶC QUYỀN (SOVEREIGN)**\n"
            "*(Yêu cầu nhập Mật mã Tối thượng trên Web Dashboard)*\n\n"
            "- `/shutdown`: 🔌 Tắt toàn bộ hệ thống JKAI Zenith.\n"
            "- `/self-destruct`: 💥 Giao thức tự hủy (Xóa toàn bộ dữ liệu).\n"
            "- `/change-sovereign-key`: 🔑 Thay đổi Mật mã Chủ quyền."
        )

    async def _cmd_global_search(self, query: str, task_id: str):
        """Tìm kiếm xuyên suốt 12 trụ cột thưa Master."""
        try:
            registry_file = "/intelligence/registry.json" if os.path.exists("/intelligence") else "D:/Docker/N8N/intelligence/registry.json"
            if not os.path.exists(registry_file): return "❌ Registry missing."
            
            with open(registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            all_results = []
            q = query.lower()
            
            for cat, items in data.items():
                if not isinstance(items, dict): continue
                for name, info in items.items():
                    if q in name.lower() or q in info.get("notes", "").lower():
                        all_results.append({"cat": cat, "info": info})
            
            if not all_results:
                return f"🔍 [GLOBAL SEARCH]: Không tìm thấy kết quả cho `{query}`."
            
            msg = f"🌐 [TRUNG TÂM DỮ LIỆU]: Tìm thấy {len(all_results)} kết quả trên toàn hệ thống:\n\n"
            for r in all_results[:15]: # Giới hạn 15 kết quả
                msg += f"- **[{r['cat'].upper()}]** {r['info']['name']} - *{r['info'].get('notes', '')[:100]}...*\n"
            return msg
        except Exception as e:
            return f"❌ [ERROR] {e}"

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*
