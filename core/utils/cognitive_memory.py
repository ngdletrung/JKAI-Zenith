import os
import json
import logging
import asyncio
import time
import hashlib
import re
from typing import Optional, Dict, Any, List

from core.qdrant_client import qdrant_client
from core.utils.embed import embed
from core.utils.engine import engine
from core.utils import path_manager

logger = logging.getLogger("JKAI.CognitiveMemory")

class CognitiveMemory:
    """
    JKAI ZENITH: COGNITIVE MEMORY GATEKEEPER v1.0
    Nhiệm vụ: Lớp bảo vệ nơ-ron toàn cục, thực hiện phản xạ tức thì (Reflex) 
    trước khi kích hoạt các luồng tư duy phức tạp thưa Master.
    """
    def __init__(self):
        self.collection = "jkai_knowledge"
        self.cache_dir = os.path.join(path_manager.get_root(), "intelligence", "storage", "neural_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Ngưỡng tương đồng (Threshold)
        self.similarity_threshold = 0.90 
        self.ttl_map = {
            "time_sensitive": 3600,    # 1 giờ (Giá vàng, thời tiết)
            "session": 43200,          # 12 giờ (Ngữ cảnh chat)
            "permanent": None          # Vĩnh cửu (Kiến trúc, luật lệ)
        }

    def _get_query_key(self, query: str) -> str:
        clean_query = re.sub(r"[^a-zA-Z0-9_]", "_", query)[:50].strip("_")
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()[:10]
        return f"{clean_query}_{query_hash}"

    def _is_time_sensitive(self, query: str) -> bool:
        """Phát hiện các truy vấn nhạy cảm với thời gian thưa Master."""
        keywords = ["hôm nay", "bây giờ", "giá vàng", "tỷ giá", "thời tiết", "mới nhất", "tin tức", "đang"]
        return any(k in query.lower() for k in keywords)

    async def check_reflex(self, query: str, task_id: str = "sys", session_id: str = None) -> Optional[Dict[str, Any]]:
        """
        🚀 [NEURAL-GATE]: Kiểm tra phản xạ nơ-ron.
        Hỗ trợ phân tách session để tránh rác tri thức thưa Master.
        """
        try:
            # 0. Tiền xử lý query
            clean_query = query.strip()
            if len(clean_query) < 5: return None
            
            # 1. Tra cứu Qdrant (Semantic Hit)
            query_emb = await embed.get_embedding_async(clean_query)
            if query_emb:
                results = await qdrant_client.search_similar(
                    query_embedding=query_emb,
                    limit=1,
                    collection=self.collection,
                    filter_dict={"namespace": "neural_cache"}
                )
                
                if results:
                    best_match = results[0]
                    score = best_match.score if hasattr(best_match, 'score') else best_match.get('score', 0)
                    
                    if score >= self.similarity_threshold:
                        payload = best_match.payload if hasattr(best_match, 'payload') else best_match.get('payload', {})
                        # Kiểm tra logic Session
                        entry_session = payload.get("session_id")
                        if entry_session and entry_session != session_id:
                            # Không dùng cache của session khác trừ khi là tri thức chung
                            return None

                        cached_time = payload.get("timestamp", 0)
                        age = time.time() - cached_time
                        
                        # Xác định TTL dựa trên loại dữ liệu
                        ttl = self.ttl_map["time_sensitive"] if self._is_time_sensitive(clean_query) else self.ttl_map["session"]
                        
                        if age < ttl:
                            msg = f"[NEURAL-HIT]: Phản xạ nơ-ron (Score: {score:.2f}, Session: {entry_session or 'Global'})"
                            engine.publish_mission_log("CACHE", msg, task_id)
                            logger.info(msg)
                            return {
                                "answer": payload.get("text", payload.get("answer", "")),
                                "source": "qdrant_reflex",
                                "score": score,
                                "timestamp": cached_time
                            }

            # 2. Tra cứu Disk (Exact/Hash Hit)
            key = self._get_query_key(clean_query)
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cached_time = data.get("timestamp", 0)
                    age = time.time() - cached_time
                    ttl = self.ttl_map["time_sensitive"] if self._is_time_sensitive(clean_query) else self.ttl_map["session"]
                    
                    if age < ttl:
                        msg = f"[DISK-HIT]: Trúng đích bộ nhớ đĩa (Age: {age:.0f}s)"
                        engine.publish_mission_log("CACHE", msg, task_id)
                        return {
                            "answer": data.get("content", data.get("answer", "")),
                            "source": "disk_reflex",
                            "timestamp": cached_time
                        }
                except Exception: pass

        except Exception as e:
            logger.error("[COG-MEM-ERR]: %s", e)
            
        return None

    async def store_reflex(self, query: str, answer: str, session_id: str = None, metadata: dict = None):
        """Lưu trữ tri thức với nhãn Session để dễ dàng thanh tẩy thưa Master."""
        if not query or not answer: return
        
        metadata = metadata or {}
        if session_id: metadata["session_id"] = session_id
        
        # 1. Lưu Disk Cache
        key = self._get_query_key(query)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        payload = {
            "query": query,
            "answer": answer,
            "timestamp": time.time(),
            "session_id": session_id,
            "metadata": metadata
        }
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.warning("[DISK-WRITE-ERR]: %s", e)

        # 2. Lưu Qdrant Cache (Vectorized)
        try:
            emb = await embed.get_embedding_async(f"Question: {query}\nAnswer: {answer}")
            if emb:
                qdrant_meta = {
                    "namespace": "neural_cache",
                    "source": "cache",
                    "original_query": query,
                    "timestamp": time.time(),
                    "session_id": session_id,
                    **metadata
                }
                await qdrant_client.upsert_intel(
                    text=answer,
                    embedding=emb,
                    metadata=qdrant_meta,
                    collection=self.collection,
                    vector_size=len(emb)
                )
                logger.info("[COG-STORE]: Đã hóa thạch tri thức (Session: %s)", session_id or "Global")
        except Exception as e:
            logger.warning("[QDRANT-WRITE-ERR]: %s", e)

    async def purge_session(self, session_id: str):
        """🧹 [SESSION-PURGE]: Xóa sạch rác tri thức của một phiên thưa Master."""
        if not session_id: return
        try:
            # Xóa trong Qdrant
            # Lưu ý: Cần filter theo session_id
            await qdrant_client.delete_points(
                collection=self.collection,
                filter_dict={"session_id": session_id}
            )
            logger.info("[NEURAL-PURGE]: Đã giải phóng nơ-ron cho Session %s", session_id)
        except Exception as e:
            logger.error("[PURGE-ERR]: %s", e)

cognitive_memory = CognitiveMemory()
