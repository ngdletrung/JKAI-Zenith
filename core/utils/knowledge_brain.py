import os
import json
import logging
import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional

from core.qdrant_client import qdrant_client
from core.utils.engine import engine
from core.config import settings

logger = logging.getLogger('KnowledgeBrain')

COLLECTION_MAP = {
    "JKAI_KNOWLEDGE": "jkai_knowledge",
    "JKAI_MEMORY": "jkai_memory",
    "JKAI_REASONING": "jkai_reasoning_bank",
    "JKAI_EXTERNAL": "jkai_external",
}

class KnowledgeBrain:
    def __init__(self):
        self.collections = {
            "KNOWLEDGE": COLLECTION_MAP["JKAI_KNOWLEDGE"],
            "MEMORY": COLLECTION_MAP["JKAI_MEMORY"],
            "REASONING": COLLECTION_MAP["JKAI_REASONING"],
        }
        self.summarizer_role = "SUMMARIZER"
        self.embedder_role = "EMBEDDER"
        self.initialized_collections = set()
        self._cache_ttl = 300
        self._cache_prefix = "brain_cache:"
        self.batch_size = 64

    def _log(self, tag: str, msg: str, task_id: str = "brain"):
        try:
            engine.publish_mission_log(f"BRAIN:{tag}", msg, task_id)
        except Exception:
            pass

    async def initialize(self, collection: str = None):
        target = collection or self.collections["KNOWLEDGE"]
        if target in self.initialized_collections:
            return
        v_size = await engine.get_vector_size(self.embedder_role)
        await qdrant_client.ensure_collection(target, vector_size=v_size)
        self.initialized_collections.add(target)

    async def ask(self, query: str, limit: int = 5, tier: int = 2, task_id: str = "knowledge_inquiry",
                  role: str = None, collection: str = None) -> str:
        target = collection or self.collections["KNOWLEDGE"]
        await self.initialize(target)

        filter_dict = {}
        if role:
            role_map = {
                "PLANNER": ["planner", "refined", "rules", "patterns", "training", "reasoning"],
                "EXECUTOR": ["executor", "refined", "tools", "skills", "training"],
                "RECEPTIONIST": ["reasoning", "refined", "agents", "knowledge", "training"],
                "STEWARD": ["rules", "protocols", "training"],
            }
            target_categories = role_map.get(role.upper(), ["universal", "training"])
            filter_dict = {"category": target_categories}

        import hashlib
        cache_key = self._cache_prefix + hashlib.md5(
            f"{query}:{tier}:{limit}:{role}:{target}".encode()
        ).hexdigest()
        try:
            cached = engine._get_redis().get(cache_key)
            if cached:
                return cached.decode("utf-8") if isinstance(cached, bytes) else cached
        except Exception:
            pass

            from core.knowledge_sources.retriever import retriever
            res = await retriever.search(query, top_k=limit, sources=[target], filter_dict=filter_dict)
            if not res.results:
                return ""

            knowledge_chunks = []
            sources = set()
            for r in res.results:
                payload = r.get("payload", {})
                content = payload.get("content") or payload.get("text", "")
                source = payload.get("path") or payload.get("metadata", {}).get("path") or payload.get("rel_path") or "Unknown"
                knowledge_chunks.append(f"--- SOURCE: {source} ---\n{content}")
                sources.add(os.path.basename(str(source)))

            raw_knowledge = "\n\n".join(knowledge_chunks)
            source_list = ", ".join(list(sources))

            if tier == 1:
                result = f"[TIER-1: RAW]\n{raw_knowledge}\n\n[NGUON]: {source_list}"
                try:
                    engine._get_redis().setex(cache_key, self._cache_ttl, result)
                except Exception:
                    pass
                return result

            if tier == 2:
                safe_knowledge = raw_knowledge[:3000]
                prompt = (
                    f"Dưới đây là tri thức trích xuất từ Kho dữ liệu JKAI (Lãnh thổ `{target}`) về chủ đề: '{query}'.\n"
                    f"TRI THỨC TRÍCH XUẤT:\n{safe_knowledge}\n\n"
                    f"YÊU CẦU: Ngôn ngữ Tiếng Việt, hào sảng, chuyên nghiệp, chỉ lấy thông tin có trong nguồn."
                )
                summary = await engine.call_chat(
                    messages=[{"role": "user", "content": prompt}],
                    role=self.summarizer_role,
                    task_id=task_id,
                )
                return f"{summary}\n\n📚 [NGUỒN]: {source_list}"

            if tier == 3:
                prompt = (
                    f"CHÀO MỪNG TỚI TẦNG MINH TRIẾT JKAI ZENITH.\nChủ đề: '{query}'\n\nDỮ LIỆU:\n{raw_knowledge}\n\n"
                    f"NHIỆM VỤ: Phân tích chiến lược đa tầng dựa trên dữ liệu trên và 12 Trụ cột DNA."
                )
                analysis = await engine.call_chat(
                    messages=[{"role": "user", "content": prompt}],
                    role="PLANNER",
                    task_id=task_id,
                )
                result = f"[TIER-3: STRATEGIC ANALYSIS]\n{analysis}\n\n[NGUON]: {source_list}"
                try:
                    engine._get_redis().setex(cache_key, self._cache_ttl, result)
                except Exception:
                    pass
                return result

        except Exception as e:
            logger.error(f"[BRAIN-QUERY-ERR]: {e}")
            return f"[BRAIN-ERR]: {e}."

    async def distill_experience(self, mission_log: str, task_id: str = "distillation"):
        target = self.collections["MEMORY"]
        await self.initialize(target)
        prompt = (
            f"Phân tích Nhật ký Sứ mệnh `{task_id}` và trích xuất 'Success Strategies' & 'Learnings'.\n\nLOG:\n{mission_log}"
        )
        distilled_wisdom = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role=self.summarizer_role,
            task_id=task_id,
        )

        if distilled_wisdom:
            embedding = await engine.get_embeddings(distilled_wisdom)
            if embedding:
                await qdrant_client.upsert_intel(
                    text=distilled_wisdom,
                    embedding=embedding,
                    collection=target,
                    metadata={
                        "path": f"mission_wisdom/{task_id}.md",
                        "type": "distilled_experience",
                        "source": "wisdom",
                        "memory_type": "wisdom",
                        "timestamp": time.time(),
                        "task_id": task_id,
                    },
                )
                return distilled_wisdom
        return None

    async def sync_all(self, task_id: str = "sys_sync"):
        from core.knowledge_sources.pipeline import ingestion_pipeline

        self._log("SYNC", f"Khoi dong KnowledgeSources Sync cho {task_id}", task_id)
        stats = await ingestion_pipeline.ingest_directory(
            directory=settings.INTELLIGENCE_DIR,
            source_id="intelligence",
            file_type_tag="docs",
            task_id=task_id,
        )
        res_msg = (
            f"[SYNC-COMPLETE]: Đã xử lý {stats.get('scanned', 0)} tệp "
            f"({stats.get('new', 0)} mới, {stats.get('updated', 0)} cập nhật, "
            f"{stats.get('skipped', 0)} bỏ qua)."
        )
        self._log("SYNC", res_msg, task_id)
        return stats


knowledge_brain = KnowledgeBrain()
