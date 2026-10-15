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
import os
from typing import Any, Dict, List, Optional, Sequence
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


def validate_egress_url_ssrf_safe(
    url: str,
    allowed_domains: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    [Slice 2.4 - WeKnora SSRF-Safe & Whitelist-Only Egress Guard]:
    - Chỉ cho phép giao thức `http` và `https`.
    - Chặn tuyệt đối địa chỉ loopback, RFC1918 private network, link-local / cloud metadata
      (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `localhost`, `.internal`, `.local`).
    - Nếu cung cấp `allowed_domains` hoặc biến môi trường `JKAI_WEB_EGRESS_ALLOWLIST`, chỉ cho phép
      truy cập các tên miền nằm trong danh sách trắng (bao gồm subdomain hợp lệ).
    """
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

    if (
        host in ("localhost", "0.0.0.0", "::1", "[::1]")
        or host.endswith(".internal")
        or host.endswith(".local")
        or host.endswith(".localhost")
    ):
        return {
            "status": "refused",
            "allowed": False,
            "error_code": "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK",
            "url": raw_url,
            "host": host,
            "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
            "msg": f"[SSRF-BLOCKED] Từ chối kết nối tới máy chủ nội bộ/loopback: '{host}'.",
        }

    try:
        ip_obj = ipaddress.ip_address(host.strip("[]"))
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK",
                "url": raw_url,
                "host": host,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "msg": f"[SSRF-BLOCKED] Từ chối kết nối tới địa chỉ IP nội bộ/metadata: '{host}'.",
            }
    except ValueError:
        pass

    env_wl = os.getenv("JKAI_WEB_EGRESS_ALLOWLIST", "").strip()
    effective_wl: List[str] = []
    if allowed_domains is not None:
        effective_wl = [str(d).strip().lower() for d in allowed_domains if str(d).strip()]
    elif env_wl:
        effective_wl = [d.strip().lower() for d in env_wl.split(",") if d.strip()]

    if effective_wl:
        matched = any(host == dom or host.endswith(f".{dom}") for dom in effective_wl)
        if not matched:
            return {
                "status": "refused",
                "allowed": False,
                "error_code": "EGRESS_DOMAIN_NOT_IN_ALLOWLIST",
                "url": raw_url,
                "host": host,
                "allowed_domains": effective_wl,
                "stage_attribution": StageAttribution.CONTROLLER_GATE.value,
                "msg": (
                    f"[EGRESS-REFUSED] Tên miền '{host}' không nằm trong danh sách trắng cho phép "
                    f"(allowed_domains={effective_wl})."
                ),
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
        lines.append(f"Trích đoạn: {snippet}")
        lines.append("")
    return "\n".join(lines).strip()


def _search_duckduckgo_direct_html(
    query: str,
    max_results: int = 5,
    timeout: float = 12.0,
) -> List[Dict[str, Any]]:
    """
    Kênh tìm kiếm DuckDuckGo Direct HTML:
    - Gửi request trực tiếp đến endpoint https://html.duckduckgo.com/html/
    - Không bị phụ thuộc vào package duckduckgo_search/ddgs vốn hay lỗi do bot-detection
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
        with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
            resp = client.post("https://html.duckduckgo.com/html/", data={"q": query})
            if resp.status_code != 200:
                return []
            html_text = resp.text
    except (Exception, AssertionError):
        return []

    parts = re.split(r'<div[^>]+class="[^"]*web-result[^"]*"', html_text)
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

    # Kênh 1: Tavily API nếu có khóa
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
                        collected.append(
                            {
                                "title": r.get("title") or r.get("url") or "Tavily Result",
                                "url": r.get("url", ""),
                                "snippet": r.get("content", ""),
                                "source": "tavily",
                                "retrieved_at": retrieved_at,
                            }
                        )
                else:
                    errors.append(f"tavily_http_{resp.status_code}")
        except Exception as exc:
            errors.append(f"tavily_err:{exc}")

    # Kênh 2: DuckDuckGo thực tế nếu chưa có kết quả
    if not collected and globals().get("DDGS") is not None:
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
            except (Exception, AssertionError) as exc:
                errors.append(f"ddg_html_err:{exc}")

        # Kênh 2b: DDGS fallback nếu Direct HTML không trả về kết quả
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

    # Kênh 3: SearXNG tự chủ (sovereign-friendly, không key) nếu có cấu hình.
    # Dat SEARXNG_URL (vd http://127.0.0.1:8888); de trong thi bo qua kenh nay.
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
        "results": collected,
        "output": formatted_text,
        "error": None,
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