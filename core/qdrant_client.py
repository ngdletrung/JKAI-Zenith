import os
import httpx
import json
import uuid
import logging
import time
import asyncio
from typing import Any, List, Dict, Optional

logger = logging.getLogger("QdrantClient")

class QdrantClientWrapper:
    def __init__(self):
        from core.config import IS_DOCKER
        env_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        if not IS_DOCKER and ("qdrant" in env_url or "rag-service" in env_url):
            self.url = env_url.replace("qdrant", "localhost").replace("rag-service", "localhost")
        else:
            self.url = env_url
        self.collection_name = "jkai_zenith_intel"
        self._async_client = None
        
        # 💎 [NEURAL-CACHE]: Bo nho dem trang thai Thanh dia thua Master
        # Tranh viec spam GET /collections lien tuc
        self._collection_cache = set()
        
        # 🚥 [TRAFFIC-CONTROL]: Semaphore de tranh DDOS noi bo thua Master
        self._semaphore = asyncio.Semaphore(16)

    def _get_async_client(self):
        if self._async_client is None:
            # Tang timeout cho cac tac vu batch lon
            self._async_client = httpx.AsyncClient(timeout=60.0)
        return self._async_client

    async def get_collections(self):
        """Lay danh sach cac Collection hien co."""
        try:
            client = self._get_async_client()
            resp = await client.get(f"{self.url}/collections")
            if resp.status_code == 200:
                cols = resp.json().get("result", {}).get("collections", [])
                # Cap nhat cache luon
                for c in cols:
                    self._collection_cache.add(c.get('name'))
                return cols
        except Exception as e:
            logger.error(f"[QDRANT-LIST-ERR] {e}")
        return []

    async def ensure_collection(self, collection_name: str = None, vector_size: int = 768):
        """Dam bao Collection da san sang va tuong thich kich thuoc."""
        target = collection_name or self.collection_name
        
        # 🚀 [FAST-PATH]: Neu da co trong cache thi van kiem tra so bo thưa Ngai
        if target in self._collection_cache:
            return True
            
        try:
            client = self._get_async_client()
            # Kiem tra thuc te va kich thuoc
            resp = await client.get(f"{self.url}/collections/{target}")
            if resp.status_code == 200:
                current_config = resp.json().get("result", {}).get("config", {}).get("params", {}).get("vectors", {})
                current_size = current_config.get("size")
                
                if current_size != vector_size:
                    logger.warning(f"⚠️ [QDRANT-MISMATCH]: Collection `{target}` co kich thuoc {current_size} nhung yeu cau {vector_size}. Dang tai cau truc...")
                    # 🏛️ [TOP-DOWN-LOG]: Thong bao cho Master qua kenh chinh thuc
                    from core.utils.mission_bus import mission_bus
                    mission_bus.publish_log("AUDIT:qdrant_client.py", f"🔄 [NEURAL-RESIZE]: Tái cấu trúc `{target}` ({current_size} -> {vector_size}) để đồng bộ tri thức.")
                    await client.delete(f"{self.url}/collections/{target}")
                else:
                    self._collection_cache.add(target)
                    return True
            
            # Tao moi hoac tai cau truc
            logger.info(f"[QDRANT] Creating/Re-initializing collection: {target} (Size: {vector_size})")
            await client.put(f"{self.url}/collections/{target}", json={
                "vectors": { "size": vector_size, "distance": "Cosine" },
                "optimizers_config": {
                    "indexing_threshold": 20000,
                    "flush_interval_sec": 30
                }
            })
            self._collection_cache.add(target)
            return True
        except Exception as e:
            logger.error(f"[QDRANT-INIT-ERR] {e}")
            return False

    async def upsert_batch(self, points: List[Dict], collection: str = None, vector_size: int = 768):
        """🚀 [BLITZ-INGESTION]: Nap no-ron theo lo (Batch) thua Master."""
        if not points: return True
        target_collection = collection or self.collection_name
        await self.ensure_collection(target_collection, vector_size=vector_size)
        
        payload = {"points": points}
        
        async with self._semaphore:
            try:
                client = self._get_async_client()
                resp = await client.put(f"{self.url}/collections/{target_collection}/points", json=payload)
                return resp.status_code == 200
            except Exception as e:
                logger.error(f"[QDRANT-BATCH-ERR] {e}")
                return False

    async def upsert_intel(self, text: str, embedding: list, metadata: dict = None, collection: str = None, vector_size: int = 768):
        """Chen tri thuc moi vao Loi Qdrant."""
        if not embedding: return False
        point = {
            "id": str(uuid.uuid4()),
            "vector": embedding,
            "payload": { "text": text, **(metadata or {}) }
        }
        return await self.upsert_batch([point], collection, vector_size)

    async def search_similar(self, query_embedding: list, limit: int = 5, collection: str = None, filter_dict: dict = None):
        """Truy luc tri thuc tuong dong."""
        if not query_embedding: return []
        target_collection = collection or self.collection_name
        await self.ensure_collection(target_collection)
        
        payload = {
            "vector": query_embedding,
            "top": limit,
            "with_payload": True
        }
        
        if filter_dict:
            must_filters = []
            for k, v in filter_dict.items():
                if isinstance(v, list):
                    must_filters.append({"key": k, "match": {"any": v}})
                else:
                    must_filters.append({"key": k, "match": {"value": v}})
            payload["filter"] = {"must": must_filters}

        async with self._semaphore:
            try:
                client = self._get_async_client()
                resp = await client.post(f"{self.url}/collections/{target_collection}/points/search", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("result", [])
            except Exception as e:
                logger.error(f"[QDRANT-SEARCH-ERR] {e}")
        return []

    async def upsert_agent_profile(self, agent_id: str, description: str, embedding: list, metadata: dict = None):
        """Ghi danh Dac vu vao Thanh dia Qdrant."""
        point = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id)),
            "vector": embedding,
            "payload": {
                "agent_id": agent_id,
                "description": description,
                "metadata": metadata or {"reliability_boost": 1.0}
            }
        }
        return await self.upsert_batch([point], "jkai_agent_profiles")

    async def upsert_skill(self, skill_id: str, name: str, description: str, embedding: list, rating: int = 100, features: list = None, tier: str = "Unknown"):
        """Ghi danh Ky nang vao Coi Vinh Hang Qdrant."""
        point = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, skill_id)),
            "vector": embedding,
            "payload": {
                "skill_id": skill_id,
                "name": name,
                "description": description,
                "rating": rating,
                "features": features or [],
                "tier": tier,
                "timestamp": time.time()
            }
        }
        return await self.upsert_batch([point], "jkai_skills")

    # ── COMPATIBILITY LAYER ─────────────────────────────────
    
    async def init_collection(self, collection_name: str, vector_size: int = 768):
        return await self.ensure_collection(collection_name, vector_size=vector_size)

    async def get_points(self, collection: str, ids: list[str]) -> list[dict[str, Any]]:
        async with self._semaphore:
            try:
                client = self._get_async_client()
                resp = await client.post(f"{self.url}/collections/{collection}/points", json={
                    "ids": ids, "with_payload": True, "with_vector": False
                })
                if resp.status_code == 200: return resp.json().get("result", [])
            except Exception as e:
                logger.error(f"[QDRANT-GET-POINTS-ERR] {e}")
        return []

    async def add_intel(self, collection: str, text: str, vector: list, metadata: dict = None, point_id: str = None):
        point = {
            "id": point_id or str(uuid.uuid4()),
            "vector": vector,
            "payload": { "text": text, **(metadata or {}) }
        }
        return await self.upsert_batch([point], collection)

qdrant_client = QdrantClientWrapper()
