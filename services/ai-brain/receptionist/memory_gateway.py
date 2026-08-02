import json
from core.utils.engine import engine

class MemoryGateway:
    """
     TẬP ĐOÀN JKAI ZENITH - MEMORY GATEWAY
    Quản lý Cortex 3 lớp và lọc dữ liệu bộ nhớ.
    """
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except Exception: pass

    def get_session_id(self, task_id: str) -> str:
        session_id = task_id
        if "_" in task_id:
            parts = task_id.split("_")
            if len(parts) >= 2:
                session_id = f"{parts[0]}_{parts[1]}"
        return session_id

    def load_history(self, task_id: str):
        """Lấy 10 tin nhắn gần nhất từ Redis"""
        session_id = self.get_session_id(task_id)
        if not self.redis_conn:
            return []
        try:
            history_key = f"chat_history:{session_id}"
            raw_history = self.redis_conn.lrange(history_key, 0, 9)
            return [json.loads(m) for m in reversed(raw_history)]
        except Exception as e:
            self._log("DEBUG", f"[RECEPTIONIST-HISTORY-LOAD-ERR] {e}", task_id)
            return []

    async def fetch_neural_context(self, goal: str) -> str:
        """Kéo dữ liệu từ Qdrant jkai_memory (episodic memory)"""
        mem_context = ""
        try:
            from core.qdrant_client import qdrant_client
            from core.utils.embed import embed
            vector = await embed.get_embedding_async(goal[:1000])
            if vector:
                memories = await qdrant_client.search_similar(vector, limit=3, collection="jkai_memory")
                if memories:
                    mem_context = "\n\n---\n️ [TRUY XUẤT KÝ ỨC] thưa Master:\n"
                    for m in memories:
                        payload = m.get('payload', {})
                        text = payload.get('text', '')[:200]
                        mem_type = payload.get('memory_type', 'memory')
                        mem_context += f"\n [{mem_type}] {text}"
        except Exception as e:
            pass
        return mem_context

    def clean_history(self, history: list) -> list:
        """️ [ELITE FILTER]: Lọc tin rác khỏi neural context"""
        clean_history = []
        for h in history[-10:]:
            content = h.get("content", "")
            if len(content) > 50 and len(set(content)) < 15: 
                continue 
            clean_history.append(h)
        return clean_history
