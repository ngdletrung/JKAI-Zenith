"""
Bo dem toan he thong cho ai-brain (nhieu worker).

Moi worker giu bo dem rieng trong RAM, nen so lieu cua worker duoc
load-balancer chon khong dai dien cho ca he thong. Hai noi dang can so lieu
he thong (firewall, critic) dung chung mot noi luu duy nhat o day thay vi moi
noi tu viet lai vong Redis + fail-fast.
"""
import logging
import time

logger = logging.getLogger("SystemCounters")


class SystemCounters:
    _PREFIX = "jkai:counters:"

    def __init__(self):
        self._down_until = 0.0
        self._local = {}

    def bump(self, counter: str, field: str, amount: int = 1) -> None:
        """Tang bo dem cuc bo va (neu Redis song) bo dem toan he thong."""
        key = f"{counter}:{field}"
        self._local[key] = self._local.get(key, 0) + amount

        # Fail fast: Redis chet khong duoc cong connect-timeout vao moi request.
        if time.time() < self._down_until:
            return
        redis = self._get_redis()
        if not redis:
            return
        try:
            redis.hincrby(self._PREFIX + counter, field, amount)
        except Exception:
            self._down_until = time.time() + 30

    def local(self, counter: str) -> dict:
        prefix = f"{counter}:"
        return {
            key[len(prefix):]: value
            for key, value in self._local.items()
            if key.startswith(prefix)
        }

    def read(self, counter: str) -> dict:
        """So lieu toan he thong neu Redis co du lieu, nguoc lai la cua worker nay."""
        result = {"source": "local", "counters": self.local(counter)}
        redis = self._get_redis()
        if not redis:
            return result
        try:
            raw = redis.hgetall(self._PREFIX + counter) or {}
            if not raw:
                return result
            counters = {}
            for field, value in raw.items():
                name = field.decode() if isinstance(field, bytes) else field
                try:
                    counters[name] = int(value)
                except (TypeError, ValueError):
                    continue
            if counters:
                result = {"source": "redis", "counters": counters}
        except Exception:
            pass
        return result

    def _get_redis(self):
        try:
            from redis_client import get_redis
            return get_redis()
        except Exception:
            return None


system_counters = SystemCounters()
