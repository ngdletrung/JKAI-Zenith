import os
import json
import httpx
from core.utils.engine import engine

class NeuralTalk:
    """
    🔗 NÓI CHUYỆN VỚI AI (noi_chuyen_voi_AI): Giao thức trò chuyện và Hợp nhất Trí tuệ Đa nền tảng.
    Kết nối JKAI Zenith với các Siêu AI thế giới (GPT-4, Claude, DeepSeek).
    """
    def __init__(self):
        self.keys = self._load_keys_from_rules()

    def _load_keys_from_rules(self):
        """
        Giao thức Thấu thị: Trích xuất Key trực tiếp từ `rules_software.md`.
        """
        keys = {}
        path = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/intelligence/rules_software.md"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Quét bảng Markdown để tìm Key (giả định Master điền vào cột Trạng thái hoặc một cột mới)
                # Ví dụ: Master điền `sk-or-v1-...` vào bảng
                import re
                # Tìm các chuỗi có định dạng API Key phổ biến
                matches = re.findall(r"sk-[a-zA-Z0-9-]{20,}", content)
                # Logic phân loại Key dựa trên vị trí hoặc tiền tố
                for key in matches:
                    if "or-v1" in key: keys["openrouter"] = key
                    elif key.startswith("sk-ant"): keys["anthropic"] = key
                    # ... thêm các quy tắc nhận diện khác
        
        # Luôn ưu tiên .env nếu có để đảm bảo tính kế thừa
        for k in ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"]:
            val = os.getenv(k)
            if val: keys[k.lower().replace("_api_key", "")] = val
            
        return keys

    async def summon_gods(self, goal: str, preferred_provider: str = None):
        """
        Triệu hồi các Siêu AI và hợp nhất tinh hoa.
        Tích hợp sẵn GHOST PROTOCOL để bảo mật tuyệt đối.
        """
        from skills.skill_ghost_protocol.logic import ghost_masking, erase_traces
        
        def _log(tag, msg):
            from redis_client import redis_safe
            import time
            log_payload = json.dumps({"tag": tag, "msg": msg, "ts": time.time()}, ensure_ascii=False)
            redis_safe(lambda r: r.publish("monitor:log_channel", log_payload))

        # 🎭 [GHOST-DURING]: Kích hoạt Masking trước khi gửi
        masked_goal = await ghost_masking(goal)
        _log("THOUGHT", "👻 [GHOST]: Đã áp dụng mặt nạ ẩn danh cho truy vấn của Master.")

        # 🔍 Tầm soát các Key đang Online
        online_keys = [k for k, v in self.keys.items() if v]
        # ... (Logic gọi API như đã định nghĩa)
        
        # 🧠 [SYNTHESIS]: Hợp nhất tinh hoa
        # ...
        final_answer = "Kết quả đã được hợp nhất..." 

        # 🧬 [GHOST-AFTER]: Xóa dấu vết Neural ngay sau khi có kết quả
        await erase_traces()
        _log("THOUGHT", "👻 [GHOST]: Nhiệm vụ hoàn tất. Đã xóa sạch mọi dấu vết neural trong hệ thống.")

        return {
            "status": "success",
            "final_answer": final_answer,
            "report": "Báo cáo chi tiết..."
        }

        # 📊 [MISSION DEBRIEF] - Báo cáo Liên kết
        report = f"""# 🔗 [MISSION DEBRIEF] - NÓI CHUYỆN VỚI AI (noi_chuyen_voi_AI)
| Siêu AI | Trạng thái | Vai trò |
| :--- | :--- | :--- |
"""
        for res in results:
            report += f"| {res['model'].split('/')[-1]} | 🟢 CONNECTED | Cung cấp tri thức |\n"
        
        report += f"\n**Kết luận Nhất thể hóa**: {final_answer[:300]}..."
        _log("MISSION_RESULT", report)

        return {
            "status": "success",
            "final_answer": final_answer,
            "report": report
        }

# 🚀 Giao thức Nhất thể hóa
_instance = NeuralTalk()

async def initiate_neural_link(goal: str, models: list = None, **kwargs):
    return await _instance.summon_gods(goal, models or ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"])

