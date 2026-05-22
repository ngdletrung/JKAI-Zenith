import json
import time
from typing import List, Dict, Any, Optional
from core.qdrant_client import qdrant_client
from core.utils.embed import embed

class ReasoningBank:
    """
    🧠 [REASONING-BANK]: Đại thư viện nơ-ron tư duy.
    Lưu trữ các mẫu Chain-of-Thought, quyết định kiến trúc và gỡ lỗi thành công.
    Giúp AI "học cách suy nghĩ" từ di sản.
    """
    def __init__(self, collection_name: str = "jkai_reasoning_bank"):
        self.collection = collection_name

    async def memorize(self, goal: str, thought: str, success_score: float = 1.0, tags: List[str] = None):
        """Nhập tâm một mẫu tư duy thành công."""
        vector = embed(goal)
        if not vector: return
        
        payload = {
            "goal": goal,
            "thought": thought,
            "score": success_score,
            "tags": tags or [],
            "timestamp": time.time()
        }
        await qdrant_client.upsert_point(self.collection, vector, payload)

    async def recall(self, goal: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Truy xuất các nơ-ron tư duy tương đồng."""
        vector = embed(goal)
        if not vector: return []
        
        results = await qdrant_client.search_similar(vector, collection=self.collection, limit=limit)
        return [r.get("payload") for r in results if r.get("score", 0) > 0.85]

# Singleton
reasoning_bank = ReasoningBank()
