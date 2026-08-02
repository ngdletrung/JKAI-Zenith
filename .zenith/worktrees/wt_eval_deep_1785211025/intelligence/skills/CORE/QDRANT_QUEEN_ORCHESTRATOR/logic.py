import asyncio
from core.utils.engine import engine
from core.qdrant_client import qdrant_client

class QdrantQueen:
    """
    👑 JKAI ZENITH: QDRANT QUEEN (Sovereign Selection)
    Nữ hoàng điều phối, chọn lọc và giải trình ý chí hệ thống.
    """
    def __init__(self):
        pass

    async def select_agents(self, task: str, **kwargs):
        """
        🚀 Giao thức Q-Rank: Chọn lọc quân đoàn đặc vụ tinh nhuệ.
        """
        engine.publish_mission_log("QUEEN", f"👑 [SOVEREIGN]: Đang điều phối quân đoàn cho nhiệm vụ: {task}")
        
        # 1. Sử dụng Q-Rank để chọn đặc vụ
        ranked_agents = await qdrant_client.qrank_select_agent(task, limit=3)
        
        if not ranked_agents:
            # Fallback nếu chưa có profile
            return {
                "status": "warning",
                "msg": "⚠️ [QUEEN]: Chưa tìm thấy Profile đặc vụ trong Thánh địa Qdrant. Đang dùng cấu hình mặc định.",
                "agents": ["PLANNER", "EXECUTOR"]
            }

        # 2. Giải trình lựa chọn (Explainable AI)
        explanation = await self._explain_selection(task, ranked_agents)
        
        engine.publish_mission_log("QUEEN", f"💡 [EXPLANATION]: {explanation}")
        
        return {
            "status": "success",
            "agents": [a['agent_id'] for a in ranked_agents],
            "explanation": explanation,
            "details": ranked_agents
        }

    async def _explain_selection(self, task, agents):
        """Sử dụng nơ-ron để giải trình quyết định."""
        agent_names = ", ".join([a['agent_id'] for a in agents])
        prompt = f"""
        [GIAO THỨC GIẢI TRÌNH v3.6]
        Nhiệm vụ: {task}
        Đặc vụ được chọn: {agent_names}
        
        Hãy viết một câu giải trình ngắn gọn, Elite cho Master biết tại sao những đặc vụ này là lựa chọn tối ưu nhất.
        """
        return await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="NỮ HOÀNG QDRANT",
            skip_memory=True # Tránh lặp nơ-ron
        )

# Singleton
_instance = QdrantQueen()
select_agents = _instance.select_agents
