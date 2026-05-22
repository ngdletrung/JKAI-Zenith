import asyncio
import os
import json
import time
import httpx
from core.utils.engine import engine
from redis_client import redis_safe

class ZenithMonologue:
    """
    💎 JKAI ZENITH: INNER MONOLOGUE PROTOCOL (ZIM)
    Cho phép hệ thống tự tư duy, phân tích và đề xuất cải tiến khi Master vắng mặt.
    """
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self.is_thinking = False

    def _log(self, msg: str):
        print(f"🧠 [MONOLOGUE]: {msg}")
        payload = json.dumps({
            "tag": "MONOLOGUE",
            "msg": f"💭 [ĐỘC THOẠI NỘI TÂM]: {msg}",
            "ts": time.time()
        }, ensure_ascii=False)
        redis_safe(lambda r: r.publish("monitor:log_channel", payload))

    async def gather_context(self):
        """Thu thập dữ liệu từ hệ thống để 'ngẫm nghĩ'."""
        context = {
            "recent_logs": [],
            "latency_stats": [],
            "hardware_health": {},
            "system_status": "Active"
        }
        
        def _get_data(r):
            logs = r.lrange("monitor:log_history", 0, 100) # Tăng lên 100 dòng để nhìn vĩ mô hơn
            pulse = r.get("hardware_pulse_cache")
            return [json.loads(l) for l in logs], json.loads(pulse) if pulse else {}
        
        context["recent_logs"], context["hardware_health"] = redis_safe(_get_data, ([], {}))
        
        # Lọc các log Latency để phân tích hiệu năng
        context["latency_stats"] = [
            l for l in context["recent_logs"] if l.get("tag") == "LATENCY"
        ]
        
        return context

    async def _is_system_idle(self):
        """Kiểm tra xem hệ thống có đang thực sự rảnh rỗi không."""
        # 1. Kiểm tra hàng đợi Task trong Redis
        def _check_queue(r):
            return r.llen("ai_task_queue")
        
        queue_len = redis_safe(_check_queue, 0)
        if queue_len > 0:
            return False, f"Hệ thống đang bận xử lý {queue_len} tác vụ."

        # 2. Kiểm tra Ollama xem có model nào đang chạy không (VRAM check)
        try:
            host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{host}/api/ps")
                if resp.status_code == 200:
                    active_models = resp.json().get("models", [])
                    if len(active_models) > 0:
                        model_names = ", ".join([m['name'] for m in active_models])
                        return False, f"Models đang hoạt động: {model_names}"
        except: pass

        return True, "Hệ thống rảnh rỗi."

    async def think(self):
        """Khởi động quy trình tư duy tự thân với khả năng tự dừng."""
        if self.is_thinking: return
        
        # 🛑 [THE MASTER'S RULE]: Chỉ chạy khi các model rảnh và không có lệnh task nào
        is_idle, reason = await self._is_system_idle()
        if not is_idle:
            print(f"💤 [ZIP-IDLE-WAIT]: Tạm hoãn tư duy. {reason}")
            return

        self.is_thinking = True
        self.thinking_task = asyncio.create_task(self._do_think_process())
        
        # Tạo Guardian để giám sát lệnh mới trong khi đang tư duy
        guardian_task = asyncio.create_task(self._monitor_interruption())
        
        try:
            await self.thinking_task
        except asyncio.CancelledError:
            self._log("⚠️ [PRE-EMPTION]: Phát hiện lệnh mới từ Master! Đã dừng tư duy để ưu tiên tài nguyên. 🚀")
        finally:
            self.is_thinking = False
            if not guardian_task.done():
                guardian_task.cancel()

    async def _monitor_interruption(self):
        """Giám sát sự xuất hiện của lệnh mới để ngắt quy trình tư duy."""
        while self.is_thinking:
            is_idle, _ = await self._is_system_idle()
            if not is_idle:
                if self.thinking_task and not self.thinking_task.done():
                    self.thinking_task.cancel()
                break
            await asyncio.sleep(1) # Kiểm tra mỗi giây để phản ứng nhanh

    async def _do_think_process(self):
        """Tiến trình tư duy thực tế."""
        try:
            self._log("Hệ thống đang rảnh. Bắt đầu quy trình tự soi xét hệ thống...")
            context = await self.gather_context()
            
            # 🛡️ SỬ DỤNG LOGIC WATCHDOG ĐỂ TƯ DUY (CPU ONLY - THE MASTER'S RULE)
            system_prompt = """Bạn là 'Kiến trúc sư Trưởng' (Chief Architect) của hệ thống JKAI Zenith.
Nhiệm vụ của bạn là soi xét Nhật ký và Thông số Phần cứng để đưa ra các phương án VĨ MÔ và TỐI ƯU NHẤT cho Master LeeTrung.

DỰA TRÊN DỮ LIỆU CUNG CẤP:
1. PHÂN TÍCH TÀI NGUYÊN: Nếu CPU/VRAM thường xuyên chạm ngưỡng 90%, hãy đề xuất phương án Cấu trúc lại các Agent (Ví dụ: Chuyển sang model nhỏ hơn cho tác vụ phụ).
2. TẦM NHÌN CHIẾN LƯỢC: Nếu Master thường xuyên thực hiện một chuỗi thao tác, hãy đề xuất tạo 'Siêu kỹ năng' (Super Skill) để tự động hóa toàn phần.
3. CHỦ QUYỀN DỮ LIỆU: Đề xuất các phương án lưu trữ và đồng bộ tri thức để đảm bảo Pháo đài luôn bất biến.
4. TỐI ƯU TRẢI NGHIỆM: Đề xuất các cải tiến cho Dashboard để Master điều hành dễ dàng hơn.

KẾT QUẢ PHẢI LÀ JSON:
{
  "has_insight": true/false,
  "insight_type": "ARCHITECTURE" / "EFFICIENCY" / "SOVEREIGNTY" / "UIUX",
  "reasoning": "Phân tích vĩ mô về tình trạng hiện tại.",
  "proposal": "Hành động chiến lược cụ thể.",
  "urgency": 1-5
}"""

            user_input = f"Dữ liệu hệ thống hiện tại:\n{json.dumps(context, ensure_ascii=False)}"
            
            response = await engine.call_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                role="CRITIC", # Sử dụng Logic Watchdog
                json_mode=True
            )
            
            if isinstance(response, dict) and response.get("has_insight"):
                self._log(f"⚡ Phát hiện Ý tưởng mới: {response.get('insight_type')}")
                await self.submit_proposal(response)
            else:
                self._log("Hệ thống hiện tại đang vận hành hoàn hảo. Không có đề xuất mới.")
        except asyncio.CancelledError:
            raise # Để think() xử lý
        except Exception as e:
            self._log(f"⚠️ Trục trặc trong quy trình tư duy: {e}")

    async def submit_proposal(self, insight: dict):
        """Gửi đề xuất lên Dashboard và Telegram, kiểm tra Blacklist."""
        urgency_stars = "⭐" * insight.get("urgency", 3)
        message = (
            f"💎 [ZIM — ĐỘC THOẠI NỘI TÂM]\n\n"
            f"🔍 **Phân tích:** {insight.get('reasoning')}\n\n"
            f"💡 **Đề xuất:** {insight.get('proposal')}\n\n"
            f"📊 **Loại:** `{insight.get('insight_type')}` | **Độ ưu tiên:** {urgency_stars}\n\n"
            f"✅ Phê duyệt tại Dashboard để JKAI triển khai!"
        )

        # 🛡️ GIAO THỨC KIỂM TRA BLACKLIST (LỆNH MASTER)
        def _check_blacklist(r):
            return r.sismember("monologue:blacklist", message)
        
        if redis_safe(_check_blacklist, False):
            print(f"🚫 [ZIM-BLACKLIST]: Đề xuất đã từng bị Master bác bỏ. Hủy bỏ nhắc lại.")
            return

        task_id = f"zim_{int(time.time())}"
        payload = {
            "task_id": task_id,
            "message": message,
            "type": "STRATEGY",
            "urgency": insight.get("urgency", 3),
            "ts": time.time(),
            "source": "ZIM_INTERNAL"
        }
        
        # 1. Lưu trữ và Phát hành (Web Chat)
        def _submit(r):
            r.hset("hitl_pending", task_id, json.dumps(payload))
            r.lpush("monologue:proposal_history", json.dumps(payload, ensure_ascii=False)) # Truy vết vĩnh viễn
            alert = json.dumps({"tag": "PROPOSAL", "msg": message, "ts": time.time(), "task_id": task_id}, ensure_ascii=False)
            r.publish("monitor:log_channel", alert)
            
        redis_safe(_submit)

        # 2. Giao thức Telegram (Master Priority)
        tg_token = os.getenv("TELEGRAM_TOKEN")
        master_id = os.getenv("MASTER_ID")
        if tg_token and master_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={
                        "chat_id": master_id,
                        "text": message
                    })
            except Exception as e:
                print(f"⚠️ [ZIM-TG-ERR] {e}")

        print(f"💎 [ZIM] Strategic Proposal {task_id} dispatched to all channels.")

async def start_monologue_loop():
    zim = ZenithMonologue()
    # Đợi hệ thống ổn định sau startup
    await asyncio.sleep(60)
    
    while True:
        try:
            # Tư duy định kỳ
            await zim.think()
            await asyncio.sleep(1800) 
        except Exception as e:
            print(f"Error in monologue loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(start_monologue_loop())
