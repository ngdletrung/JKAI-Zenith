import json
from core.utils.engine import engine

class MemoryGateway:
    """
    🧠 TẬP ĐOÀN JKAI ZENITH - MEMORY GATEWAY
    Quản lý Cortex 3 lớp và lọc dữ liệu bộ nhớ.
    """
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

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
        """Kéo dữ liệu từ Vector Semantic Memory (3-Layer Cortex)"""
        mem_context = ""
        try:
            from semantic_memory import memory
            mem_idx = await memory.search_index(goal, limit=5)
            if mem_idx:
                top_ids = [m["id"] for m in mem_idx[:2]]
                past_memories = await memory.get_details(top_ids)
                
                mem_context = "\n\n---\n🏛️ [TRUY XUẤT VỎ NÃO THẦN KINH] thưa Master:\n"
                mem_context += "📊 Ký ức liên quan (Chỉ mục):\n"
                mem_context += "\n".join([f"- [#{m['id']}] {m['summary']} (Score: {m['score']:.2f})" for m in mem_idx])
                
                if past_memories:
                    mem_context += "\n\n📖 Chi tiết Ký ức Chiến lược:\n"
                    mem_context += "\n".join([f"💎 Observation #{m.get('task_id', '??')}: {m['text']}" for m in past_memories])
        except Exception as e:
            pass
        return mem_context

    def clean_history(self, history: list) -> list:
        """🛡️ [ELITE FILTER]: Lọc tin rác khỏi neural context"""
        clean_history = []
        for h in history[-10:]:
            content = h.get("content", "")
            if len(content) > 50 and len(set(content)) < 15: 
                continue 
            clean_history.append(h)
        return clean_history
