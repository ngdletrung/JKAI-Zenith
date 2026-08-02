import os
import json
import time
import hashlib
from collections import OrderedDict
from typing import Optional, Any

class CacheLayer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lru: OrderedDict[str, Any] = OrderedDict()
        self._lru_max = 500
        self._initialized = True

    def _get_redis(self):
        try:
            from core.utils.engine import engine
            return engine._get_redis()
        except Exception:
            return None

    def get_file_cache(self, path: str) -> Optional[str]:
        key = f"ks_cache:file:{hashlib.md5(path.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                val = r.get(key)
                if val:
                    return val.decode("utf-8")
            except Exception:
                pass
        if key in self._lru:
            self._lru.move_to_end(key)
            return self._lru[key]
        return None

    def set_file_cache(self, path: str, content: str, ttl: int = 86400):
        key = f"ks_cache:file:{hashlib.md5(path.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                r.setex(key, ttl, content)
            except Exception:
                pass
        self._lru[key] = content
        self._lru.move_to_end(key)
        if len(self._lru) > self._lru_max:
            self._lru.popitem(last=False)

    def get_embedding(self, text: str) -> Optional[list]:
        key = f"ks_cache:embed:{hashlib.md5(text.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                val = r.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return None

    def set_embedding(self, text: str, vector: list, ttl: int = 604800):
        key = f"ks_cache:embed:{hashlib.md5(text.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                r.setex(key, ttl, json.dumps(vector))
            except Exception:
                pass

    def warmup_hot_entries(self, entries: list[tuple[str, str, list]]):
        for text, content, vector in entries:
            if text:
                self.set_embedding(text, vector)
            if content:
                self.set_file_cache(text, content)

    def invalidate(self, path: str):
        key = f"ks_cache:file:{hashlib.md5(path.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                r.delete(key)
            except Exception:
                pass
        self._lru.pop(key, None)

cache_layer = CacheLayer()
