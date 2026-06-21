import redis
import os
import redis as sync_redis
import redis.asyncio as async_redis
import asyncio
import logging

logger = logging.getLogger("redis_client")

class RedisClient:
    _instance = None
    _sync_instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.host = os.getenv("REDIS_HOST", "redis-ai")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD", "Admin@123456")
        self._async_client = None
        self._sync_client = None

    async def get_client(self):
        if self._async_client is None:
            self._async_client = async_redis.Redis(
                host=self.host, port=self.port, password=self.password,
                decode_responses=True,
                socket_timeout=60,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=15
            )
        return self._async_client

    def get_sync_client(self):
        if self._sync_client is None:
            self._sync_client = sync_redis.Redis(
                host=self.host, port=self.port, password=self.password,
                decode_responses=True, socket_timeout=5
            )
        return self._sync_client

redis_client = RedisClient()

def redis_safe(func, default=None):
    try:
        r = redis_client.get_sync_client()
        if r:
            return func(r)
    except Exception:
        pass
    return default

# ── Legacy API wrappers (for compatibility) ──
def get_redis():
    """Trả về sync Redis client (legacy API)."""
    return redis_client.get_sync_client()

async def get_async_redis():
    """Trả về async Redis client (legacy API)."""
    client = await redis_client.get_client()
    return client
