import os
import httpx
import re
import asyncio
from typing import List, Optional
from core.utils.model_router import ModelRouter

class Embedder:
    _instance = None
    _async_client = None
    _sync_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            cls._instance._init_embedder()
        return cls._instance

    def _init_embedder(self):
        self.ollama_url = os.getenv("OLLAMA_EMBED_URL", "http://host.docker.internal:11434/api/embeddings")
        self.timeout = int(os.getenv("EMBED_TIMEOUT", "30"))
        from core.config import settings
        self.rules_path = os.path.join(settings.INTELLIGENCE_DIR, "rule_hardware.md")
        self._router = ModelRouter(self.rules_path)
        self._rules_cache = None
        self._rules_last_mtime = 0
        self._embedding_cache = {}  # 🧠 [NEURAL-CACHE]: Lưu trữ vector để tránh tính toán trùng lặp
        self._max_cache_size = 1000
        self._semaphore = asyncio.Semaphore(5)  # 🛡️ [CONCURRENCY-GUARD]: Giới hạn 5 luồng embedding song song
        
    def _get_rules_from_file(self):
        """Elite Logic: Trích xuất thông tin từ rule_hardware.md thông qua ModelRouter."""
        params = {
            "model": None, 
            "num_gpu": None, 
            "num_ctx": None,
            "num_thread": None,
        }
        
        if not os.path.exists(self.rules_path): return params

        try:
            mtime = os.path.getmtime(self.rules_path)
            if self._rules_cache and mtime <= self._rules_last_mtime:
                return self._rules_cache

            self._router._refresh_rules_if_needed()
            embed_cfg = self._router.get_role_config("EMBEDDER")
            if not embed_cfg:
                return params

            params["model"] = embed_cfg.get("model")
            opts = embed_cfg.get("options", {})
            params["num_ctx"] = opts.get("num_ctx", 2048)
            params["num_gpu"] = opts.get("num_gpu", 0)
            params["num_thread"] = opts.get("num_thread", 0)

            self._rules_cache = params
            self._rules_last_mtime = mtime
        except Exception as e:
            print(f"⚠️ [EMBED-PARSE-ERR]: {e}")
        return params

    def _get_options(self, rules):
        opts = {"num_gpu": rules["num_gpu"], "num_ctx": rules["num_ctx"]}
        if "num_thread" in rules and rules["num_thread"] > 0:
            opts["num_thread"] = rules["num_thread"]
        return opts

    def _get_async_client(self):
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    def _get_sync_client(self):
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.timeout)
        return self._sync_client

    async def get_embedding_async(self, text: str, model: str = None) -> Optional[List[float]]:
        if not text: return None
        
        # 🧠 [CACHE-CHECK]
        cache_key = f"{model}:{text[:200]}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        async with self._semaphore:  # 🛡️ [CONCURRENCY-CONTROL]
            rules = self._get_rules_from_file()
            target_model = model or rules["model"]
            opts = self._get_options(rules)
            
            # ✂️ [NEURAL-CHUNKING]: Tự động chia nhỏ văn bản nếu quá dài (Tránh lỗi 500 Ollama)
            # Nomic-embed-text có giới hạn khoảng 2048 tokens, ta chọn 4000 chars (~1000 tokens) cho an toàn.
            MAX_CHARS = 4000
            if len(text) > MAX_CHARS:
                chunks = [text[i:i+MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
                all_vectors = []
                for chunk in chunks:
                    v = await self._call_ollama_embed(chunk, target_model, opts)
                    if v: all_vectors.append(v)
                
                if not all_vectors: return None
                
                # 🧬 [VECTOR-FUSION]: Trung bình cộng các vector thành phần (Pure Python)
                dim = len(all_vectors[0])
                mean_vector = [0.0] * dim
                for v in all_vectors:
                    for i in range(dim):
                        mean_vector[i] += v[i]
                
                count = len(all_vectors)
                for i in range(dim):
                    mean_vector[i] /= count
                
                return mean_vector
            else:
                return await self._call_ollama_embed(text, target_model, opts)

    async def _call_ollama_embed(self, text: str, model: str, opts: dict) -> Optional[List[float]]:
        max_retries = 3
        retry_delay = 1.0
        for attempt in range(max_retries):
            try:
                client = self._get_async_client()
                resp = await client.post(
                    self.ollama_url,
                    json={
                        "model": model, 
                        "prompt": text,
                        "options": opts
                    }
                )
                
                if resp.status_code == 200:
                    return resp.json().get("embedding")
                
                if resp.status_code in [500, 503, 429] and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return None
        return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Lấy vector tri thức (Sync - Dùng cho các service truyền thống)."""
        if not text: return None
        
        # 🧠 [CACHE-CHECK]
        cache_key = f"default:{text[:200]}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        rules = self._get_rules_from_file()
        opts = self._get_options(rules)
        target_model = rules["model"]
        
        MAX_CHARS = 4000
        if len(text) > MAX_CHARS:
            chunks = [text[i:i+MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
            all_vectors = []
            for chunk in chunks:
                v = self._call_ollama_embed_sync(chunk, target_model, opts)
                if v: all_vectors.append(v)
            
            if not all_vectors: return None
            
            dim = len(all_vectors[0])
            mean_vector = [0.0] * dim
            for v in all_vectors:
                for i in range(dim):
                    mean_vector[i] += v[i]
            
            count = len(all_vectors)
            for i in range(dim):
                mean_vector[i] /= count
                
            return mean_vector
        else:
            return self._call_ollama_embed_sync(text, target_model, opts)

    def _call_ollama_embed_sync(self, text: str, model: str, opts: dict) -> Optional[List[float]]:
        import time
        max_retries = 3
        retry_delay = 1.0
        for attempt in range(max_retries):
            try:
                client = self._get_sync_client()
                resp = client.post(
                    self.ollama_url,
                    json={
                        "model": model, 
                        "prompt": text,
                        "options": opts
                    }
                )
                
                if resp.status_code == 200:
                    return resp.json().get("embedding")
                
                if resp.status_code in [500, 503, 429] and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
        return None

    def __call__(self, text: str) -> Optional[List[float]]:
        """Cú pháp tắt: embed(text) -> Trả về embedding đồng bộ."""
        return self.get_embedding(text)

embedder = Embedder()
embed = embedder