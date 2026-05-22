import os

# 🛡️ JKAI ZENITH: ROBUST REDIS CLIENT v14.2
# Giao thức: Tuyệt đối không gây sập hệ thống nếu thiếu Library hoặc Server.

try:
    import redis
    import redis.asyncio as redis_async
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ [REDIS-WARN] Thư viện 'redis' chưa được cài đặt. Một số tính năng log/cache sẽ bị vô hiệu hóa.")

class RedisClient:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "redis-ai")
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
                socket_timeout=5
            )
        except: self.client = None

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
            except: pass
        return self._sync_client

    async def close(self):
        if self.client:
            await self.client.close()

    async def lpush(self, queue: str, data: str):
        if self.client:
            try: await self.client.lpush(queue, data)
            except: pass

    async def brpop(self, queue: str, timeout: int = 5):
        if self.client:
            try: return await self.client.brpop([queue], timeout=timeout)
            except: pass
        return None

    async def setnx(self, key: str, value: str, timeout_sec: int) -> bool:
        if self.client:
            try: return await self.client.set(key, value, nx=True, ex=timeout_sec)
            except: pass
        return False
        
    async def get(self, key: str) -> str:
        if self.client:
            try: return await self.client.get(key)
            except: pass
        return None
        
    async def set(self, key: str, value: str, ex: int = None):
        if self.client:
            try: await self.client.set(key, value, ex=ex)
            except: pass

    async def execute_batch(self, operations: list):
        """⚡ GIAO THỨC PIPELINE: Thực thi hàng loạt lệnh!"""
        if not self.client: return
        try:
            async with self.client.pipeline() as pipe:
                for op in operations:
                    method = getattr(pipe, op[0])
                    method(*op[1:])
                await pipe.execute()
        except: pass

redis_client = RedisClient()

def redis_safe(func, default=None):
    """Tiện ích thực thi Redis an toàn cho các tác vụ đồng bộ (Logging)."""
    if not REDIS_AVAILABLE: return default
    try:
        r = redis_client.get_sync_client()
        if r: return func(r)
    except: pass
    return default
