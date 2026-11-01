# -*- coding: utf-8 -*-
"""
C14 — Cache effectiveness metrics (fail-first).

The embedding cache decides whether a query costs 1.8s (Ollama) or 0.004s
(Redis/LRU). Without hit/miss counters there is no way to tell whether it is
actually working in production, so silent regressions stay invisible.

Contract:
1. CacheLayer counts redis hits, LRU hits, misses and stores for embeddings
   (and the same for the file cache).
2. ai-brain exposes the counters at GET /cache/stats.
"""

from pathlib import Path

import importlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "core" / "knowledge_sources" / "cache.py"
AI_BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"


class FakeRedis:
    def __init__(self, write_through=False):
        self.stored = {}
        self.writes = {}
        self.write_through = write_through

    def get(self, key):
        return self.stored.get(key)

    def setex(self, key, ttl, value):
        self.writes[key] = value
        if self.write_through:
            self.stored[key] = value


def load_cache_module():
    spec = importlib.util.spec_from_file_location("c14_cache_layer", CACHE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def delta(before, after, key):
    return after[key] - before[key]


def test_embedding_counters_track_redis_lru_and_miss(monkeypatch):
    module = load_cache_module()
    layer = module.CacheLayer()

    before = layer.stats()
    layer._get_redis = lambda: FakeRedis()
    assert layer.get_embedding("c14-miss-probe") is None
    after_miss = layer.stats()
    assert delta(before, after_miss, "embed_misses") == 1

    layer.set_embedding("c14-lru-probe", [0.5, 0.5])
    after_store = layer.stats()
    assert delta(before, after_store, "embed_stores") == 1

    assert layer.get_embedding("c14-lru-probe") == [0.5, 0.5]
    after_lru = layer.stats()
    assert delta(before, after_lru, "embed_lru_hits") == 1

    shared_redis = FakeRedis(write_through=True)
    module.cache_layer._get_redis = lambda: shared_redis
    module.cache_layer.set_embedding("c14-redis-probe", [1.0, 2.0])
    assert module.cache_layer.get_embedding("c14-redis-probe") == [1.0, 2.0]
    after_redis = module.cache_layer.stats()
    assert after_redis["embed_redis_hits"] >= 1
    assert after_redis["embed_stores"] >= 1


def test_stats_are_snapshots_not_live_reference():
    module = load_cache_module()
    layer = module.CacheLayer()
    snapshot = layer.stats()
    snapshot["embed_misses"] = 10 ** 6
    assert layer.stats()["embed_misses"] != 10 ** 6
    for key in ("embed_redis_hits", "embed_lru_hits", "embed_misses", "embed_stores"):
        assert key in layer.stats()
    for key in ("file_redis_hits", "file_lru_hits", "file_misses"):
        assert key in layer.stats()


def test_ai_brain_exposes_cache_stats_route():
    source = AI_BRAIN_MAIN.read_text(encoding="utf-8")
    assert "'/cache/stats'" in source or '"/cache/stats"' in source
    assert "cache_layer.stats()" in source or "cache_layer.aggregate_stats()" in source
