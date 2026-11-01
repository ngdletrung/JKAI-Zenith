import os
import json
import time
import hashlib
from collections import OrderedDict
from typing import Optional, Any

class CacheLayer:
    _instance = None
    _STATS_PREFIX = "ks_cache:stats:"
    _STATS_TTL = 300

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lru: OrderedDict[str, Any] = OrderedDict()
        self._embed_lru: OrderedDict[str, list] = OrderedDict()
        self._lru_max = 500
        self._stats = {
            "file_redis_hits": 0,
            "file_lru_hits": 0,
            "file_misses": 0,
            "file_stores": 0,
            "embed_redis_hits": 0,
            "embed_lru_hits": 0,
            "embed_misses": 0,
            "embed_stores": 0,
        }
        self._initialized = True

    def stats(self) -> dict:
        """Counters for cache effectiveness; a snapshot, not the live dict."""
        return dict(self._stats)

    def aggregate_stats(self) -> dict:
        """Counters summed across ai-brain workers.

        Each worker keeps its own counters in memory, so reporting a single
        worker's numbers from a load-balanced endpoint is misleading. Workers
        publish their snapshot into Redis on read; the answer covers every
        worker that reported within `_STATS_TTL` seconds.
        """
        local = self.stats()
        result = {
            "pid": os.getpid(),
            "workers": 1,
            "ttl": self._STATS_TTL,
            "aggregate": dict(local),
            "local": local,
        }
        redis = self._get_redis()
        if not redis:
            return result

        try:
            self._publish_local_stats(redis)
            totals = {key: 0 for key in local}
            workers = 0
            for key in redis.scan_iter(match=f"{self._STATS_PREFIX}*"):
                raw = redis.hgetall(key) or {}
                if not raw:
                    continue
                workers += 1
                for name in totals:
                    value = raw.get(name, raw.get(name.encode(), 0))
                    try:
                        totals[name] += int(value)
                    except (TypeError, ValueError):
                        pass
            if workers:
                result["workers"] = workers
                result["aggregate"] = totals
        except Exception:
            pass
        return result

    def _publish_local_stats(self, redis) -> None:
        key = f"{self._STATS_PREFIX}{os.getpid()}"
        redis.hset(key, mapping={k: int(v) for k, v in self._stats.items()})
        redis.expire(key, self._STATS_TTL)

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
                    self._stats["file_redis_hits"] += 1
                    return val.decode("utf-8")
            except Exception:
                pass
        if key in self._lru:
            self._stats["file_lru_hits"] += 1
            self._lru.move_to_end(key)
            return self._lru[key]
        self._stats["file_misses"] += 1
        return None

    def set_file_cache(self, path: str, content: str, ttl: int = 86400):
        key = f"ks_cache:file:{hashlib.md5(path.encode()).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                r.setex(key, ttl, content)
            except Exception:
                pass
        self._stats["file_stores"] += 1
        self._lru[key] = content
        self._lru.move_to_end(key)
        if len(self._lru) > self._lru_max:
            self._lru.popitem(last=False)

    def get_embedding(self, text: str) -> Optional[list]:
        key = f"ks_cache:embed:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                val = r.get(key)
                if val:
                    self._stats["embed_redis_hits"] += 1
                    return json.loads(val)
            except Exception:
                pass
        if key in self._embed_lru:
            self._stats["embed_lru_hits"] += 1
            self._embed_lru.move_to_end(key)
            return list(self._embed_lru[key])
        self._stats["embed_misses"] += 1
        return None

    def set_embedding(self, text: str, vector: list, ttl: int = 604800):
        key = f"ks_cache:embed:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
        r = self._get_redis()
        if r:
            try:
                r.setex(key, ttl, json.dumps(vector))
            except Exception:
                pass
        self._stats["embed_stores"] += 1
        self._embed_lru[key] = list(vector)
        self._embed_lru.move_to_end(key)
        if len(self._embed_lru) > self._lru_max:
            self._embed_lru.popitem(last=False)

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
