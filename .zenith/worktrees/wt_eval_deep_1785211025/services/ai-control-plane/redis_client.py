import redis
import redis.asyncio as async_redis
import os
import redis as sync_redis
import logging

logger = logging.getLogger(__name__)

_REDIS_INSTANCE = None

def get_redis():
    global _REDIS_INSTANCE
    if _REDIS_INSTANCE is None:
        try:
            _REDIS_INSTANCE = sync_redis.Redis(
                host=os.getenv("REDIS_HOST", "redis-ai"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", "Admin@123456"),
                decode_responses=True,
                socket_timeout=5
            )
        except Exception:
            return None
    return _REDIS_INSTANCE

async def get_async_redis():
    import redis.asyncio as async_redis
    try:
        return async_redis.Redis(
            host=os.getenv("REDIS_HOST", "redis-ai"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", "Admin@123456"),
            decode_responses=True,
            socket_timeout=60,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=15
        )
    except Exception:
        return None

def redis_safe(func, default=None):
    try:
        r = get_redis()
        if r:
            return func(r)
    except Exception:
        pass
    return default
