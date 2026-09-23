# -*- coding: utf-8 -*-
"""
tests/test_executor_gateway_health.py
Unit tests for ExecutorGateway [N1] probe-before-dispatch circuit breaker.
Spec compliance (from OpenCode Turn 44):
- GET /health before dispatch; unhealthy -> failover immediately (no wasted budget)
- Both executors dead -> FAIL_FAST clean < 2s
- Mock 3 states: executor_1 UP, executor_1 DOWN->failover, both DOWN
"""

import asyncio
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add ai-brain to path (hyphenated directory)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))

from receptionist.executor_gateway import (
    ExecutorGateway,
    ExecutionRequest,
    _health_cache,
    _HealthCache,
)


class FakeResponse:
    def __init__(self, data=None, status_code=200):
        self._data = data if data is not None else {"status": "UP"}
        self.status_code = status_code

    def json(self):
        return self._data


def _make_gateway(get_resp=None, post_resp=None):
    """Create an ExecutorGateway with a mock http_client."""
    client = MagicMock()
    if get_resp is not None:
        client.get = AsyncMock(return_value=get_resp)
    else:
        client.get = AsyncMock(side_effect=ConnectionError("down"))
    if post_resp is not None:
        client.post = AsyncMock(return_value=post_resp)
    else:
        client.post = AsyncMock(side_effect=ConnectionError("down"))
    return ExecutorGateway(client)


@pytest.fixture(autouse=True)
def clear_health_cache():
    _health_cache._cache.clear()
    yield
    _health_cache._cache.clear()


@pytest.mark.asyncio
async def test_probe_healthy_returns_true():
    """Executor returns 200 with {'status': 'UP'} -> probe returns True, cache updated."""
    gw = _make_gateway(get_resp=FakeResponse(data={"status": "UP"}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is True
    assert _health_cache.is_known_healthy("executor") is True


@pytest.mark.asyncio
async def test_probe_unhealthy_returns_false_and_caches():
    """Executor returns 503 -> probe returns False, cache marks unhealthy."""
    gw = _make_gateway(get_resp=FakeResponse(data={"status": "DOWN"}, status_code=503))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False
    assert _health_cache.is_known_healthy("executor") is False


@pytest.mark.asyncio
async def test_probe_404_is_false_positive_guard():
    """Executor returns 404 -> probe returns False (not treated as healthy)."""
    gw = _make_gateway(get_resp=FakeResponse(data={}, status_code=404))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False


@pytest.mark.asyncio
async def test_probe_200_bad_body_is_unhealthy():
    """Executor returns 200 but status field is missing -> unhealthy."""
    gw = _make_gateway(get_resp=FakeResponse(data={"error": "service unavailable"}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False


@pytest.mark.asyncio
async def test_probe_broken_status_no_false_positive():
    """{'status':'broken'} contains 'ok' as substring but must NOT be treated as healthy (JSON-first)."""
    gw = _make_gateway(get_resp=FakeResponse(data={"status": "broken"}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False, "Substring 'ok' in 'broken' must NOT be a false positive"


@pytest.mark.asyncio
async def test_probe_setup_status_no_false_positive():
    """{'status':'setup'} contains 'up' as substring but must NOT be treated as healthy (JSON-first)."""
    gw = _make_gateway(get_resp=FakeResponse(data={"status": "setup"}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False, "Substring 'up' in 'setup' must NOT be a false positive"


@pytest.mark.asyncio
async def test_probe_ok_status_is_healthy():
    """{'status':'ok'} (exact match) must be treated as healthy."""
    gw = _make_gateway(get_resp=FakeResponse(data={"status": "ok"}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is True


@pytest.mark.asyncio
async def test_probe_healthy_boolean_true():
    """{'healthy': True} must be treated as healthy."""
    gw = _make_gateway(get_resp=FakeResponse(data={"healthy": True}, status_code=200))
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is True


@pytest.mark.asyncio
async def test_probe_exception_returns_false():
    """Executor is unreachable -> probe returns False, cache marks unhealthy."""
    gw = _make_gateway()  # get raises ConnectionError
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is False


@pytest.mark.asyncio
async def test_cached_healthy_skips_re_probe():
    """If cache TTL valid and healthy, no HTTP call made."""
    _health_cache.update("executor", True)
    client = MagicMock()
    client.get = AsyncMock(side_effect=AssertionError("Should NOT probe again"))
    gw = ExecutorGateway(client)
    result = await gw._probe_executor_health("executor", "http://executor:8000")
    assert result is True


@pytest.mark.asyncio
async def test_cached_unhealthy_skips_re_probe():
    """If cache TTL valid and unhealthy, no HTTP call made."""
    _health_cache.mark_unhealthy("executor_2")
    client = MagicMock()
    client.get = AsyncMock(side_effect=AssertionError("Should NOT probe again"))
    gw = ExecutorGateway(client)
    result = await gw._probe_executor_health("executor_2", "http://executor-2:8000")
    assert result is False
