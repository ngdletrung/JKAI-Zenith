# -*- coding: utf-8 -*-
"""
C25 — Cache metrics must not report one worker as the whole system.

ai-brain runs `uvicorn --workers 2`, each with its own CacheLayer counters.
GET /cache/stats used to return whichever worker the load balancer picked, so
the dashboard showed a different (and always partial) picture on each poll.

Contract:
1. `stats()` stays a local snapshot (C14).
2. `aggregate_stats()` sums every worker that published within the TTL.
3. Redis being unavailable degrades to the local snapshot, never to an error.
4. ai-brain's /cache/stats exposes the aggregate plus the worker count.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "core" / "knowledge_sources" / "cache.py"
AI_BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"


class FakeRedis:
    def __init__(self, hashes=None):
        self.hashes = dict(hashes or {})
        self.ttls = {}

    def hset(self, key, mapping=None):
        self.hashes.setdefault(key, {}).update(mapping or {})

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def scan_iter(self, match=None):
        prefix = (match or "").rstrip("*")
        return [k for k in list(self.hashes) if k.startswith(prefix)]


def load_cache_module():
    spec = importlib.util.spec_from_file_location("c25_cache_layer", CACHE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_snapshot_is_unchanged():
    module = load_cache_module()
    layer = module.CacheLayer()
    snapshot = layer.stats()
    assert snapshot["embed_misses"] == 0
    snapshot["embed_misses"] = 999
    assert layer.stats()["embed_misses"] == 0


def test_aggregate_sums_published_workers():
    module = load_cache_module()
    layer = module.CacheLayer()
    layer._stats["embed_misses"] = 5
    layer._stats["embed_stores"] = 4

    other = {k: 7 for k in layer._stats}
    redis = FakeRedis({f"{module.CacheLayer._STATS_PREFIX}4242": other})
    layer._get_redis = lambda: redis

    report = layer.aggregate_stats()
    assert report["workers"] == 2, "own snapshot + the other worker"
    assert report["aggregate"]["embed_misses"] == 12
    assert report["aggregate"]["embed_stores"] == 11
    assert report["local"]["embed_misses"] == 5
    own_key = f"{module.CacheLayer._STATS_PREFIX}{report['pid']}"
    assert own_key in redis.hashes, "worker must publish itself on read"
    assert redis.ttls[own_key] == module.CacheLayer._STATS_TTL


def test_without_redis_aggregate_equals_local():
    module = load_cache_module()
    layer = module.CacheLayer()
    layer._stats["embed_redis_hits"] = 3
    layer._get_redis = lambda: None

    report = layer.aggregate_stats()
    assert report["workers"] == 1
    assert report["aggregate"] == report["local"]
    assert report["aggregate"]["embed_redis_hits"] == 3


def test_redis_errors_do_not_break_the_endpoint():
    module = load_cache_module()
    layer = module.CacheLayer()

    class Broken:
        def hset(self, *a, **kw):
            raise RuntimeError("redis down")

    layer._get_redis = lambda: Broken()
    report = layer.aggregate_stats()
    assert report["workers"] == 1
    assert report["aggregate"] == report["local"]


def test_route_reports_workers_and_aggregate():
    source = AI_BRAIN_MAIN.read_text(encoding="utf-8")
    assert "/cache/stats" in source
    assert "aggregate_stats()" in source
    assert '"workers": report["workers"]' in source
