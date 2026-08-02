import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("PipelineCache")

DEFAULT_TTL = 3600
REALTIME_KEYWORDS = [
    "thời tiết", "weather", "tin tức", "news", "giá vàng", "tỷ giá",
    "chứng khoán", "hôm nay", "bây giờ", "hiện tại", "nhiệt độ",
    "temperature", "stock", "price", "forex", "crypto"
]

try:
    from core.utils.hallucination_guard import QueryClassifier, query_classifier, QueryType
except ImportError:
    QueryClassifier = None
    query_classifier = None
    QueryType = None


def _cache_key(goal: str, mode: str = "auto") -> str:
    raw = f"{goal.strip().lower()}::mode={mode}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"pipeline:cache:{h}"


def _is_realtime(goal: str) -> bool:
    g = goal.lower()
    return any(kw in g for kw in REALTIME_KEYWORDS)


def _ttl_for(goal: str) -> int:
    if query_classifier is not None and QueryType is not None:
        try:
            qtype = query_classifier.classify(goal)
            if qtype == QueryType.FACT_CRITICAL:
                return 86400
            elif qtype == QueryType.TEMPORAL_SENSITIVE:
                return 300
            elif qtype == QueryType.PARAMETRIC_SAFE:
                return 3600
            elif qtype == QueryType.AMBIGUOUS:
                return 1800
        except Exception as e:
            logger.warning("Error classifying query for TTL fallback: %s", e)
    if _is_realtime(goal):
        return 60
    return DEFAULT_TTL


def _is_error_response(answer: str) -> bool:
    if not isinstance(answer, str):
        return False
    clean = answer.strip().lower()
    if not clean:
        return False
    if clean in ["aborted by master", "error", "exception", "failed", "internal server error", "system error"]:
        return True
    import re
    if re.match(r"^(?:error|failed|exception|aborted)[\s\:\-\#]*[a-zA-Z0-9_\s\.\,\(\)\[\]\'\"\/\\\-]{0,120}$", clean):
        return True
    if clean.startswith("traceback (most recent call last):"):
        return True
    return False


class PipelineCache:
    def __init__(self):
        self._redis = None
        self._local: Dict[str, tuple] = {}

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis as rd
                host = "redis-ai"
                self._redis = rd.Redis(
                    host=host, port=6379, db=0,
                    socket_timeout=2, socket_connect_timeout=2,
                    decode_responses=True
                )
            except Exception:
                self._redis = False
        return self._redis if self._redis else None

    async def get(self, goal: str, mode: str = "auto") -> Optional[Dict[str, Any]]:
        key = _cache_key(goal, mode)
        r = self._get_redis()
        if r:
            try:
                val = r.get(key)
                if val:
                    data = json.loads(val)
                    logger.info("[CACHE-HIT] key=%s goal=%.60s mode=%s", key, goal, mode)
                    return data
            except Exception:
                pass
        cached = self._local.get(key)
        if cached:
            data, exp = cached
            if time.time() < exp:
                logger.info("[CACHE-HIT-LOCAL] key=%s", key)
                return json.loads(data)
            else:
                self._local.pop(key, None)
        return None

    async def set(self, goal: str, mode: str, result: Dict[str, Any]) -> None:
        key = _cache_key(goal, mode)
        # Do not cache error/abort responses
        answer = result.get("answer") or result.get("msg") or result.get("response") or ""
        if isinstance(answer, str) and _is_error_response(answer):
            logger.warning("[CACHE-SKIP] Aborted/error response not cached key=%s goal=%.60s", key, goal)
            return
        ttl = _ttl_for(goal)
        serialized = json.dumps(result, ensure_ascii=False, default=str)
        self._local[key] = (serialized, time.time() + ttl)
        r = self._get_redis()
        if r:
            try:
                r.setex(key, ttl, serialized)
                logger.debug("[CACHE-SET] key=%s ttl=%ds", key, ttl)
            except Exception:
                pass

    async def invalidate(self, goal: str, mode: str = "auto") -> None:
        key = _cache_key(goal, mode)
        self._local.pop(key, None)
        r = self._get_redis()
        if r:
            try:
                r.delete(key)
            except Exception:
                pass


pipeline_cache = PipelineCache()
