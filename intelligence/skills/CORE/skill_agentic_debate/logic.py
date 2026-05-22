import json
import asyncio
from core.utils.engine import engine

class CouncilOfMinds:
    """
    🧠 COUNCIL OF MINDS: Giao thức Tranh luận Đa phương JKAI Zenith.
    Cho phép các Đặc vụ tranh luận để tìm ra giải pháp tối ưu nhất.
    """
    def __init__(self):
        self.roles = ["ARCHITECT", "CRITIC", "ARBITER"]

    async def initiate_debate(self, goal: str, context: str = "", rounds: int = 2):
        """
        Khởi động phiên tranh luận giữa các Đặc vụ.
        """
        debate_history = []
        current_proposal = ""
        
        def _log(tag, msg):
            from redis_client import redis_safe
            import time
            log_payload = json.dumps({"tag": tag, "msg": msg, "ts": time.time()}, ensure_ascii=False)
            redis_safe(lambda r: r.publish("monitor:log_channel", log_payload))

        _log("THOUGHT", f"🧠 [COUNCIL]: Khởi tạo Hội đồng Trí tuệ. Mục tiêu: {goal}")

        # B1: ARCHITECT đưa ra bản thiết kế đầu tiên
        _log("THOUGHT", "🧠 [ARCHITECT]: Đang phác thảo bản thiết kế chiến lược ban đầu...")
        architect_prompt = f"Mục tiêu: {goal}\nBối cảnh: {context}\nHãy đưa ra một giải pháp toàn diện và tối ưu nhất."
        current_proposal = await engine.call_chat(
            messages=[{"role": "user", "content": architect_prompt}],
            role="PLANNER"
        )
        debate_history.append({"role": "ARCHITECT", "content": current_proposal})

        for r in range(rounds):
            # B2: CRITIC tìm lỗi và phản biện
            _log("THOUGHT", f"🧠 [CRITIC]: Đang thực hiện phản biện vòng {r+1}...")
            critic_prompt = f"Mục tiêu: {goal}\nGiải pháp hiện tại: {current_proposal}\nHãy tìm ra các lỗ hổng, rủi ro hoặc điểm chưa tối ưu."
            critic_feedback = await engine.call_chat(
                messages=[{"role": "user", "content": critic_prompt}],
                role="CRITIC"
            )
            debate_history.append({"role": f"CRITIC (Vòng {r+1})", "content": critic_feedback})

            # B3: ARCHITECT điều chỉnh giải pháp
            _log("THOUGHT", f"🧠 [ARCHITECT]: Đang tiếp thu phản biện và tối ưu hóa bản thiết kế...")
            architect_refine_prompt = f"Phản biện từ Critic: {critic_feedback}\nHãy điều chỉnh lại giải pháp của bạn."
            current_proposal = await engine.call_chat(
                messages=[{"role": "user", "content": architect_refine_prompt}],
                role="PLANNER"
            )
            debate_history.append({"role": f"ARCHITECT (Tối ưu {r+1})", "content": current_proposal})

        # B4: ARBITER đưa ra phán quyết cuối cùng
        _log("THOUGHT", "🧠 [ARBITER]: Đang tổng hợp các luồng tư duy để đưa ra phán quyết cuối cùng...")
        arbiter_prompt = f"Lịch sử tranh luận: {json.dumps(debate_history, ensure_ascii=False)}\nHãy đưa ra quyết định cuối cùng Elite nhất cho Master."
        final_decision = await engine.call_chat(
            messages=[{"role": "user", "content": arbiter_prompt}],
            role="RECEPTIONIST"
        )

        # 📊 [MISSION DEBRIEF] - Báo cáo kết quả Hội đồng
        report = f"""# 🧠 [MISSION DEBRIEF] - HỘI ĐỒNG TRÍ TUỆ
| Đặc vụ | Hành động | Kết quả |
| :--- | :--- | :--- |
| **Architect** | Thiết kế & Tối ưu | {rounds+1} phiên bản |
| **Critic** | Phản biện đa chiều | {rounds} vòng kiểm định |
| **Arbiter** | Phán quyết cuối cùng | 🟢 Đã ban hành |

**Kết luận Chiến lược**: {final_decision[:300]}...
"""
        _log("MISSION_RESULT", report)

        return {
            "status": "success",
            "final_decision": final_decision,
            "report": report
        }

# 🚀 Giao thức Nhất thể hóa
_instance = CouncilOfMinds()

async def initiate_agentic_debate(goal: str, **kwargs):
    res = await _instance.initiate_debate(goal, **kwargs)
    return res
