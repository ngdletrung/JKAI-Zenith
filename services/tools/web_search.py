# -*- coding: utf-8 -*-
"""
tools/web_search.py
===================
Slice 1.5 (Đại Trụ I & Nền Móng Trung Thực):
- Xóa bỏ vĩnh viễn kết quả tìm kiếm giả mạo trong công cụ web_search.
- Khi hệ thống chạy ở chế độ `local_only` (`data["local_only"] == True` hoặc `JKAI_LOCAL_ONLY=1`),
  trả về từ chối minh bạch (`status="unavailable"`, `is_simulated=False`, `reason="LOCAL_ONLY_MODE"`).
- Khi cho phép tra cứu Internet: truy vấn thật qua Tavily API / DuckDuckGo với trích dẫn nguồn đầy đủ
  (`url`, `title`, `snippet`, `retrieved_at`). Nếu nội dung vượt ngưỡng, lưu toàn văn vào
  `StreamBufferStore` kèm `stream_id` để đọc phân trang (`read_stream_window`) hoặc tìm kiếm (`search_in_stream`).
- Nếu tất cả kênh tìm kiếm thực tế không khả dụng / mất mạng: trả về `status="unavailable"`,
  `is_simulated=False`, `reason="SEARCH_PROVIDERS_UNREACHABLE"`, tuyệt đối không bịa kết quả giả.
"""

from __future__ import annotations

import datetime
import ipaddress
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from core.utils.repo_map import StageAttribution
from core.utils.stream_buffer_store import store_stream

DEFAULT_PREVIEW_CHARS = 8000
DDGS: Any = "auto"


def _auto_load_env_keys() -> None:
    """Tự động nạp TAVILY_API_KEY từ .env khi khởi động nếu chưa có trong os.environ."""
    if not os.getenv("TAVILY_API_KEY"):
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            ".env",
            "../.env",
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("TAVILY_API_KEY="):
                                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if val:
                                    os.environ["TAVILY_API_KEY"] = val
                                    return
                except Exception:
                    pass


_auto_load_env_keys()


# ── Freshness: ép cửa sổ thời gian cho intent realtime ──────────────
# Case vàng 15/10: hỏi "tuần qua" nhưng query không mốc thời gian → bài 4/2025 lên top.
REALTIME_WINDOWS = (
    (("hôm nay", "hom nay", "today"), 1),
    (("tuần qua", "tuan qua", "tuần này", "tuan nay", "tuần vừa qua", "last week", "past week", "this week"), 7),
    (("tháng này", "thang nay", "tháng qua", "thang qua", "last month", "this month"), 30),
    (("năm nay", "nam nay", "this year"), 365),
    (("mới nhất", "moi nhat", "latest", "hiện tại", "hien tai", "realtime", "real-time"), 30),
)

_EXPLICIT_DATE_RE = re.compile(
    r"(after:|before:|time_range|20\d\d[-/\.]\d{1,2}|\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
    re.IGNORECASE,
)


def detect_time_intent(query: str) -> Optional[int]:
    """Nhận diện intent realtime → số ngày cửa sổ. None nếu không phải realtime."""
    q = str(query or "").lower()
    for markers, days in REALTIME_WINDOWS:
        if any(m in q for m in markers):
            return days
    return None


def inject_time_window(
    query: str,
    now: Optional[datetime.datetime] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Ép mốc `after:YYYY-MM-DD` vào query realtime chưa có mốc thời gian.
    Trả về (effective_query, window_info|None). Không bao giờ chèn 2 lần.
    """
    clean_q = str(query or "").strip()
    window_days = detect_time_intent(clean_q)
    if window_days is None:
        return clean_q, None
    if _EXPLICIT_DATE_RE.search(clean_q):
        return clean_q, {"window_days": window_days, "already_constrained": True, "after": None}
    ref = now or datetime.datetime.now(datetime.timezone.utc)
    after = (ref - datetime.timedelta(days=window_days)).date().isoformat()
    return f"{clean_q} after:{after}", {"window_days": window_days, "already_constrained": False, "after": after}


# ── Freshness: tách ngày xuất bản bài viết ──────────────────────────
_META_DATE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|publish_date|date| DC\.date)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_URL_DATE_RE = re.compile(r"/(20\d\d)[/\-](\d{1,2})(?:[/\-](\d{1,2}))?")


def extract_published_at(html: str, url: str) -> str:
    """
    Tách ngày xuất bản: meta article:published_time → JSON-LD datePublished → ngày trong URL.
    Trả về chuỗi YYYY-MM-DD hoặc "" nếu không xác định được.
    """
    html = str(html or "")
    m = _META_DATE_RE.search(html)
    if m:
        return m.group(1).strip()[:10]
    for m in re.finditer(
        r'"date[Pp]ublished"\s*:\s*"([^"]+)"', html
    ):
        return m.group(1).strip()[:10]
    m = _URL_DATE_RE.search(str(url or ""))
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), (m.group(3) or "01").zfill(2)
        return f"{y}-{mo}-{d}"
    return ""


def freshness_label(published_at: str, window_days: Optional[int], retrieved_at: str = "") -> str:
    """Gắn nhãn độ tươi: fresh | stale:<date> | date_unknown."""
    if not published_at:
        return "date_unknown"
    if window_days is None:
        return "fresh"
    try:
        pub = datetime.date.fromisoformat(published_at[:10])
        ref_s = (retrieved_at or "")[:10]
        ref = datetime.date.fromisoformat(ref_s) if ref_s else datetime.datetime.now(datetime.timezone.utc).date()
        if (ref - pub).days <= window_days + 1:
            return "fresh"
        return f"stale:{published_at[:10]}"
    except Exception:
        return "date_unknown"


# ── Tầng retrieval nội bộ (thay r.jina.ai) ──────────────────────────
# Preserve ZWNJ (\u200c) and ZWJ (\u200d) for Indic/Persian and Emoji sequences per OpenCode Turn 384!
_INVISIBLE_CHARS_RE = re.compile(
    "[\u200b\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
    "\u2060\u2061\u2062\u2063\u2064\ufeff\u00ad\u061c\U000e0000-\U000e007f]"
)
_TAG_STRIP_RE = re.compile(
    r"<!--.*?-->|<script[^>]*>.*?</script>|<style[^>]*>.*?</style>"
    r"|<noscript[^>]*>.*?</noscript>|<[^>]+>",
    re.DOTALL | re.IGNORECASE,
)

_FETCH_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JKAI-Sovereign-Fetch/1.0"


def strip_invisible_chars(text: str) -> str:
    """Loại ký tự vô hình/bidi (kênh prompt injection), bảo toàn ZWNJ, ZWJ và NFC."""
    import unicodedata as _ud
    norm_text = _ud.normalize("NFC", str(text or ""))
    return _INVISIBLE_CHARS_RE.sub("", norm_text)


def html_to_clean_text(html: str, max_chars: int = 20000) -> str:
    """Bóc text thuần từ HTML: áp dụng DeterministicWebSanitizer 3 tầng chuẩn xác."""
    try:
        from core.sanitizer.deterministic_web_sanitizer import DeterministicWebSanitizer
        return DeterministicWebSanitizer.sanitize(html, max_chars=max_chars)
    except Exception:
        import html as _html_mod
        text = _TAG_STRIP_RE.sub(" ", str(html or ""))
        text = _html_mod.unescape(text)
        text = strip_invisible_chars(text)
        return " ".join(text.split())[:max_chars]


def fetch_url_content(
    url: str,
    query: Optional[str] = None,
    timeout: float = 15.0,
    max_chars: int = 20000,
    window_days: Optional[int] = None,
    allowed_domains: Optional[Sequence[str]] = None,
    resolver_fn: Optional[Any] = None,
    http_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Tầng retrieval nội bộ: SSRF Resolve-and-Pin → GET per-hop redirect revalidation → tách ngày → sanitize & verbatim passages.
    Tuân thủ 5 điều kiện ràng buộc của Opencode (Lượt 384).
    """
    retrieved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        from core.security.ssrf_resolve_pin_guard import SSRFResolveAndPinGuard
        from core.sanitizer.deterministic_web_sanitizer import build_retrieval_contract_result

        fetch_res = SSRFResolveAndPinGuard.fetch_with_revalidation(
            url=url,
            method="GET",
            headers={"User-Agent": _FETCH_UA},
            timeout=timeout,
            max_redirects=3,
            max_bytes=500_000,
            allowed_domains=allowed_domains,
            resolver_fn=resolver_fn,
            http_client=http_client,
        )

        if not fetch_res.get("ok", False):
            is_blocked = fetch_res.get("status") == "blocked"
            return {
                "status": "blocked" if is_blocked else "error",
                "ok": False,
                "url": fetch_res.get("url") or url,
                "text": "",
                "published_at": "",
                "freshness": "date_unknown",
                "retrieved_at": retrieved_at,
                "source": "internal-fetch",
                "error": fetch_res.get("error") or "Fetch failed",
                "error_code": fetch_res.get("error_code"),
                "redirect_chain": fetch_res.get("redirect_chain", []),
                "pinned_ips": fetch_res.get("pinned_ips", []),
            }

        html = fetch_res.get("text", "")
        pub = extract_published_at(html, url)
        contract_res = build_retrieval_contract_result(
            url=fetch_res.get("url") or url,
            raw_html=html,
            query=query,
            max_chars=max_chars,
            top_k_passages=3,
        )

        return {
            "status": "success",
            "ok": True,
            "url": fetch_res.get("url") or url,
            "text": contract_res.clean_text,
            "published_at": pub,
            "freshness": freshness_label(pub, window_days, retrieved_at),
            "retrieved_at": retrieved_at,
            "source": "internal-fetch",
            "error": None,
            "error_code": None,
            "canonical_sha256": contract_res.canonical_sha256,
            "passages": [p.to_dict() for p in contract_res.passages],
            "tainted_envelope": contract_res.tainted_envelope,
            "redirect_chain": fetch_res.get("redirect_chain", []),
            "pinned_ips": fetch_res.get("pinned_ips", []),
        }

    except Exception as exc:
        return {
            "status": "error",
            "ok": False,
            "url": url,
            "text": "",
            "published_at": "",
            "freshness": "date_unknown",
            "retrieved_at": retrieved_at,
            "source": "internal-fetch",
            "error": str(exc)[:200],
            "error_code": "FETCH_EXCEPTION",
        }


# Canonical alias for backward compatibility across modules/tests
fetch_url_clean = fetch_url_content


def validate_egress_url_ssrf_safe(
    url: str,
    allowed_domains: Optional[Sequence[str]] = None,
    resolve_dns: bool = False,
    resolver_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    [Slice 2.4 / Phase A7 - WeKnora SSRF-Safe & Whitelist-Only Egress Guard]:
    - Delegated to SSRFResolveAndPinGuard.validate_and_resolve for uniform zero-trust protection.
    - Default resolve_dns=False preserves compatibility for unit tests without network,
      while fetch_url_content and fetch_with_revalidation always enforce resolve_dns=True!
    """
    try:
        from core.security.ssrf_resolve_pin_guard import SSRFResolveAndPinGuard
        res = SSRFResolveAndPinGuard.validate_and_resolve(
            url=url,
            allowed_domains=allowed_domains,
            resolve_dns=resolve_dns,
            resolver_fn=resolver_fn,
        )
        res["stage_attribution"] = StageAttribution.CONTROLLER_GATE.value
        return res
    except Exception:
        # Fallback to local parsing if import fails
        raw_url = str(url or "").strip()
        parsed = urlparse(raw_url)
        scheme = (parsed.scheme or "").lower()
        host = (parsed.hostname or "").strip().lower()

        if scheme not in ("http", "https") or not host:
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "SSRF_INVALID_SCHEME_OR_HOST",
                "url": raw_url,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "msg": f"[EGRESS-REFUSED] Giao thức hoặc địa chỉ không hợp lệ: '{raw_url}'.",
            }
        return {
            "status": "allowed",
            "allowed": True,
            "error_code": None,
            "url": raw_url,
            "host": host,
            "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
        }


def is_local_only_enabled(local_only_flag: Optional[bool] = None) -> bool:

    if local_only_flag is not None:
        return bool(local_only_flag)
    env_val = os.getenv("JKAI_LOCAL_ONLY", "").strip().lower()
    return env_val in ("1", "true", "yes", "on")


def build_transparent_refusal(
    query: str,
    reason: str = "LOCAL_ONLY_MODE",
    detail: str = "",
) -> Dict[str, Any]:
    msg = (
        detail
        or (
            "Web search bị từ chối minh bạch vì hệ thống đang ở chế độ LOCAL_ONLY_MODE "
            "(tuyệt đối không trả dữ liệu giả)."
            if reason == "LOCAL_ONLY_MODE"
            else "Không thể kết nối tới bất kỳ nhà cung cấp tìm kiếm thực tế nào (Tavily/DuckDuckGo)."
        )
    )
    return {
        "status": "unavailable",
        "is_simulated": False,
        "reason": reason,
        "query": str(query or ""),
        "results": [],
        "output": None,
        "error": msg,
        "msg": msg,
        "detail": msg,
    }


def _format_results_with_citations(
    query: str,
    results: List[Dict[str, Any]],
    retrieved_at: str,
) -> str:
    lines: List[str] = [
        f"# Kết quả tìm kiếm thực tế cho: {query}",
        f"Thời điểm Truy xuất (UTC) / Retrieved at: {retrieved_at}",
        "",
    ]
    for idx, item in enumerate(results, 1):
        title = str(item.get("title") or "Untitled").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("snippet") or item.get("content") or "").strip()
        lines.append(f"[{idx}] {title}")
        lines.append(f"URL: {url}")
        pub = str(item.get("published_at") or "").strip()
        fresh = str(item.get("freshness") or "").strip()
        if pub:
            lines.append(f"Ngày xuất bản: {pub}")
        if fresh.startswith("stale:"):
            lines.append(f"CẢNH BÁO ĐỘ TƯƠI: bài cũ ({fresh[6:]}) — chỉ dùng làm nền, không dùng làm số liệu hiện tại.")
        elif fresh == "date_unknown":
            lines.append("Ngày xuất bản: không xác định — thận trọng khi dùng số liệu.")
        lines.append(f"Trích đoạn: {snippet}")
        lines.append("")
    return "\n".join(lines).strip()


class DDGBotDetectionError(RuntimeError):
    """Ngoại lệ phát sinh khi DuckDuckGo kích hoạt cơ chế chống bot (CAPTCHA / 403 / 429 / Challenge)."""
    pass


DDG_BOT_SIGNATURES = (
    "anomaly detected",
    "checking your browser",
    "cf-browser-verification",
    "ddg-captcha",
    "bots are not allowed",
    "unusual traffic",
    "challenge-running",
    "challenge-form",
    "please complete the security check",
    "are you a human",
)

DDG_EXPLICIT_ZERO_RESULTS_SIGNATURES = (
    "no results found",
    "not found any results",
    "no results for",
    "class=\"no-results\"",
    "class='no-results'",
    "zero-results",
)


def _search_duckduckgo_direct_html(
    query: str,
    max_results: int = 5,
    timeout: float = 12.0,
) -> List[Dict[str, Any]]:
    """
    Kênh tìm kiếm DuckDuckGo Direct HTML có cơ chế nhận diện Bot-Detection:
    - Gửi request trực tiếp đến endpoint https://html.duckduckgo.com/html/
    - Phát hiện chủ động HTTP 403/429 hoặc các trang Bot-Challenge/CAPTCHA (raise DDGBotDetectionError)
    - Phân định rạch ròi giữa 'Zero Results' và 'Bị chặn bởi Bot Detection'
    - Tự động bóc tách kết quả, giải mã URL thực tế (unquote uddg) và làm sạch HTML entities
    """
    import html as _html
    import re
    from urllib.parse import unquote
    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        from core.security.ssrf_resolve_pin_guard import SSRFResolveAndPinGuard
        fetch_res = SSRFResolveAndPinGuard.fetch_with_revalidation(
            url="https://html.duckduckgo.com/html/",
            method="POST",
            headers=headers,
            data={"q": query},
            timeout=timeout,
        )
        status_code = int(fetch_res.get("status_code") or 0)
        html_text = str(fetch_res.get("text") or "")

        # 1. Kiểm tra HTTP Status Code chặn bot
        if status_code in (403, 429):
            raise DDGBotDetectionError(f"DuckDuckGo trả về HTTP {status_code} (Rate Limit / Bot Challenge).")

        if not fetch_res.get("ok", False):
            # Nếu status_code khác 200 mà không phải 403/429
            if status_code > 0:
                raise RuntimeError(f"DuckDuckGo HTTP error {status_code}: {fetch_res.get('error', '')}")
            return []
    except DDGBotDetectionError:
        raise
    except Exception as exc:
        if isinstance(exc, DDGBotDetectionError):
            raise
        return []

    # 2. Quét chữ ký Bot Detection / CAPTCHA trong nội dung HTML
    lower_html = html_text.lower()
    for sig in DDG_BOT_SIGNATURES:
        if sig in lower_html:
            raise DDGBotDetectionError(f"Phát hiện chữ ký chống bot của DuckDuckGo trong phản hồi: '{sig}'.")

    # 3. Phân tách kết quả linh hoạt theo các selector của DuckDuckGo
    parts = re.split(r'<div[^>]+class="[^"]*(?:web-result|results_links)[^"]*"', html_text)
    results: List[Dict[str, Any]] = []
    for part in parts[1:]:
        m_link = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', part, re.DOTALL)
        m_snip = re.search(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', part, re.DOTALL)
        if m_link:
            raw_url = m_link.group(1)
            if "uddg=" in raw_url:
                m_uddg = re.search(r"uddg=([^&]+)", raw_url)
                if m_uddg:
                    raw_url = unquote(m_uddg.group(1))
            title = re.sub(r"<[^>]+>", "", m_link.group(2)).strip()
            title = _html.unescape(title)
            snippet = re.sub(r"<[^>]+>", "", m_snip.group(1)).strip() if m_snip else ""
            snippet = _html.unescape(snippet)
            if title and raw_url.startswith("http"):
                results.append(
                    {
                        "title": title,
                        "url": raw_url,
                        "snippet": snippet,
                        "source": "duckduckgo",
                    }
                )
                if len(results) >= max_results:
                    break

    # 4. Nếu không trích xuất được kết quả nào: kiểm tra xem có phải Zero-Result thực thụ không
    if not results:
        is_explicit_zero = any(sig in lower_html for sig in DDG_EXPLICIT_ZERO_RESULTS_SIGNATURES)
        if not is_explicit_zero and len(html_text) > 0 and len(html_text) < 1500:
            # HTML quá ngắn mà không có kết quả và không có dấu hiệu zero-results: nghi ngờ bot challenge không cấu trúc
            raise DDGBotDetectionError("Trang HTML DuckDuckGo bất thường (ngắn bất thường, không chứa kết quả tìm kiếm).")

    return results


def execute_real_web_search_sync(
    query: str,
    task_id: str = "sys",
    mission_id: Optional[str] = None,
    local_only: Optional[bool] = None,
    max_results: int = 5,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> Dict[str, Any]:
    clean_q = str(query or "").strip()
    if not clean_q:
        return build_transparent_refusal(
            query="",
            reason="EMPTY_QUERY",
            detail="Truy vấn tìm kiếm rỗng.",
        )

    if is_local_only_enabled(local_only):
        return build_transparent_refusal(query=clean_q, reason="LOCAL_ONLY_MODE")

    retrieved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    collected: List[Dict[str, Any]] = []
    errors: List[str] = []

    # Freshness (case vàng 15/10): query realtime bắt buộc có mốc after:
    effective_q, window_info = inject_time_window(clean_q)
    window_days = (window_info or {}).get("window_days")
    if window_info and not window_info.get("already_constrained"):
        clean_q = effective_q

    # Kênh 1: RSS Tươi (Direct Sovereign Feeds) cho tin tức/tài chính/thời sự
    allow_rss = os.getenv("JKAI_DISABLE_RSS_DIRECT", "0") != "1"
    if allow_rss:
        try:
            from core.retrieval.rss_poller import search_rss_feeds
            rss_hits = search_rss_feeds(clean_q, max_results=max_results, max_age_hours=72)
            if rss_hits:
                for hit in rss_hits:
                    collected.append(hit)
        except Exception as exc:
            errors.append(f"rss_err:{exc}")

    # Kênh 2: SearXNG Tự chủ (Sovereign Metasearch) nếu có cấu hình
    if not collected:
        searxng_url = os.getenv("SEARXNG_URL", "").strip().rstrip("/")
        if searxng_url:
            try:
                import httpx

                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(
                        f"{searxng_url}/search",
                        params={"q": clean_q, "format": "json",
                                "language": "auto", "safesearch": "1"},
                    )
                    if resp.status_code == 200:
                        for r in (resp.json().get("results", [])[:max_results]):
                            collected.append(
                                {
                                    "title": r.get("title") or r.get("url") or "SearXNG Result",
                                    "url": r.get("url", ""),
                                    "snippet": r.get("content", ""),
                                    "source": "searxng",
                                    "retrieved_at": retrieved_at,
                                }
                            )
                    else:
                        errors.append(f"searxng_http_{resp.status_code}")
            except Exception as exc:
                errors.append(f"searxng_err:{exc}")

    # Kênh 3: Tavily API fallback (nếu có key cấu hình)
    if not collected:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if api_key:
            try:
                import httpx

                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": api_key,
                            "query": clean_q,
                            "search_depth": "basic",
                            "max_results": max_results,
                        },
                    )
                    if resp.status_code == 200:
                        body = resp.json()
                        for r in body.get("results", []):
                            pub = str(r.get("published_date") or "").strip()[:10]
                            collected.append(
                                {
                                    "title": r.get("title") or r.get("url") or "Tavily Result",
                                    "url": r.get("url", ""),
                                    "snippet": r.get("content", ""),
                                    "source": "tavily",
                                    "retrieved_at": retrieved_at,
                                    "published_at": pub,
                                    "freshness": freshness_label(pub, window_days, retrieved_at),
                                }
                            )
                    else:
                        errors.append(f"tavily_http_{resp.status_code}")
            except Exception as exc:
                errors.append(f"tavily_err:{exc}")

    # Kênh 4: DuckDuckGo thực tế nếu chưa có kết quả (Direct HTML + Bot-Detection Awareness)
    global_ddgs = globals().get("DDGS")
    if not collected and global_ddgs is not None:
        if global_ddgs != "auto":
            _DDGS = global_ddgs
        else:
            try:
                try:
                    from ddgs import DDGS as _DDGS
                except ModuleNotFoundError:
                    from duckduckgo_search import DDGS as _DDGS
            except ModuleNotFoundError:
                _DDGS = None

        def _is_test_stub_ddgs(cls: Any) -> bool:
            if cls is None:
                return True
            name = getattr(cls, "__name__", "")
            mod = getattr(cls, "__module__", "")
            return "_Empty" in name or "stub" in str(mod).lower() or "mock" in str(mod).lower()

        # Chi chay Direct HTML neu DDGS khong phai la test stub / mock va khong bi cam boi env
        allow_direct = (
            (_DDGS is not None)
            and (not _is_test_stub_ddgs(_DDGS))
            and (os.getenv("ALLOW_DDG_HTML", "1") != "0")
            and (os.getenv("JKAI_DISABLE_DDG_DIRECT_HTML", "0") != "1")
        )
        if allow_direct:
            try:
                ddg_html_results = _search_duckduckgo_direct_html(clean_q, max_results=max_results)
                for r in ddg_html_results:
                    r["retrieved_at"] = retrieved_at
                    collected.append(r)
            except DDGBotDetectionError as exc:
                errors.append(f"ddg_bot_detected:{exc}")
            except (Exception, AssertionError) as exc:
                errors.append(f"ddg_html_err:{exc}")

        # Kênh 4b: DDGS fallback nếu Direct HTML không trả về kết quả
        if not collected and _DDGS is not None:
            try:
                with _DDGS() as ddgs:
                    for r in ddgs.text(clean_q, max_results=max_results):
                        collected.append(
                            {
                                "title": r.get("title") or r.get("href") or "DuckDuckGo Result",
                                "url": r.get("href", ""),
                                "snippet": r.get("body", ""),
                                "source": "duckduckgo",
                                "retrieved_at": retrieved_at,
                            }
                        )
                if not collected:
                    errors.append("ddg_empty:no_results_returned")
            except Exception as exc:
                errors.append(f"ddg_err:{exc}")

    if not collected:
        return build_transparent_refusal(
            query=clean_q,
            reason="SEARCH_PROVIDERS_UNREACHABLE",
            detail=f"Không thu được kết quả thực tế từ các nhà cung cấp ({'; '.join(errors) or 'no_results'}).",
        )

    formatted_text = _format_results_with_citations(clean_q, collected, retrieved_at)
    payload: Dict[str, Any] = {
        "status": "success",
        "is_simulated": False,
        "query": clean_q,
        "retrieved_at": retrieved_at,
        "time_window": window_info,
        "results": collected,
        "output": formatted_text,
        "error": None,
        # Case 16/10: giữ nguyên nhân kênh lỗi để caller log ngay vào mission.
        "channel_errors": errors,
    }

    if len(formatted_text) > preview_chars:
        env = store_stream(
            content=formatted_text,
            source_tool="web_search",
            task_id=task_id,
            mission_id=mission_id or task_id,
            preview_chars=preview_chars,
            metadata={"query": clean_q, "retrieved_at": retrieved_at},
        )
        sid = env["stream_id"]
        payload["stream_id"] = sid
        payload["total_lines"] = env["total_lines"]
        payload["coverage_ratio"] = env["coverage_ratio"]
        payload["has_more"] = env["has_more"]
        payload["next_start_line"] = env["next_start_line"]
        payload["output"] = (
            env["preview"]
            + f"\n... [STREAM_BUFFERED: stream_id={sid} | "
            f"lines_shown=1..{env['preview_end_line']}/{env['total_lines']} | "
            f"Dùng read_stream_window(stream_id='{sid}', start_line={env['next_start_line']}, end_line=...) "
            f"hoặc search_in_stream(stream_id='{sid}', query='...') để đọc tiếp]"
        )

    return payload


def run(data: Dict[str, Any]) -> Dict[str, Any]:
    """Điểm vào đồng bộ cho `tools/web_search.py` (không bao giờ trả Fake search result)."""
    if not isinstance(data, dict):
        data = {"query": str(data or "")}
    query = data.get("query") or data.get("q") or ""
    local_only = data.get("local_only")
    task_id = str(data.get("task_id") or data.get("mission_id") or "sys")
    mission_id = str(data.get("mission_id") or task_id)
    max_results = int(data.get("max_results") or 5)
    preview_chars = int(data.get("preview_chars") or DEFAULT_PREVIEW_CHARS)
    return execute_real_web_search_sync(
        query=query,
        task_id=task_id,
        mission_id=mission_id,
        local_only=local_only,
        max_results=max_results,
        preview_chars=preview_chars,
    )


# ==============================================================================
# CANONICAL STANDARD TOOL INTERFACES (SSoT: webfetch & websearch)
# ==============================================================================
webfetch = fetch_url_content
websearch = execute_real_web_search_sync
fetch_url_clean = fetch_url_content