# -*- coding: utf-8 -*-
"""
tests/test_should_stop.py
Unit tests for centralized should_stop helper in core/utils/engine.py.
Spec compliance:
- Global stop signal (str and bytes: 'true', b'true', '1', b'1') -> True
- Task stop signal ('agent:stop_signal:{task_id}') -> True
- Redis None / down / exception -> False (fail-safe, no blind abort)
"""

import pytest
from core.utils.engine import should_stop


class MockRedis:
    def __init__(self, store=None, raise_exc=False):
        self.store = store or {}
        self.raise_exc = raise_exc

    def get(self, key):
        if self.raise_exc:
            raise ConnectionError("Redis connection lost")
        return self.store.get(key)


def test_should_stop_global_signal():
    # Test str 'true'
    r1 = MockRedis({"agent:stop_signal": "true"})
    assert should_stop(redis_conn=r1) is True

    # Test bytes b'true'
    r2 = MockRedis({"agent:stop_signal": b"true"})
    assert should_stop(redis_conn=r2) is True

    # Test str '1' and bytes b'1'
    r3 = MockRedis({"agent:stop_signal": "1"})
    assert should_stop(redis_conn=r3) is True

    r4 = MockRedis({"agent:stop_signal": b"1"})
    assert should_stop(redis_conn=r4) is True

    # No stop signal
    r5 = MockRedis({"agent:stop_signal": "false"})
    assert should_stop(redis_conn=r5) is False


def test_should_stop_task_specific_signal():
    task_id = "task_abc123"
    # No global, but task signal set
    r1 = MockRedis({f"agent:stop_signal:{task_id}": "true"})
    assert should_stop(task_id=task_id, redis_conn=r1) is True

    # Task signal set as bytes
    r2 = MockRedis({f"agent:stop_signal:{task_id}": b"true"})
    assert should_stop(task_id=task_id, redis_conn=r2) is True

    # Other task has signal, current task does not
    r3 = MockRedis({"agent:stop_signal:other_task": "true"})
    assert should_stop(task_id=task_id, redis_conn=r3) is False


def test_should_stop_redis_down_or_unread():
    # Redis None
    assert should_stop(task_id="t1", redis_conn=None) is False

    # Redis raises exception
    r_err = MockRedis(raise_exc=True)
    assert should_stop(task_id="t1", redis_conn=r_err) is False
