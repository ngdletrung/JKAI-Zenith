# -*- coding: utf-8 -*-
"""
core/utils/redis_client.py
Unified Redis Client Bridge (Re-exports from core.redis_client - Single Source of Truth).
Eliminates code duplication and disparate connection configurations (T1).
"""

from core.redis_client import (
    RedisClient,
    redis_client,
    redis_safe,
    get_redis,
    get_async_redis,
    get_redis_client,
    publish_event,
)

__all__ = [
    "RedisClient",
    "redis_client",
    "redis_safe",
    "get_redis",
    "get_async_redis",
    "get_redis_client",
    "publish_event",
]