import os
import httpx
import re
import asyncio
from typing import List, Optional

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
        self._rules_cache = None
        self._rules_last_mtime = 0
        self._embedding_cache = {}  # 🧠 [NEURAL-CACHE]: Lưu trữ vector để tránh tính toán trùng lặp
        self._max_cache_size = 1000
        self._semaphore = asyncio.Semaphore(5)  # 🛡️ [CONCURRENCY-GUARD]: Giới hạn 5 luồng embedding song song
        
    def _get_rules_from_file(self):
        """Elite Logic: Trích xuất thông tin từ rule_hardware.md với cơ chế Caching."""
        params = {
            "model": None, 
            "num_gpu": None, 
            "num_ctx": None
        }
        
        if not os.path.exists(self.rules_path): return params

        try:
            mtime = os.path.getmtime(self.rules_path)
            if self._rules_cache and mtime <= self._rules_last_mtime:
                return self._rules_cache

            with open(self.rules_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 💎 [NEURAL-HEADER-PARSER]: Tự động ánh xạ cột.
            lines = [l.strip() for l in content.split('\n') if '|' in l]
            if len(lines) < 3: return params

            profiles = {}
            in_section_25 = False
            in_section_3 = False
            headers = []

            for line in content.split('\n'):
                line = line.strip()
                if "2.5." in line: in_section_25 = True; in_section_3 = False; headers = []; continue
                if "3." in line: in_section_3 = True; in_section_25 = False; headers = []; continue
                if not (in_section_25 or in_section_3) or not line.startswith('|') or ':---' in line: continue
                
                parts = [p.replace('**', '').replace('`', '').strip() for p in line.split('|')]
                if not parts[0]: parts.pop(0)
                if parts and not parts[-1]: parts.pop()
                
                if "ROLE" in line.upper() or "PROFILE NAME" in line.upper():
                    headers = [h.strip().upper() for h in parts]
                    continue
                
                if in_section_25 and headers:
                    p_data = {headers[i]: parts[i] for i in range(len(parts)) if i < len(headers)}
                    p_name = p_data.get("PROFILE NAME", "").upper()
                    if p_name:
                        profiles[p_name] = {
                            "num_ctx": int(re.findall(r'\d+', p_data.get("NUM_CTX", "2048"))[0]),
                            "num_gpu": int(re.findall(r'\d+', p_data.get("NUM_GPU", "0"))[0]),
                            "num_thread": int(re.findall(r'\d+', p_data.get("NUM_THREAD", "0"))[0])
                        }
                    continue

                if in_section_3 and "EMBEDDER" in line.upper() and headers:
                    row_data = {headers[i]: parts[i] for i in range(len(parts)) if i < len(headers)}
                    
                    if "ACTIVE MODEL" in row_data: params["model"] = row_data["ACTIVE MODEL"]
                    
                    # [PROFILE-SYNC]: Ưu tiên Mapping, sau đó đến Profile
                    ctx_val = row_data.get("NUM_CTX", "N/A")
                    gpu_val = row_data.get("NUM_GPU", "N/A")
                    thr_val = row_data.get("NUM_THREAD", "N/A")
                    prof_name = row_data.get("ACTIVE PROFILE", "").upper()
                    
                    if ctx_val.isdigit(): params["num_ctx"] = int(ctx_val)
                    elif prof_name in profiles: params["num_ctx"] = profiles[prof_name]["num_ctx"]
                    
                    if gpu_val.isdigit(): params["num_gpu"] = int(gpu_val)
                    elif prof_name in profiles: params["num_gpu"] = profiles[prof_name]["num_gpu"]

                    if thr_val.isdigit(): params["num_thread"] = int(thr_val)
                    elif prof_name in profiles: params["num_thread"] = profiles[prof_name]["num_thread"]
                    break
            
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
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    client = self._get_async_client()
                    resp = await client.post(
                        self.ollama_url,
                        json={
                            "model": target_model, 
                            "prompt": text,
                            "options": opts
                        }
                    )
                    
                    if resp.status_code == 200:
                        vector = resp.json().get("embedding")
                        # 🧠 [CACHE-STORE]
                        if vector and len(self._embedding_cache) < self._max_cache_size:
                            self._embedding_cache[cache_key] = vector
                        return vector
                    
                    if resp.status_code in [500, 503, 429] and attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    
                    return None
                except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadTimeout):
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    return None
                except Exception: return None
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
        import time
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                client = self._get_sync_client()
                resp = client.post(
                    self.ollama_url,
                    json={
                        "model": rules["model"], 
                        "prompt": text,
                        "options": opts
                    }
                )
                
                if resp.status_code == 200:
                    vector = resp.json().get("embedding")
                    # 🧠 [CACHE-STORE]
                    if vector and len(self._embedding_cache) < self._max_cache_size:
                        self._embedding_cache[cache_key] = vector
                    return vector
                
                if resp.status_code in [500, 503, 429] and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadTimeout):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return None
            except Exception: return None
        return None

    def __call__(self, text: str) -> Optional[List[float]]:
        """Cú pháp tắt: embed(text) -> Trả về embedding đồng bộ."""
        return self.get_embedding(text)

embedder = Embedder()
embed = embedder