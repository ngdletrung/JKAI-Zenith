import re
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import List

from core.utils.hallucination_guard import QueryClassifier, QueryType

logger = logging.getLogger("JKAI.SearchIntelligence")

# 14 fast regex patterns for realtime detection (Tier 2)
REALTIME_PATTERNS: List[re.Pattern] = [
    re.compile(r"(thời tiết|weather|nhiệt độ)", re.IGNORECASE),
    re.compile(r"(giá vàng|gold price)", re.IGNORECASE),
    re.compile(r"(chứng khoán|cổ phiếu|mã cp|stock price|thị trường chứng khoán)", re.IGNORECASE),
    re.compile(r"(tỷ số|kết quả bóng đá|lịch thi đấu|ngoại hạng anh|champions league|football score)", re.IGNORECASE),
    re.compile(r"(giá xăng|giá dầu|xăng dầu|petrol price|gas price)", re.IGNORECASE),
    re.compile(r"(giá bitcoin|giá coin|crypto price|btc price)", re.IGNORECASE),
    re.compile(r"(tin tức|thời sự|tin mới nhất|breaking news|hot news)", re.IGNORECASE),
    re.compile(r"(lãi suất ngân hàng|lãi suất|interest rate)", re.IGNORECASE),
    re.compile(r"(tỷ giá|tỉ giá|exchange rate|giá usd)", re.IGNORECASE),
    re.compile(r"(hôm nay|hiện nay|bây giờ|today|right now|current time)", re.IGNORECASE),
    re.compile(r"(mới nhất|mới ra|latest|update|cập nhật)", re.IGNORECASE),
    re.compile(r"(lịch chiếu phim|showtimes)", re.IGNORECASE),
    re.compile(r"(xổ số|kqxs|vietlott)", re.IGNORECASE),
    re.compile(r"(đang diễn ra|sự kiện hôm nay|happening now)", re.IGNORECASE),
]

# Tier 4: anchor sentences đại diện cho các câu realtime phổ biến (dùng cho embedding fallback)
_REALTIME_ANCHOR_TEXTS = [
    "giá vàng hôm nay là bao nhiêu",
    "thời tiết ngày mai thế nào",
    "tin tức mới nhất trong ngày",
    "tỷ giá usd hôm nay",
    "giá bitcoin hiện tại",
    "kết quả bóng đá đêm qua",
    "giá xăng mới nhất",
    "lãi suất ngân hàng hiện nay",
    "cập nhật thị trường chứng khoán",
    "sự kiện đang diễn ra tại việt nam",
]


@dataclass
class SearchContext:
    """Clean representation of the search context after intelligence analysis."""
    query: str
    query_type: QueryType
    is_realtime: bool
    needs_disclaimer: bool
    should_inject_memory: bool


class SearchIntelligenceLayer:
    """Layer responsible for analyzing queries, managing query classification caching,

    applying the Realtime Cascade detection, and making selective memory injection decisions.
    """

    def __init__(self, classifier: QueryClassifier | None = None) -> None:
        self.classifier = classifier or QueryClassifier()

    @lru_cache(maxsize=1024)
    def classify_query(self, query: str) -> QueryType:
        """Classifies query using QueryClassifier and caches the result with LRU Cache.

        This avoids repeating classification for the same query.
        """
        logger.debug("Classifying query (cache miss): %s", query[:60])
        return self.classifier.classify(query)

    @lru_cache(maxsize=1024)
    def is_realtime_cached(self, query: str) -> bool:
        """Realtime Cascade implementation wrapped with LRU Cache (Tier 1).

        This acts as the first tier of the Realtime Cascade.
        """
        return self._detect_realtime_cascade_uncached(query)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _embedding_fallback_is_realtime(self, query: str, threshold: float = 0.75) -> bool:
        """Tier 4: Embedding-based fallback.

        Computes cosine similarity between the query embedding and each anchor
        sentence embedding. Returns True if any anchor exceeds the threshold.
        This runs only when Tiers 2 and 3 both fail to detect realtime intent.
        """
        try:
            from core.utils.embed import get_embedding  # type: ignore
            query_vec = get_embedding(query)
            if not query_vec:
                return False
            for anchor in _REALTIME_ANCHOR_TEXTS:
                anchor_vec = get_embedding(anchor)
                if not anchor_vec:
                    continue
                sim = self._cosine_similarity(query_vec, anchor_vec)
                if sim >= threshold:
                    logger.debug(
                        "Realtime detected via Tier 4 (embedding sim=%.3f) for: %s", sim, query[:60]
                    )
                    return True
        except Exception as _e:
            logger.debug("Tier 4 embedding fallback unavailable: %s", _e)
        return False

    def _detect_realtime_cascade_uncached(self, query: str) -> bool:
        """Performs Realtime Cascade detection (Tiers 2, 3 & 4)."""
        # 🛡️ [SOVEREIGNTY & REFLEX GATE]: Tuyệt đối không kích hoạt web search cho các câu hỏi về danh tính, hệ thống JKAI, trò chuyện, toán học hay năng lực nội tại.
        q_lower = query.lower()
        sovereign_keywords = [
            "jkai", "zenith", "antigravity", "master", "mô hình", "model", "trình độ", 
            "năng lực", "cấu hình", "bạn là", "tôi hỏi", "kiểm tra", "hoạt động", 
            "tính năng", "quy trình", "qui trình", "nhân", "chia", "cộng", "trừ", 
            "bằng mấy", "giúp gì", "làm được gì", "bài toán", "hệ thống", "trợ lý", "cải tiến"
        ]
        if any(kw in q_lower for kw in sovereign_keywords):
            logger.debug("Sovereign/Reflex keyword detected in '%s' -> Suppressing realtime search.", query[:60])
            return False

        # Tier 2: Fast keyword regex checks (14 patterns)
        for pattern in REALTIME_PATTERNS:
            if pattern.search(query):
                logger.debug("Realtime detected via Tier 2 (Regex pattern match): %s", query[:60])
                return True

        # Tier 3: QueryClassifier identification (FACT_CRITICAL or TEMPORAL_SENSITIVE)
        query_type = self.classify_query(query)
        if query_type in (QueryType.FACT_CRITICAL, QueryType.TEMPORAL_SENSITIVE):
            logger.debug("Realtime detected via Tier 3 (QueryClassifier type %s): %s", query_type, query[:60])
            return True

        # Tier 4: Embedding similarity fallback (catches ambiguous/paraphrased realtime queries)
        if self._embedding_fallback_is_realtime(query):
            return True

        return False

    def should_inject_memory(self, query_type: QueryType, run_mode: str = "default") -> bool:
        """Selective Memory Injector: decides whether memory should be injected.

        For example, do not skip memory for logic, creative, or parametric questions (PARAMETRIC_SAFE).
        """
        if query_type == QueryType.PARAMETRIC_SAFE:
            return True
        if run_mode == "strict_rag":
            return False
        return True

    def analyze(self, query: str, run_mode: str = "default") -> SearchContext:
        """Analyzes a query and builds a clean SearchContext."""
        # Tier 1: Check cache is implicitly done inside the cached method call
        is_realtime = self.is_realtime_cached(query)
        query_type = self.classify_query(query)

        # Decide if disclaimer is needed
        needs_disclaimer = is_realtime or query_type in (QueryType.FACT_CRITICAL, QueryType.TEMPORAL_SENSITIVE)

        # Decide if memory should be injected
        inject_mem = self.should_inject_memory(query_type, run_mode=run_mode)

        return SearchContext(
            query=query,
            query_type=query_type,
            is_realtime=is_realtime,
            needs_disclaimer=needs_disclaimer,
            should_inject_memory=inject_mem,
        )
