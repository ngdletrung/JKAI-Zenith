import json
import asyncio
from core.utils.engine import engine

class OmniEvolution:
    """
    🌀 OMNI-EVOLUTION: Giao thức Tự tiến hóa Độc lập JKAI Zenith.
    Tự học công nghệ mới và đề xuất nâng cấp hệ thống.
    """
    def __init__(self):
        self.focus_areas = ["LLM Optimization", "FastAPI Patterns", "Docker Security", "React Performance"]

    async def scan_for_evolution(self, focus_area: str = None):
        """
        Quét các nguồn tri thức và đề xuất nâng cấp.
        """
        def _log(tag, msg):
            from redis_client import redis_safe
            import time
            log_payload = json.dumps({"tag": tag, "msg": msg, "ts": time.time()}, ensure_ascii=False)
            redis_safe(lambda r: r.publish("monitor:log_channel", log_payload))

        target = focus_area or self.focus_areas[0]
        _log("THOUGHT", f"🌀 [OMNI-EVOLVE]: Đang khởi động cảm biến, tầm soát công nghệ mới trong lĩnh vực: `{target}`...")

        # 1. Thu thập dữ liệu từ Web (Giả lập thông qua tri thức hiện tại của AI)
        research_prompt = f"Hãy tìm kiếm và phân tích các xu hướng, kỹ thuật mới nhất (năm 2024-2026) về `{target}` có thể áp dụng cho một hệ thống AI Microservices."
        tech_intel = await engine.call_chat(
            messages=[{"role": "user", "content": research_prompt}],
            role="PLANNER"
        )

        # 2. Phân tích hiện trạng hệ thống
        _log("THOUGHT", "🧠 [OMNI-EVOLVE]: Đang so chiếu với kiến trúc hiện tại của JKAI Zenith...")
        
        # 3. Đưa ra đề xuất tiến hóa Elite
        proposal_prompt = f"""Dựa trên tri thức mới: {tech_intel}
        Hãy đưa ra một ĐỀ XUẤT TIẾN HÓA CHIẾN LƯỢC cho Master LeeTrung.
        Đề xuất phải bao gồm:
        1. ⚡ TÊN NÂNG CẤP
        2. 🎯 TẠI SAO CẦN (Lý do kỹ thuật)
        3. 🛠️ CÁCH THỰC HIỆN (Các bước thay đổi code)
        4. 💎 GIÁ TRỊ MANG LẠI
        """
        
        final_proposal = await engine.call_chat(
            messages=[{"role": "user", "content": proposal_prompt}],
            role="CRITIC" # Dùng Critic để đảm bảo tính khắt khe của đề xuất
        )

        # 📊 [MISSION DEBRIEF] - Báo cáo Tiến hóa
        report = f"""# 🌀 [MISSION DEBRIEF] - OMNI-EVOLUTION SCAN
| Lĩnh vực | Trạng thái | Đề xuất |
| :--- | :--- | :--- |
| **{target}** | 🟢 Đã tầm soát | 💎 1 Đề xuất mới |

**Kiến nghị từ AI**: {final_proposal[:300]}...
"""
        _log("MISSION_RESULT", report)

        return {
            "status": "success",
            "intel": tech_intel,
            "proposal": final_proposal,
            "report": report
        }

# 🚀 Giao thức Nhất thể hóa
_instance = OmniEvolution()

async def initiate_evolution_scan(focus_area: str = None, **kwargs):
    return await _instance.scan_for_evolution(focus_area)
