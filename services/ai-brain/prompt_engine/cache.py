import hashlib
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("JKAI.PromptEngine.Cache")


class PromptCacheEntry:
    def __init__(self, key: str, value: str, ttl: int = 300):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class PromptCache:
    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, PromptCacheEntry] = {}
        self._default_ttl = default_ttl

    def make_key(self, role: str, task_type: str, behavior_version: str = "1.0") -> str:
        raw = f"{role}:{task_type}:{behavior_version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: str, ttl: Optional[int] = None):
        self._store[key] = PromptCacheEntry(key, value, ttl or self._default_ttl)

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


prompt_cache = PromptCache()
