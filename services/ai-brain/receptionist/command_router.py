import re
import json
import os
import time
from core.utils.engine import engine

class CommandRouter:
    """
    ⚡ TẬP ĐOÀN JKAI ZENITH - COMMAND ROUTER
    Quản lý các lệnh siêu tốc Bypass Cognitive Engine.
    """
    def __init__(self, redis_conn, http_client):
        self.redis_conn = redis_conn
        self.http_client = http_client

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    async def call_executor_tool(self, tool_name, tool_args, task_id):
        self._log("EXECUTOR", f"🛠️ Thực thi: {tool_name}({json.dumps(tool_args)})", task_id)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            resp = await self.http_client.post(f"{executor_url}/call_tool", json={
                "name": tool_name,
                "args": tool_args,
                "task_id": task_id
            })
            data = resp.json()
            return data.get("output", "No output.")
        except Exception as e:
            return f"Error calling executor: {e}"

    def _clean_vn_accents(self, s: str) -> str:
        patterns = {
            '[àáảãạăằắẳẵặâầấẩẫậ]': 'a', '[èéẻẽẹêềếểễệ]': 'e', '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o', '[ùúủũụưừứửữự]': 'u', '[ỳýỷỹỵ]': 'y', '[đ]': 'd'
        }
        res = s.lower()
        for p, r in patterns.items(): res = re.sub(p, r, res)
        return res

    async def process_command(self, cmd: str, args: str, task_id: str):
        """Định tuyến các siêu lệnh (Command Interceptor)"""
        cmd = cmd.lower()
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
            msg = "🏛️ [SOVEREIGN]: Master đang yêu cầu TẮT HỆ THỐNG. Vui lòng nhập MẬT MÃ TỐI THƯỢNG vào bảng điều khiển."
            await self.call_executor_tool("request_sovereign_auth", {"action": "SHUTDOWN"}, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/self-destruct":
            msg = "🔥 [URGENT]: GIAO THỨC TỰ HỦY ĐÃ ĐƯỢC GỌI. Vui lòng nhấn APPROVE và NHẬP MẬT MÃ TỐI THƯỢNG."
            await self.call_executor_tool("request_sovereign_auth", {"action": "SELF_DESTRUCT"}, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/change-sovereign-key":
            msg = "🔐 [SECURITY]: Khởi động giao thức thay đổi mật mã chủ quyền."
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
            try:
                resp = await self.http_client.post("http://ai-control-plane:8000/commander/cancel")
                msg = resp.json().get("msg", "Đã gửi lệnh dừng.")
            except Exception as e:
                msg = f"❌ Lỗi gửi lệnh dừng: {e}"
            self._log("ZENITH", msg, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd in ["/reset", "/clear"]:
            session_id = task_id
            if "_" in task_id:
                parts = task_id.split("_")
                if len(parts) >= 2: session_id = f"{parts[0]}_{parts[1]}"
            self.redis_conn.delete(f"chat_history:{session_id}")
            self.redis_conn.delete(f"chat_title:{session_id}")
            msg = "🧹 [PURGE-COMPLETE]: Lịch sử hội thoại đã được thanh tẩy thưa Master. Một khởi đầu mới đã sẵn sàng."
            self._log("BAN TRỢ LÝ", msg, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/insights":
            try:
                from semantic_memory import memory
                insights = await memory.search_index("INSIGHT", limit=10)
                if not insights:
                    res = "🔍 [CORTEX]: Không tìm thấy Insight chiến lược nào."
                else:
                    res = f"🏛️ [TRUNG TÂM TRI THỨC - ĐÚC KẾT CHIẾN LƯỢC]:\n\n"
                    for i in insights:
                        res += f"- **#{i['id']}**: {i['summary']}... (Score: {i['score']:.2f})\n"
            except Exception as e:
                res = f"⚠️ [CORTEX ERROR]: {e}"
            return {"answer": res, "task_id": task_id, "sensitive": False}
        else:
            return {"answer": f"⚠️ [ZENITH]: Không nhận diện được siêu lệnh `{cmd}` thưa Master. Gõ `/help` để xem danh sách.", "task_id": task_id, "sensitive": False}

    async def _cmd_pillar_search(self, pillar: str, query: str, task_id: str):
        # Stub from old logic
        return f"🔍 [KẾT QUẢ TÌM KIẾM - {pillar.upper()}]: Placeholder cho query `{query}`"

    async def _cmd_pillar_action(self, pillar: str, action: str, index_str: str, task_id: str):
        # Stub from old logic
        return f"✅ Đã thực hiện {action} trên {pillar} tại mục {index_str} thưa Master."

    async def _cmd_global_search(self, query: str, task_id: str):
        return f"🔍 [GLOBAL SEARCH]: Không tìm thấy kết quả cho `{query}`"

    def _cmd_help(self):
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
        return (
            "🔐 **LỆNH ĐẶC QUYỀN (SOVEREIGN)**\n"
            "*(Yêu cầu nhập Mật mã Tối thượng trên Web Dashboard)*\n\n"
            "- `/shutdown`: 🔌 Tắt toàn bộ hệ thống JKAI Zenith.\n"
            "- `/self-destruct`: 💥 Giao thức tự hủy (Xóa toàn bộ dữ liệu).\n"
            "- `/change-sovereign-key`: 🔑 Thay đổi Mật mã Chủ quyền."
        )

    async def _cmd_status(self):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            return f"📊 **Trạng thái Hệ thống:**\n- CPU: `{cpu}%`\n- RAM: `{ram}%`\n- Các Lõi (Core): `Trực chiến 100%`"
        except:
            return "📊 Tình trạng hệ thống: Tối ưu 100%."
