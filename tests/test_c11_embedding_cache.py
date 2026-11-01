# -*- coding: utf-8 -*-
"""
C11 — Embedding cache correctness + async safety (fail-first).

Regression contract:
1. Two texts sharing the first 200 characters must never share a cached vector.
2. A repeated embedding must be served from cache without a second Ollama call.
3. Cache lookup/store must include the resolved model (no "None:" bucket).
4. Redis outage must be fail-soft (still return the computed vector).
5. Redis access on the async path must not block the event loop.
"""

import asyncio
import time
import uuid

import pytest

from core.knowledge_sources.cache import cache_layer
from core.utils.embed import Embedder, embed


RULES = {
    "model": "test-embed:latest",
    "num_gpu": 0,
    "num_ctx": 2048,
    "num_thread": 4,
}


def _unique(prefix: str = "c11") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


@pytest.fixture(autouse=True)
def offline_cache(monkeypatch):
    """No real Redis in unit tests; the in-process LRU still exercises the cache path."""
    monkeypatch.setattr(cache_layer, "_get_redis", lambda: None)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(embed, "_get_rules_from_file", lambda: dict(RULES))
    return embed


@pytest.mark.asyncio
async def test_prefix_200_collision_returns_distinct_vectors(client, monkeypatch):
    calls = []

    async def fake_embed(text, model, opts):
        calls.append(text)
        return [1.0] if "A-" in text else [2.0]

    monkeypatch.setattr(client, "_call_ollama_embed", fake_embed)

    shared_prefix = "x" * 200
    text_a = shared_prefix + "A-" + _unique()
    text_b = shared_prefix + "B-" + _unique()

    vec_a = await client.get_embedding_async(text_a)
    vec_b = await client.get_embedding_async(text_b)

    assert vec_a != vec_b, "Texts sharing a 200-char prefix must not share a cached vector"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_second_call_is_cache_hit_without_ollama(client, monkeypatch):
    calls = []

    async def fake_embed(text, model, opts):
        calls.append(text)
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(client, "_call_ollama_embed", fake_embed)

    text = _unique("cache-hit")
    first = await client.get_embedding_async(text)
    second = await client.get_embedding_async(text)

    assert first == second == [0.1, 0.2, 0.3]
    assert len(calls) == 1, "Second call must be served from cache"


@pytest.mark.asyncio
async def test_cache_key_uses_resolved_model(client, monkeypatch):
    seen = []

    def spy_get(key):
        seen.append(key)
        return None

    monkeypatch.setattr(cache_layer, "get_embedding", spy_get)

    async def fake_embed(text, model, opts):
        return [1.0]

    monkeypatch.setattr(client, "_call_ollama_embed", fake_embed)

    text = _unique("model-key")
    await client.get_embedding_async(text)

    assert seen == [f"{RULES['model']}\x00{text}"], f"unexpected cache key(s): {seen}"


@pytest.mark.asyncio
async def test_redis_outage_is_fail_soft(client, monkeypatch):
    class BoomRedis:
        def get(self, *args, **kwargs):
            raise RuntimeError("redis down")

        def setex(self, *args, **kwargs):
            raise RuntimeError("redis down")

    monkeypatch.setattr(cache_layer, "_get_redis", lambda: BoomRedis())

    async def fake_embed(text, model, opts):
        return [9.0, 8.0]

    monkeypatch.setattr(client, "_call_ollama_embed", fake_embed)

    result = await client.get_embedding_async(_unique("redis-down"))
    assert result == [9.0, 8.0]


@pytest.mark.asyncio
async def test_redis_access_does_not_block_event_loop(client, monkeypatch):
    def slow_get(key):
        time.sleep(0.30)
        return None

    monkeypatch.setattr(cache_layer, "get_embedding", slow_get)

    async def fake_embed(text, model, opts):
        return [1.0]

    monkeypatch.setattr(client, "_call_ollama_embed", fake_embed)

    async def worker():
        return await client.get_embedding_async(_unique("non-blocking"))

    ticks = []

    async def ticker():
        for _ in range(3):
            ticks.append(time.perf_counter())
            await asyncio.sleep(0.03)

    start = time.perf_counter()
    await asyncio.gather(worker(), ticker())
    elapsed_first_tick = ticks[0] - start

    assert elapsed_first_tick < 0.20, (
        f"Event loop was blocked for {elapsed_first_tick:.3f}s by the sync cache call"
    )


def test_sync_path_writes_then_hits_cache(client, monkeypatch):
    calls = []

    def fake_embed_sync(text, model, opts):
        calls.append(text)
        return [0.5, 0.5]

    monkeypatch.setattr(client, "_call_ollama_embed_sync", fake_embed_sync)

    text = _unique("sync-cache")
    first = client.get_embedding(text)
    second = client.get_embedding(text)

    assert first == second == [0.5, 0.5]
    assert len(calls) == 1, "Sync path must store results and hit the cache on repeat"


def test_knowledge_manager_keeps_no_second_embedding_cache():
    """A parallel md5('embed_cache:...') store drifted from the model-qualified
    CacheLayer and could hand another model's vector to a caller. One owner only."""
    import inspect
    from core.utils import knowledge_manager

    source = inspect.getsource(knowledge_manager)
    assert "embed_cache:" not in source
    assert "_get_cached_embedding" not in source
    assert "_cache_embedding" not in source


@pytest.mark.asyncio
async def test_knowledge_manager_delegates_to_shared_embedder(monkeypatch):
    import core.utils.embed as embed_mod
    import core.qdrant_client as qdrant_mod
    from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator

    seen = []

    def fake_embed(text):
        seen.append(text)
        return [0.25, 0.75]

    class FakeQdrant:
        async def search_similar(self, vector, **kwargs):
            assert vector == [0.25, 0.75], "Caller must receive the embedder's vector"
            return []

    monkeypatch.setattr(embed_mod, "embed", fake_embed)
    monkeypatch.setattr(qdrant_mod, "qdrant_client", FakeQdrant())

    km = JKAIKnowledgeOrchestrator()
    assert await km.retrieve_intel_async("truy vấn tri thức") == []
    assert seen == ["truy vấn tri thức"]

