import redis
import redis.asyncio as async_redis
import os
import json

# Singleton Redis Clients
_redis_client = None
_async_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_host = os.getenv("REDIS_HOST")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_pass = os.getenv("REDIS_PASSWORD")
        if not redis_host: raise ValueError("REDIS_HOST not set in .env")
        
        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_pass,
            decode_responses=True,
            socket_timeout=5,
            socket_keepalive=True
        )
    return _redis_client

async def get_async_redis():
    global _async_redis_client
    if _async_redis_client is None:
        redis_host = os.getenv("REDIS_HOST")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_pass = os.getenv("REDIS_PASSWORD")
        
        _async_redis_client = async_redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_pass,
            decode_responses=True,
            socket_timeout=None, # No timeout for async pop
            socket_keepalive=True
        )
    return _async_redis_client

def redis_safe(func, default=None):
    """Tiện ích kết nối Redis an toàn (Dùng chung connection)."""
    try:
        r = get_redis()
        return func(r)
    except Exception as e:
        print(f"❌ [JKAI-REDIS] Error: {e}")
        return default
