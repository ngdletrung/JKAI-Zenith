import time
from typing import Dict, Optional

COLLECTION_KNOWLEDGE = "jkai_knowledge"
COLLECTION_MEMORY = "jkai_memory"
COLLECTION_REASONING = "jkai_reasoning_bank"
COLLECTION_EXTERNAL = "jkai_external"


class KnowledgeSources:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    async def sync_all(self, directories: list = None, task_id: str = "ks_sync") -> Dict:
        from core.knowledge_sources.pipeline import ingestion_pipeline
        from core.config import settings

        if directories is None:
            directories = [settings.INTELLIGENCE_DIR]

        results = {}
        for d in directories:
            stats = await ingestion_pipeline.ingest_directory(
                directory=d,
                source_id=os.path.basename(d) if os.path.isdir(d) else "local",
                task_id=task_id,
            )
            results[os.path.basename(d) if os.path.isdir(d) else d] = stats

        return {
            "status": "completed",
            "task_id": task_id,
            "results": results,
            "elapsed": time.time(),
        }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        include_external: bool = False,
        filter_dict: dict = None,
    ) -> Dict:
        from core.knowledge_sources.retriever import retriever

        result = await retriever.search(
            query=query,
            top_k=top_k,
            include_external=include_external,
            filter_dict=filter_dict,
        )
        structured = []
        for r in result.results:
            p = r.get("payload", {})
            structured.append({
                "content": p.get("text", ""),
                "source": p.get("rel_path") or p.get("filename", "unknown"),
                "score": r.get("_ranked_score", r.get("score", 0.0)),
                "type": p.get("source") or p.get("memory_type") or "knowledge",
                "collection": r.get("_collection", "unknown"),
            })

        return {
            "query": query,
            "results": structured,
            "sources": result.sources,
            "elapsed": result.elapsed,
        }

    async def get_status(self) -> Dict:
        from core.knowledge_sources.metadata import metadata_db

        sources = metadata_db.list_sources()
        return {
            "collections": {
                COLLECTION_KNOWLEDGE: "active",
                COLLECTION_MEMORY: "active",
                COLLECTION_REASONING: "active",
                COLLECTION_EXTERNAL: "ready",
            },
            "sources": sources,
            "total_sources": len(sources),
        }


import os
knowledge_sources = KnowledgeSources()
