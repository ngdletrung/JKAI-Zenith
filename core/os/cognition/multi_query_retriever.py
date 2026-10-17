# -*- coding: utf-8 -*-
"""
core/os/cognition/multi_query_retriever.py
===========================================
[Trọng điểm 2 - Hiện đại hóa Kiến trúc Tìm kiếm SOTA: Học hỏi Perplexica & Khoj]
Multi-Query Deep Retrieval & Stream Buffering:
1. Query Decomposition: Tự động phân tách 1 yêu cầu bao quát của Master thành
   3 góc nhìn truy vấn con (Sub-queries) chuyên sâu theo lĩnh vực (Finance/Tech/News/General).
2. Concurrent Retrieval: Truy vấn song song các sub-queries qua các nhà cung cấp thực tế.
3. Cross-Query Deduplication & Hybrid Scoring: Khử trùng lặp URL và xếp hạng ưu tiên các nguồn xuất hiện đa góc nhìn.
4. Deep Article Ingestion & StreamBufferStore: Tự động đọc sâu các bài phân tích hàng đầu
   và nạp toàn văn vào StreamBufferStore kèm `stream_id` để Synthesizer T6 tổng hợp báo cáo sâu sắc.
5. Observability: Ghi nhận sự kiện cấu trúc vào `CognitiveEventStore`.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse

from core.utils.stream_buffer_store import store_stream

logger = logging.getLogger("JKAI.MultiQueryRetriever")


class QueryDomain(str, Enum):
    FINANCE_STOCK = "FINANCE_STOCK"
    TECH_SOFTWARE = "TECH_SOFTWARE"
    ACADEMIC_SCIENCE = "ACADEMIC_SCIENCE"
    NEWS_CURRENT = "NEWS_CURRENT"
    GENERAL = "GENERAL"


FINANCE_KEYWORDS = {
    "chứng khoán", "chung khoan", "vn-index", "vnindex", "cổ phiếu", "co phieu",
    "thị trường", "thi truong", "giao dịch", "giao dich", "thanh khoản", "thanh khoan",
    "khối ngoại", "khoi ngoai", "tự doanh", "tu doanh", "ngân hàng", "ngan hang",
    "bất động sản", "bat dong san", "lãi suất", "lai suat", "tài chính", "tai chinh",
    "vnd", "usd", "vàng", "vang", "bitcoin", "crypto", "cpi", "gdp", "stock", "stocks"
}

TECH_KEYWORDS = {
    "code", "coding", "python", "docker", "kubernetes", "linux", "kernel", "microkernel",
    "architecture", "kiến trúc", "kien truc", "api", "database", "sql", "nosql",
    "algorithm", "thuật toán", "thuat toan", "git", "ci/cd", "devops", "benchmark",
    "asyncio", "golang", "rust", "typescript", "framework", "performance", "security"
}

NEWS_KEYWORDS = {
    "hôm nay", "hom nay", "tuần này", "tuan nay", "tuần qua", "tuan qua",
    "mới nhất", "moi nhat", "tin tức", "tin tuc", "thời sự", "thoi su",
    "bão", "thời tiết", "chính trị", "sự kiện", "su kien", "nóng", "nong"
}


def classify_query_domain(query: str) -> QueryDomain:
    """Phân loại lĩnh vực câu hỏi để áp dụng chiến lược phân tách sub-queries tối ưu."""
    q_lower = (query or "").lower()
    
    if any(k in q_lower for k in FINANCE_KEYWORDS):
        return QueryDomain.FINANCE_STOCK
    if any(k in q_lower for k in TECH_KEYWORDS):
        return QueryDomain.TECH_SOFTWARE
    if any(k in q_lower for k in NEWS_KEYWORDS):
        return QueryDomain.NEWS_CURRENT
    
    return QueryDomain.GENERAL


def clean_base_query(query: str) -> str:
    """Loại bỏ các từ chỉ thị thừa để trích xuất lõi chủ đề."""
    q = str(query or "").strip()
    noise_patterns = [
        r"^hãy\s+phân\s+tích\s+",
        r"^phân\s+tích\s+",
        r"^tìm\s+kiếm\s+",
        r"^cho\s+tôi\s+biết\s+",
        r"^hãy\s+cho\s+biết\s+",
        r"^tổng\s+hợp\s+",
        r"^báo\s+cáo\s+",
        r"^tra\s+cứu\s+",
        r"\s+nguồn\s+tin\s+cậy.*$",
        r"\s+chi\s+tiết\s+nhất.*$",
    ]
    for p in noise_patterns:
        q = re.sub(p, "", q, flags=re.IGNORECASE).strip()
    return q


def decompose_query(query: str, domain: Optional[QueryDomain] = None) -> List[str]:
    """
    Bóc tách 1 câu hỏi thành 3 góc nhìn truy vấn con (Aspect-Based Sub-Queries).
    Đảm bảo bao phủ:
    1. Xu hướng / Thực trạng chỉ số cốt lõi.
    2. Dòng tiền / Cơ cấu động lực / Động thái chuyên sâu.
    3. Nhóm ngành / Cổ phiếu / Thành phần dẫn dắt hoặc tác động.
    """
    base_q = clean_base_query(query)
    eff_domain = domain or classify_query_domain(query)

    if eff_domain == QueryDomain.FINANCE_STOCK:
        return [
            f"{base_q} diễn biến xu hướng chỉ số vn-index thanh khoản giao dịch",
            f"{base_q} dòng tiền mua bán ròng khối ngoại tự doanh",
            f"{base_q} các nhóm ngành dẫn dắt cổ phiếu tâm điểm nổi bật",
        ]

    if eff_domain == QueryDomain.TECH_SOFTWARE:
        return [
            f"{base_q} core architecture design principles overview",
            f"{base_q} benchmark comparison performance tradeoffs",
            f"{base_q} best practices real-world implementation guide",
        ]

    if eff_domain == QueryDomain.NEWS_CURRENT:
        return [
            f"{base_q} diễn biến sự kiện mới nhất tổng hợp",
            f"{base_q} nguyên nhân bối cảnh nhận định chuyên gia",
            f"{base_q} tác động hệ quả phản ứng các bên",
        ]

    return [
        f"{base_q} tổng quan thông tin chính xác mới nhất",
        f"{base_q} phân tích chi tiết dữ liệu thực tế",
        f"{base_q} bài học kinh nghiệm và khuyến nghị",
    ]


def canonicalize_url(raw_url: str) -> str:
    """Chuẩn hóa URL: loại bỏ tracking parameters, trailing slash, fragment."""
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url)
        # Loại bỏ query parameters tracking (utm_*, ref, etc.)
        clean_query_parts = []
        if parsed.query:
            for param in parsed.query.split("&"):
                k = param.split("=")[0].lower()
                if not (k.startswith("utm_") or k in ("ref", "fbclid", "gclid")):
                    clean_query_parts.append(param)
        clean_query = "&".join(clean_query_parts)
        clean_path = parsed.path.rstrip("/")
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            clean_query,
            "",  # fragment bỏ qua
        ))
    except Exception:
        return raw_url.strip()


def deduplicate_and_rank_results(
    subquery_results: Sequence[Tuple[str, List[Dict[str, Any]]]],
    window_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Hợp nhất và khử trùng lặp kết quả từ nhiều sub-queries.
    Tính điểm uy tín và tần suất xuất hiện chéo (Cross-Query Consensus).
    Freshness (case vàng 15/10): bài cũ quá cửa sổ intent bị trừ điểm và gắn nhãn stale.
    """
    seen: Dict[str, Dict[str, Any]] = {}

    for sub_q, items in subquery_results:
        for idx, item in enumerate(items):
            url = str(item.get("url") or item.get("link") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            canon_url = canonicalize_url(url)
            if not canon_url:
                continue

            if canon_url not in seen:
                try:
                    from tools.web_search import freshness_label
                    pub = str(item.get("published_at") or "").strip()
                    fresh = freshness_label(
                        pub, window_days,
                        str(item.get("retrieved_at") or ""),
                    )
                except Exception:
                    pub, fresh = "", "date_unknown"
                seen[canon_url] = {
                    "title": item.get("title") or "Untitled",
                    "url": url,
                    "canonical_url": canon_url,
                    "snippet": item.get("snippet") or item.get("content") or "",
                    "source": item.get("source") or "web",
                    "retrieved_at": item.get("retrieved_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "published_at": pub,
                    "freshness": fresh,
                    "matched_subqueries": [sub_q],
                    # Bài cũ quá cửa sổ intent bị trừ một nửa điểm rank
                    "rank_score": (1.0 / (idx + 1)) * (0.5 if fresh.startswith("stale:") else 1.0),
                }
            else:
                entry = seen[canon_url]
                if sub_q not in entry["matched_subqueries"]:
                    entry["matched_subqueries"].append(sub_q)
                # Tăng điểm khi nguồn xuất hiện ở nhiều góc nhìn sub-queries
                entry["rank_score"] += (1.0 / (idx + 1)) * 1.5
                # Bổ sung trích đoạn nếu dài hơn
                curr_snip = entry["snippet"]
                new_snip = item.get("snippet") or item.get("content") or ""
                if len(new_snip) > len(curr_snip):
                    entry["snippet"] = new_snip

    # Sắp xếp theo rank_score giảm dần
    ranked = sorted(seen.values(), key=lambda x: x["rank_score"], reverse=True)
    return ranked


@dataclass
class MultiQueryConfig:
    max_subqueries: int = 3
    results_per_subquery: int = 4
    max_deep_reads: int = 2
    max_preview_chars: int = 8000
    deep_read_timeout: float = 15.0
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "MultiQueryConfig":
        enabled = os.getenv("JKAI_MULTI_QUERY_ENABLED", "1") != "0"
        max_reads = int(os.getenv("JKAI_MULTI_QUERY_DEEP_READS", "2"))
        return cls(max_deep_reads=max_reads, enabled=enabled)


class MultiQueryRetriever:
    """
    Bộ máy truy xuất sâu đa góc nhìn (Multi-Query Deep Retrieval Engine):
    - Đảm bảo độc lập, trung thực và tối ưu hoá bộ nhớ qua StreamBufferStore.
    """

    def __init__(self, config: Optional[MultiQueryConfig] = None):
        self.config = config or MultiQueryConfig.from_env()

    async def retrieve_deep(
        self,
        query: str,
        task_id: str = "sys",
        trace_id: str = "trace_multi_query",
        local_only: bool = False,
        executor_gateway: Optional[Any] = None,
        logger_emitter: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Thực thi quy trình Multi-Query Deep Retrieval trọn vẹn:
        1. Decompose Query thành 3 sub-queries.
        2. Chạy đồng thời tìm kiếm cho cả 3 sub-queries.
        3. Khử trùng lặp và xếp hạng.
        4. Đọc sâu các URL bài viết chất lượng cao nhất.
        5. Đóng gói vào StreamBufferStore và trả về kết quả cấu trúc.
        """
        def _log(msg: str):
            if logger_emitter and callable(logger_emitter):
                try:
                    logger_emitter("EXECUTOR", msg, task_id, trace_id=trace_id)
                except Exception:
                    pass

        domain = classify_query_domain(query)
        sub_queries = decompose_query(query, domain=domain)[: self.config.max_subqueries]

        _log(f"🧠 [MULTI-QUERY] Nhận diện lĩnh vực '{domain.value}'. Đã phân tách thành {len(sub_queries)} góc nhìn truy vấn con.")

        # Ghi nhận sự kiện khởi động
        try:
            from core.os.cognition.event_model import event_store
            event_store.append(
                aggregate_id=task_id,
                event_type="MULTI_QUERY_RETRIEVAL_STARTED",
                payload={"query": query, "domain": domain.value, "sub_queries": sub_queries},
                correlation_id=trace_id,
            )
        except Exception:
            pass

        from tools.web_search import execute_real_web_search_sync

        async def _search_one(sq: str) -> Tuple[str, List[Dict[str, Any]]]:
            try:
                # Chạy search sync trong threadpool
                res = await asyncio.to_thread(
                    execute_real_web_search_sync,
                    query=sq,
                    task_id=task_id,
                    local_only=local_only,
                    max_results=self.config.results_per_subquery,
                )
                if isinstance(res, dict) and res.get("status") == "success":
                    return sq, res.get("results") or []
                return sq, []
            except Exception as e:
                logger.warning("[MULTI-QUERY] Lỗi tìm kiếm subquery '%s': %s", sq, e)
                return sq, []

        # Chạy song song cả 3 sub-queries
        tasks = [_search_one(sq) for sq in sub_queries]
        subquery_outputs = await asyncio.gather(*tasks)

        # Hợp nhất và khử trùng lặp (kèm hạ điểm bài cũ quá cửa sổ intent)
        try:
            from tools.web_search import detect_time_intent
            _window = detect_time_intent(query)
        except Exception:
            _window = None
        deduped = deduplicate_and_rank_results(subquery_outputs, window_days=_window)
        _log(f"🌐 [MULTI-QUERY] Thu thập thành công {len(deduped)} nguồn thông tin không trùng lặp.")

        if not deduped:
            from tools.web_search import build_transparent_refusal
            return build_transparent_refusal(
                query=query,
                reason="SEARCH_PROVIDERS_UNREACHABLE",
                detail="Không thu thập được dữ liệu từ tất cả các sub-queries.",
            )

        # Chọn top URLs chất lượng cao để đọc sâu
        from core.os.cognition.in_flight_chain import filter_candidate_urls
        deep_read_urls = filter_candidate_urls(deduped, max_urls=self.config.max_deep_reads)

        deep_articles: List[Dict[str, Any]] = []
        if deep_read_urls:
            _log(f"⚡ [MULTI-QUERY] Đang đọc sâu toàn văn {len(deep_read_urls)} bài phân tích tâm điểm...")
            from tools.web_search import detect_time_intent, fetch_url_content

            try:
                _deep_window = detect_time_intent(query)
            except Exception:
                _deep_window = None

            async def _fetch_one(target_url: str) -> Optional[Dict[str, Any]]:
                try:
                    fetched = await asyncio.to_thread(
                        fetch_url_content,
                        target_url,
                        self.config.deep_read_timeout,
                        20000,
                        _deep_window,
                    )
                except Exception as read_err:
                    logger.warning("[MULTI-QUERY] Không thể đọc sâu URL %s: %s", target_url, read_err)
                    return None
                if fetched.get("status") != "success" or not fetched.get("text"):
                    return None
                article: Dict[str, Any] = {"url": target_url, "full_text": fetched["text"]}
                if fetched.get("published_at"):
                    article["published_at"] = fetched["published_at"]
                    article["freshness"] = fetched.get("freshness", "")
                return article

            for url in deep_read_urls:
                article = await _fetch_one(url)
                if article:
                    deep_articles.append(article)

        # Xây dựng nội dung toàn văn hoàn chỉnh
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report_sections: List[str] = [
            f"# Báo cáo Dữ liệu Đa Chiều (Multi-Query Deep Retrieval): {query}",
            f"Thời điểm Truy xuất (UTC) / Retrieved at: {now_utc}",
            f"Lĩnh vực nhận diện: {domain.value}",
            f"Các góc nhìn truy vấn: {', '.join(sub_queries)}",
            "",
            "## I. BẢNG TỔNG HỢP CÁC NGUỒN TIN HÀNG ĐẦU:",
        ]

        for i, item in enumerate(deduped[:8], 1):
            report_sections.append(f"[{i}] {item['title']}")
            report_sections.append(f"URL: {item['url']}")
            report_sections.append(f"Trích đoạn: {item['snippet']}")
            report_sections.append(f"Độ trùng khớp góc nhìn: {len(item.get('matched_subqueries', []))}/3 sub-queries")
            report_sections.append("")

        if deep_articles:
            report_sections.append("## II. TRÍCH XUẤT TOÀN VĂN TỪ CÁC BÀI BÁO PHÂN TÍCH CHUYÊN SÂU:")
            for idx, article in enumerate(deep_articles, 1):
                report_sections.append(f"### [BÀI {idx}] Nguồn: {article['url']}")
                report_sections.append(article["full_text"][:4000])
                report_sections.append("")

        full_text_report = "\n".join(report_sections).strip()

        # Tích hợp StreamBufferStore nếu nội dung vượt ngưỡng
        stream_id = None
        if len(full_text_report) > 4000:
            env = store_stream(
                content=full_text_report,
                source_tool="multi_query_retriever",
                task_id=task_id,
                mission_id=task_id,
                preview_chars=self.config.max_preview_chars,
                metadata={
                    "query": query,
                    "domain": domain.value,
                    "sub_queries": sub_queries,
                    "deduped_count": len(deduped),
                },
            )
            stream_id = env.get("stream_id")

        # Ghi nhận sự kiện hoàn tất vào CognitiveEventStore
        try:
            from core.os.cognition.event_model import event_store
            event_store.append(
                aggregate_id=task_id,
                event_type="MULTI_QUERY_RETRIEVAL_COMPLETED",
                payload={
                    "query": query,
                    "domain": domain.value,
                    "sub_queries_count": len(sub_queries),
                    "deduped_sources": len(deduped),
                    "deep_reads": len(deep_articles),
                    "stream_id": stream_id,
                },
                correlation_id=trace_id,
            )
        except Exception:
            pass

        return {
            "status": "success",
            "is_simulated": False,
            "original_query": query,
            "domain": domain.value,
            "sub_queries": sub_queries,
            "total_sources_found": len(deduped),
            "deep_reads_count": len(deep_articles),
            "stream_id": stream_id,
            "results": deduped[:8],
            "output": full_text_report,
        }


# Singleton instance
multi_query_retriever = MultiQueryRetriever()
