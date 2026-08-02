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
        self.password = os.getenv("REDIS_PASSWORD", None)
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

    async def subscribe_wakeup_event(self, channel: str, timeout: float = 300.0):
        """[REACTIVE-WAKEUP]: Lắng nghe sự kiện đánh thức qua Redis Pub/Sub thay vì polling liên tục."""
        client = await self.get_client()
        if not client:
            return None
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(channel)
            end_time = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < end_time:
                remaining = end_time - asyncio.get_event_loop().time()
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=min(remaining, 1.0))
                if message and message.get("type") == "message":
                    return message.get("data")
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.debug(f"[REACTIVE-WAKEUP] Error subscribing to {channel}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
        return None

    async def publish_wakeup_event(self, channel: str, message: str = "WAKEUP"):
        """[REACTIVE-WAKEUP]: Phát sóng tín hiệu đánh thức tiến trình ngầm qua Redis Pub/Sub."""
        client = await self.get_client()
        if client:
            try:
                await client.publish(channel, message)
            except Exception as e:
                logger.debug(f"[REACTIVE-WAKEUP] Error publishing to {channel}: {e}")

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

async def wait_for_wakeup(channel: str, timeout: float = 300.0):
    return await redis_client.subscribe_wakeup_event(channel, timeout)

async def notify_wakeup(channel: str, message: str = "WAKEUP"):
    return await redis_client.publish_wakeup_event(channel, message)

