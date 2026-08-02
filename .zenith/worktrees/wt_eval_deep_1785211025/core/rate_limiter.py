class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_limit(self, identifier: str, limit: int, window_sec: int) -> bool:
        # Token bucket or fixed window via Redis
        # Ví dụ: INCR, EXPIRE
        key = f"rate_limit:{identifier}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window_sec)
        return current <= limit
