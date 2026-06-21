import os

# 🛡️ JKAI ZENITH: ROBUST REDIS CLIENT v14.3 (SINGLE SOURCE OF TRUTH)
# Giao thức: Tuyệt đối không gây sập hệ thống nếu thiếu Library hoặc Server.

try:
    import redis
    import redis.asyncio as redis_async
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    import warnings
    warnings.warn("[REDIS-WARN] Thu vien 'redis' chua duoc cai dat. Mot so tinh nang log/cache se bi vo hieu hoa.")

class RedisClient:
    def __init__(self):
        env_host = os.getenv("REDIS_HOST", "redis-ai")
        from core.config import IS_DOCKER
        if not IS_DOCKER and env_host in ["redis-ai", "redis-queue"]:
            self.host = "127.0.0.1"
        else:
            self.host = env_host
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD", "Admin@123456")
        self.client = None
        self._sync_client = None

    async def connect(self):
        if not REDIS_AVAILABLE: return None
        try:
            self.client = redis_async.Redis(
                host=self.host, 
                port=self.port, 
                password=self.password, 
                decode_responses=True,
                socket_timeout=60,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=15
            )
        except Exception: self.client = None

    def get_sync_client(self):
        if not REDIS_AVAILABLE: return None
        if self._sync_client is None:
            try:
                self._sync_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=5
                )
            except Exception: pass
        return self._sync_client

    async def get_async_client(self):
        if not self.client:
            await self.connect()
        return self.client

    def pubsub(self):
        client = self.get_sync_client()
        if client:
            return client.pubsub()
        return None

    async def close(self):
        if self.client:
            await self.client.close()

    async def lpush(self, queue: str, data: str):
        if self.client:
            try: await self.client.lpush(queue, data)
            except Exception: pass

    async def brpop(self, queue: str, timeout: int = 5):
        if self.client:
            try: return await self.client.brpop([queue], timeout=timeout)
            except Exception: pass
        return None

    async def setnx(self, key: str, value: str, timeout_sec: int) -> bool:
        if self.client:
            try: return await self.client.set(key, value, nx=True, ex=timeout_sec)
            except Exception: pass
        return False
        
    async def get(self, key: str) -> str:
        if self.client:
            try: return await self.client.get(key)
            except Exception: pass
        return None
        
    async def set(self, key: str, value: str, ex: int = None):
        if self.client:
            try: await self.client.set(key, value, ex=ex)
            except Exception: pass

    async def execute_batch(self, operations: list):
        if not self.client: return
        try:
            async with self.client.pipeline() as pipe:
                for op in operations:
                    method = getattr(pipe, op[0])
                    method(*op[1:])
                await pipe.execute()
        except Exception: pass

redis_client = RedisClient()

def redis_safe(func, default=None):
    """Tiện ích thực thi Redis an toàn cho các tác vụ đồng bộ (Logging)."""
    if not REDIS_AVAILABLE: return default
    try:
        r = redis_client.get_sync_client()
        if r: return func(r)
    except Exception:
        pass
    return default

# ── Legacy API wrappers (for service-level redis_client.py compatibility) ──
def get_redis():
    """Trả về sync Redis client (legacy API)."""
    return redis_client.get_sync_client()

async def get_async_redis():
    """Trả về async Redis client (legacy API)."""
    client = await redis_client.get_async_client()
    return client
