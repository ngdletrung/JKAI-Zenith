"""
Gọi POST /invalidate_cache trên mọi executor sau khi promote skill/repo.
"""

from __future__ import annotations

import logging
import os
from typing import List, Tuple

import httpx

logger = logging.getLogger("jkai.executor_cache")


def _executor_base_urls() -> List[str]:
    urls: List[str] = []
    try:
        from core.utils.registry import registry

        for key in ("executor", "executor_2"):
            try:
                u = registry.get_service_url(key).rstrip("/")
                if u and u not in urls:
                    urls.append(u)
            except Exception:
                pass
    except Exception:
        pass

    for env_key in ("EXECUTOR_URL", "EXECUTOR_2_URL"):
        u = (os.getenv(env_key) or "").strip().rstrip("/")
        if u and u not in urls:
            urls.append(u)

    extra = os.getenv("EXECUTOR_INVALIDATE_URLS", "")
    for part in extra.split(","):
        u = part.strip().rstrip("/")
        if u and u not in urls:
            urls.append(u)

    return urls


def invalidate_all_executors_sync(timeout: float = 8.0) -> Tuple[bool, str]:
    """Đồng bộ — dùng sau promote từ hàm sync."""
    urls = _executor_base_urls()
    if not urls:
        return False, "Không có URL executor để invalidate."

    ok_n = 0
    parts: List[str] = []
    with httpx.Client(timeout=timeout) as client:
        for base in urls:
            try:
                resp = client.post(f"{base}/invalidate_cache")
                if resp.status_code == 200:
                    ok_n += 1
                    parts.append(f"✅ {base}")
                else:
                    parts.append(f"⚠️ {base} HTTP {resp.status_code}")
            except Exception as e:
                parts.append(f"❌ {base}: {e}")
                logger.warning("invalidate_cache failed for %s: %s", base, e)

    summary = f"Cache executor: {ok_n}/{len(urls)} — " + "; ".join(parts)
    return ok_n > 0, summary


async def invalidate_all_executors(timeout: float = 8.0) -> Tuple[bool, str]:
    urls = _executor_base_urls()
    if not urls:
        return False, "Không có URL executor để invalidate."

    ok_n = 0
    parts: List[str] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for base in urls:
            try:
                resp = await client.post(f"{base}/invalidate_cache")
                if resp.status_code == 200:
                    ok_n += 1
                    parts.append(f"✅ {base}")
                else:
                    parts.append(f"⚠️ {base} HTTP {resp.status_code}")
            except Exception as e:
                parts.append(f"❌ {base}: {e}")
                logger.warning("invalidate_cache failed for %s: %s", base, e)

    summary = f"Cache executor: {ok_n}/{len(urls)} — " + "; ".join(parts)
    return ok_n > 0, summary
