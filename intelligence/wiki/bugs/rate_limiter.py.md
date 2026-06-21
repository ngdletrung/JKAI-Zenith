---
type: python_file
file: rate_limiter.py
tags: []
---

# rate_limiter

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_limit(self, identifier: str, limit: int, window_sec: int) -> bool:
        # Token bucket or fixed window via Redis
        # Ví dụ: INCR, EXPIRE
        key = f"rate_limit:{identifier}"
 

