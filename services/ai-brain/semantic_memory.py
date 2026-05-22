import json
import time
import httpx
import os
from typing import List, Dict, Any

class SemanticMemory:
    """
    💎 JKAI ZENITH: SEMANTIC MEMORY ENGINE
    Sử dụng Qdrant để lưu trữ và truy vấn tri thức vĩnh cửu.
    """
    def __init__(self):
        from core.utils.engine import engine
        self.engine = engine
        self.qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.collection_name = "zenith_missions"
        
        # 💎 Kênh truyền dẫn vĩnh cửu thưa Master
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(600.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        # 🎯 TUÂN THỦ CHỈ THỊ MASTER: Lấy thông số từ Nguồn Sống Duy Nhất
        cfg = self.engine.get_role_config("EMBEDDER")
        self.embedding_model = cfg.get("model", "nomic-embed-text:latest")
        self.vector_size = cfg.get("options", {}).get("num_ctx", 768)
        if "nomic" in self.embedding_model: self.vector_size = 768
        elif "minilm" in self.embedding_model: self.vector_size = 384

    async def _get_embedding(self, text: str) -> List[float]:
        """Tạo vector từ văn bản qua Ollama với thời gian chờ ngắn."""
        try:
            # Nomic yêu cầu prefix để đạt độ chính xác cao nhất
            prompt = f"search_document: {text}"
            resp = await self.client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": prompt},
                timeout=60.0 # Tăng lên 60 giây để tránh ReadTimeout trên CPU thưa Master
            )
            if resp.status_code != 200:
                return []
            return resp.json()["embedding"]
        except Exception as e:
            import traceback
            print(f"❌ [MEMORY-EMBED-ERR] {str(e)}")
            traceback.print_exc()
            return []

    async def init_collection(self):
        """Khởi tạo hoặc tái cấu trúc collection trong Qdrant thưa Master."""
        try:
            # Check current collection
            check = await self.client.get(f"{self.qdrant_url}/collections/{self.collection_name}")
            
            recreate = False
            if check.status_code == 200:
                config = check.json().get("result", {}).get("config", {})
                current_size = config.get("params", {}).get("vectors", {}).get("size")
                if current_size != self.vector_size:
                    print(f"🔄 [MEMORY-SYNC] Kích thước vector thay đổi ({current_size} -> {self.vector_size}). Đang tái cấu trúc...")
                    await self.client.delete(f"{self.qdrant_url}/collections/{self.collection_name}")
                    recreate = True
            else:
                recreate = True

            if recreate:
                await self.client.put(
                    f"{self.qdrant_url}/collections/{self.collection_name}",
                    json={
                        "vectors": {
                            "size": self.vector_size,
                            "distance": "Cosine"
                        }
                    }
                )
                print(f"✅ [MEMORY-INIT] Collection '{self.collection_name}' ({self.vector_size}D) initialized.")
        except Exception as e:
            print(f"❌ [MEMORY-INIT-ERR] {e}")

    async def store_log(self, task_id: str, tag: str, msg: str):
        """Lưu trữ một đoạn nhật ký vào bộ nhớ vĩnh cửu."""
        if not msg or len(msg) < 10: return
        
        vector = await self._get_embedding(msg)
        if not vector: return

        point_id = f"{task_id}_{int(time.time() * 1000)}"
        # Simplified point ID using a hash or UUID for Qdrant compatibility if needed
        # For now, let's just use a timestamp-based integer or string
        
        try:
            await self.client.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={
                    "points": [
                        {
                            "id": int(time.time() * 1000000), # Unique int ID
                            "vector": vector,
                            "payload": {
                                "task_id": task_id,
                                "tag": tag,
                                "text": msg,
                                "ts": time.time()
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            print(f"❌ [MEMORY-STORE-ERR] {e}")

    async def search_index(self, query: str, limit: int = 10) -> List[Dict]:
        """Lớp 1: Tìm kiếm chỉ mục ký ức (Token-efficient) thưa Master."""
        vector = await self._get_embedding(query)
        if not vector: return []
        try:
            resp = await self.client.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json={"vector": vector, "limit": limit, "with_payload": True}
            )
            results = resp.json().get("result", [])
            return [{"id": r["id"], "tag": r["payload"].get("tag"), "summary": r["payload"].get("text")[:100], "score": r["score"]} for r in results if r["score"] > 0.6]
        except: return []

    async def get_details(self, ids: List[int]) -> List[Dict]:
        """Lớp 3: Truy xuất chi tiết ký ức theo ID thưa Master."""
        try:
            resp = await self.client.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={"ids": ids}
            )
            results = resp.json().get("result", [])
            return [r["payload"] for r in results]
        except: return []

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Tìm kiếm tương thích ngược thưa Master."""
        idx = await self.search_index(query, limit)
        if not idx: return []
        return await self.get_details([i["id"] for i in idx])

memory = SemanticMemory()
