import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from core.utils.engine import engine
from core.qdrant_client import qdrant_client
from core.utils.embed import embed

# Industrial Logging
logger = logging.getLogger(__name__)

class SAFLANeural:
    """
    🧠 JKAI ZENITH: SAFLA NEURAL (Self-Aware Feedback Loop Algorithm)
    Hệ thần kinh ký ức tự học 4 tầng bộ nhớ.
    Đảm bảo tri thức luôn được kế thừa và tối ưu hóa thời gian thực.
    """
    
    def __init__(self):
        self.working_memory: List[Dict[str, Any]] = [] # RAM (Working Tier)
        self.max_working_size = 10
        self.collections = {
            "semantic": "jkai_semantic_knowledge",
            "episodic": "jkai_episodic_memory"
        }

    async def assimilate(self, text: str, tier: str = "episodic", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        📥 Giao thức NHẬP TÂM: Khắc tri thức vào Thánh địa Qdrant.
        """
        try:
            vector = embed(text)
            if not vector:
                return {"status": "error", "message": "Embedding failure"}
            
            collection = self.collections.get(tier, self.collections["episodic"])
            
            # Thực thi cấy ghép thực tế
            success = await qdrant_client.upsert_intel(
                text=text,
                embedding=vector,
                metadata={
                    **(metadata or {}),
                    "tier": tier,
                    "timestamp": time.time(),
                    "sovereign_id": "ZENITH-v4.4"
                }
            )
            
            if success:
                engine.publish_mission_log("SAFLA", f"🧠 [ASSIMILATE]: Tri thức đã được nhập tâm vào tầng {tier.upper()}.")
                return {"status": "success"}
            return {"status": "error", "message": "Qdrant upsert failed"}
            
        except Exception as e:
            logger.error(f"Assimilation error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def recall(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        🔍 Giao thức TRUY HỒI: Lục tìm ký ức đa tầng.
        """
        try:
            vector = embed(query)
            if not vector:
                return {"status": "error", "message": "Embedding failure"}
            
            # Tìm kiếm song song trên các tầng ký ức
            tasks = [
                qdrant_client.search_similar(vector, limit=limit, collection=self.collections["semantic"]),
                qdrant_client.search_similar(vector, limit=limit, collection=self.collections["episodic"])
            ]
            
            results = await asyncio.gather(*tasks)
            semantic_hits, episodic_hits = results
            
            # Hợp nhất và xếp hạng ký ức
            unified_memory = {
                "working": self.working_memory,
                "semantic": semantic_hits,
                "episodic": episodic_hits,
                "query": query
            }
            
            engine.publish_mission_log("SAFLA", f"🔍 [RECALL]: Đã truy hồi được {len(semantic_hits) + len(episodic_hits)} mảnh ký ức liên quan.")
            return {"status": "success", "memory": unified_memory}
            
        except Exception as e:
            logger.error(f"Recall error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def forge_concept(self, sources: List[str]) -> Dict[str, Any]:
        """
        🔥 Giao thức ĐÚC KHÁI NIỆM: Tổng hợp tri thức rời rạc thành quy luật.
        """
        try:
            source_text = "\n".join(sources)
            prompt = f"""
            [GIAO THỨC ĐÚC KHÁI NIỆM SAFLA]
            Dữ liệu nguồn:
            {source_text}
            
            Hãy tổng hợp những dữ liệu trên thành một quy luật hoặc khái niệm vĩ mô (Semantic Concept) để JKAI ghi nhớ mãi mãi.
            """
            
            concept = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="BỘ NÃO SAFLA",
                skip_memory=True
            )
            
            # Lưu khái niệm mới vào tầng Semantic
            await self.assimilate(concept, tier="semantic", metadata={"type": "forged_concept"})
            
            engine.publish_mission_log("SAFLA", "🔥 [FORGE]: Khái niệm vĩ mô mới đã được đúc thành công.")
            return {"status": "success", "concept": concept}
            
        except Exception as e:
            logger.error(f"Forge error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def update_working_memory(self, item: Dict[str, Any]):
        """Cập nhật tầng Working Memory (RAM)."""
        self.working_memory.append(item)
        if len(self.working_memory) > self.max_working_size:
            self.working_memory.pop(0)

# Singleton
_instance = SAFLANeural()

async def execute(action: str, **kwargs) -> Any:
    func = getattr(_instance, action, None)
    if func and asyncio.iscoroutinefunction(func):
        return await func(**kwargs)
    raise ValueError(f"Action '{action}' not recognized.")

# Legacy
assimilate = _instance.assimilate
recall = _instance.recall
forge_concept = _instance.forge_concept
