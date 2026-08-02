import redis
import os
import redis

_REDIS_INSTANCE = None

def get_redis():
    global _REDIS_INSTANCE
    if _REDIS_INSTANCE is None:
        _REDIS_INSTANCE = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis-ai"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_timeout=5
        )
    return _REDIS_INSTANCE

def redis_safe(func, default=None):
    try:
        r = get_redis()
        if r:
            return func(r)
    except Exception:
        pass
    return default

