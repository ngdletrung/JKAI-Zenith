"""
🧠 Redis Client V4 — Singleton + Safe Connection
- Singleton pattern để tránh tạo nhiều connection
- Auto-reconnect
- Logging và health check
"""

import os
import json
import logging
import time
from typing import Optional

import redis

logger = logging.getLogger("redis_client_v4")

_redis_instance: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Trả về Redis client singleton"""
    global _redis_instance

    if _redis_instance is not None:
        try:
            _redis_instance.ping()
            return _redis_instance
        except Exception:
            logger.warning("Redis connection lost, reconnecting...")
            _redis_instance = None

    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", "")

    try:
        client = redis.Redis(
            host=host,
            port=port,
            password=password or None,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        client.ping()
        _redis_instance = client
        logger.info(f"✅ Connected to Redis at {host}:{port}")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        # Trả về client dummy để tránh crash hoàn toàn
        dummy = redis.Redis(host="localhost", port=6379, decode_responses=True)
        dummy.ping = lambda: None  # type: ignore
        return dummy


def publish_event(channel: str, message: dict):
    """Helper publish event qua Redis Pub/Sub"""
    try:
        r = get_redis_client()
        r.publish(channel, json.dumps(message))
    except Exception as e:
        logger.warning(f"Failed to publish event to {channel}: {e}")


# Alias phổ biến
get_redis = get_redis_client

def redis_safe(func, default=None):
    """Tiện ích kết nối Redis an toàn (Dùng chung connection)."""
    try:
        r = get_redis()
        return func(r)
    except Exception as e:
        logger.error(f"❌ [JKAI-REDIS] Error: {e}")
        return default