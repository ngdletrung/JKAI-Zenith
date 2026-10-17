# -*- coding: utf-8 -*-
"""
core/retrieval/rss_poller.py — Sovereign Real-Time RSS/Atom Feed Ingestion Engine.

Part of JKAI-Zenith Sovereign Information Architecture:
1. Direct, lightweight feed ingestion for core financial and economic sources (Vietstock, CafeF, VnEconomy, Kitco, etc.).
2. High-precision publication timestamping (RFC-822 / ISO-8601) solving the freshness problem at the root.
3. Zero-trust SSRF protection via SSRFResolveAndPinGuard.
4. In-memory and disk caching with deduplication and lexical/BM25 scoring for search cascades.
"""

from __future__ import annotations

import os
import re
import html
import json
import hashlib
import datetime
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence
import xml.etree.ElementTree as ET

# Default Sovereign Financial and Macroeconomic RSS Feeds
DEFAULT_CORE_RSS_FEEDS: List[Dict[str, str]] = [
    {
        "name": "Vietstock - Thị Trường",
        "url": "https://vietstock.vn/rss/thi-truong-chung-khoan.rss",
        "category": "finance_vn",
    },
    {
        "name": "Vietstock - Doanh Nghiệp",
        "url": "https://vietstock.vn/rss/doanh-nghiep.rss",
        "category": "corporate_vn",
    },
    {
        "name": "Vietstock - Tài Chính",
        "url": "https://vietstock.vn/rss/tai-chinh.rss",
        "category": "macro_vn",
    },
    {
        "name": "CafeF - Thị Trường Chứng Khoán",
        "url": "https://cafef.vn/thi-truong-chung-khoan.rss",
        "category": "finance_vn",
    },
    {
        "name": "CafeF - Tài Chính Quốc Tế",
        "url": "https://cafef.vn/tai-chinh-quoc-te.rss",
        "category": "finance_global",
    },
    {
        "name": "CafeF - Bất Động Sản",
        "url": "https://cafef.vn/bat-dong-san.rss",
        "category": "realestate_vn",
    },
    {
        "name": "VnEconomy - Tài Chính",
        "url": "https://vneconomy.vn/tai-chinh.rss",
        "category": "finance_vn",
    },
    {
        "name": "VnEconomy - Chứng Khoán",
        "url": "https://vneconomy.vn/chung-khoan.rss",
        "category": "finance_vn",
    },
    {
        "name": "VnEconomy - Tiêu Điểm",
        "url": "https://vneconomy.vn/tieu-diem.rss",
        "category": "macro_vn",
    },
    {
        "name": "Báo Chính Phủ - Kinh Tế",
        "url": "https://baochinhphu.vn/kinh-te.rss",
        "category": "policy_vn",
    },
    {
        "name": "Kitco News - Gold & Precious Metals",
        "url": "https://www.kitco.com/rss/category/commodities/gold",
        "category": "gold_commodities",
    },
]

CACHE_FILE_DEFAULT = Path("data/cache/rss_feed_cache.json")
DEFAULT_CACHE_TTL_SECONDS = 900  # 15 minutes


@dataclass
class RSSItem:
    title: str
    link: str
    description: str
    published_at: str  # ISO-8601 UTC
    published_date: str  # YYYY-MM-DD
    source_name: str
    feed_url: str
    guid: str
    freshness: str  # "fresh", "stale:YYYY-MM-DD", "date_unknown"
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_html_text(raw_html: str) -> str:
    """Removes HTML tags and unescapes text entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw_html))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_rfc822_or_iso_date(date_str: str) -> Optional[datetime.datetime]:
    """Parses RFC-822 / RFC-2822 or ISO-8601 date string into UTC datetime."""
    if not date_str:
        return None
    raw = str(date_str).strip()
    # 1. Try RFC-822 (e.g. 'Thu, 16 Oct 2026 14:30:00 +0700' or '16 Oct 2026 07:30:00 GMT')
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass

    # 2. Try ISO-8601 (e.g. '2026-10-16T14:30:00Z' or '2026-10-16T14:30:00+07:00')
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass

    # 3. Fallback regex for common format YYYY-MM-DD HH:MM:SS
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?", raw)
    if m:
        try:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            hour = int(m.group(4) or 0)
            minute = int(m.group(5) or 0)
            second = int(m.group(6) or 0)
            return datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)
        except Exception:
            pass

    return None


def calculate_rss_freshness(pub_dt: Optional[datetime.datetime], now_dt: Optional[datetime.datetime] = None) -> str:
    """Calculates freshness label based on age."""
    if not pub_dt:
        return "date_unknown"
    now = now_dt or datetime.datetime.now(datetime.timezone.utc)
    age = now - pub_dt
    pub_date_str = pub_dt.strftime("%Y-%m-%d")
    if age.total_seconds() <= 48 * 3600:
        return "fresh"
    return f"stale:{pub_date_str}"


class RSSFeedParser:
    """Zero-dependency parser for both RSS 2.0 and Atom 1.0 feeds."""

    @classmethod
    def parse_feed_xml(
        cls,
        xml_text: str,
        source_name: str,
        feed_url: str,
        now_dt: Optional[datetime.datetime] = None,
    ) -> List[RSSItem]:
        if not xml_text or not xml_text.strip():
            return []

        try:
            root = ET.fromstring(xml_text.strip())
        except ET.ParseError:
            # Try stripping potential preamble junk
            clean_xml = re.sub(r"^[^<]+", "", xml_text.strip())
            try:
                root = ET.fromstring(clean_xml)
            except Exception:
                return []

        items: List[RSSItem] = []
        now = now_dt or datetime.datetime.now(datetime.timezone.utc)

        # Case A: Standard RSS 2.0 (<rss><channel><item>...)
        channel = root.find("channel")
        rss_items = root.findall(".//item") if channel is None else channel.findall("item")

        if rss_items:
            for it in rss_items:
                title = _clean_html_text(it.findtext("title", ""))
                link = (it.findtext("link", "") or "").strip()
                description = _clean_html_text(it.findtext("description", ""))
                pub_date_raw = it.findtext("pubDate", "") or it.findtext("date", "")
                guid = (it.findtext("guid", "") or link).strip()

                if not title and not description:
                    continue

                pub_dt = parse_rfc822_or_iso_date(pub_date_raw)
                pub_iso = pub_dt.isoformat() if pub_dt else ""
                pub_date_str = pub_dt.strftime("%Y-%m-%d") if pub_dt else ""
                freshness = calculate_rss_freshness(pub_dt, now)

                item_sha = hashlib.sha256(f"{link}|{title}|{pub_iso}".encode("utf-8")).hexdigest()

                items.append(
                    RSSItem(
                        title=title,
                        link=link,
                        description=description,
                        published_at=pub_iso,
                        published_date=pub_date_str,
                        source_name=source_name,
                        feed_url=feed_url,
                        guid=guid,
                        freshness=freshness,
                        sha256=item_sha,
                    )
                )
            return items

        # Case B: Atom 1.0 (<feed><entry>...)
        # Handle XML namespaces in Atom (e.g. {http://www.w3.org/2005/Atom})
        atom_entries = root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry")
        for ent in atom_entries:
            title = _clean_html_text(ent.findtext("{http://www.w3.org/2005/Atom}title", "") or ent.findtext("title", ""))
            
            # Link in Atom is typically an attribute: <link href="..." />
            link = ""
            link_elem = ent.find("{http://www.w3.org/2005/Atom}link")
            if link_elem is None:
                link_elem = ent.find("link")
            if link_elem is not None:
                link = (link_elem.get("href") or link_elem.text or "").strip()

            summary_elem = ent.find("{http://www.w3.org/2005/Atom}summary")
            if summary_elem is None:
                summary_elem = ent.find("summary")
            summary = summary_elem.text if summary_elem is not None else ""

            content_elem = ent.find("{http://www.w3.org/2005/Atom}content")
            if content_elem is None:
                content_elem = ent.find("content")
            content = content_elem.text if content_elem is not None else ""

            description = _clean_html_text(summary or content)

            pub_raw = (
                ent.findtext("{http://www.w3.org/2005/Atom}published", "")
                or ent.findtext("{http://www.w3.org/2005/Atom}updated", "")
                or ent.findtext("published", "")
                or ent.findtext("updated", "")
            )
            guid = (
                ent.findtext("{http://www.w3.org/2005/Atom}id", "")
                or ent.findtext("id", "")
                or link
            ).strip()

            if not title and not description:
                continue

            pub_dt = parse_rfc822_or_iso_date(pub_raw)
            pub_iso = pub_dt.isoformat() if pub_dt else ""
            pub_date_str = pub_dt.strftime("%Y-%m-%d") if pub_dt else ""
            freshness = calculate_rss_freshness(pub_dt, now)

            item_sha = hashlib.sha256(f"{link}|{title}|{pub_iso}".encode("utf-8")).hexdigest()

            items.append(
                RSSItem(
                    title=title,
                    link=link,
                    description=description,
                    published_at=pub_iso,
                    published_date=pub_date_str,
                    source_name=source_name,
                    feed_url=feed_url,
                    guid=guid,
                    freshness=freshness,
                    sha256=item_sha,
                )
            )

        return items


class RSSFeedPoller:
    """
    Periodic poller and search engine for sovereign RSS feeds.
    Safeguards network calls with SSRFResolveAndPinGuard and caches results to disk.
    """

    def __init__(
        self,
        feeds: Optional[List[Dict[str, str]]] = None,
        cache_file: Optional[Path] = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ):
        self.feeds = list(feeds or DEFAULT_CORE_RSS_FEEDS)
        self.cache_file = Path(cache_file or CACHE_FILE_DEFAULT)
        self.cache_ttl_seconds = cache_ttl_seconds
        self._memory_cache: List[RSSItem] = []
        self._last_poll_time: float = 0.0

    def _load_cache_from_disk(self) -> bool:
        if not self.cache_file.exists():
            return False
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            saved_time = float(data.get("saved_at", 0))
            if (datetime.datetime.now().timestamp() - saved_time) > self.cache_ttl_seconds:
                return False  # Expired
            self._last_poll_time = saved_time
            self._memory_cache = [
                RSSItem(**item) for item in data.get("items", [])
            ]
            return len(self._memory_cache) > 0
        except Exception:
            return False

    def _save_cache_to_disk(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": self._last_poll_time,
                "count": len(self._memory_cache),
                "items": [it.to_dict() for it in self._memory_cache],
            }
            tmp_file = self.cache_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp_file.replace(self.cache_file)
        except Exception:
            pass

    def fetch_feed_items(self, feed_cfg: Dict[str, str], timeout: float = 8.0) -> List[RSSItem]:
        url = feed_cfg.get("url", "").strip()
        name = feed_cfg.get("name", "RSS Feed")
        if not url:
            return []

        try:
            from core.security.ssrf_resolve_pin_guard import SSRFResolveAndPinGuard
            headers = {
                "User-Agent": "JKAI-Sovereign-RSSPoller/1.0 (+https://github.com/ngdletrung/JKAI-Zenith)",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }
            fetch_res = SSRFResolveAndPinGuard.fetch_with_revalidation(
                url=url,
                method="GET",
                headers=headers,
                timeout=timeout,
            )
            if not fetch_res.get("ok", False):
                return []
            xml_text = str(fetch_res.get("text") or "")
            return RSSFeedParser.parse_feed_xml(xml_text, source_name=name, feed_url=url)
        except Exception:
            return []

    def poll_all_feeds(self, force: bool = False, max_workers: int = 4) -> List[RSSItem]:
        """Polls all configured feeds, deduplicating items into the sovereign cache."""
        now_ts = datetime.datetime.now().timestamp()
        if not force and self._memory_cache and (now_ts - self._last_poll_time) < self.cache_ttl_seconds:
            return self._memory_cache

        if not force and self._load_cache_from_disk():
            return self._memory_cache

        import concurrent.futures

        collected_items: Dict[str, RSSItem] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_feed = {
                executor.submit(self.fetch_feed_items, feed): feed for feed in self.feeds
            }
            for future in concurrent.futures.as_completed(future_to_feed):
                try:
                    feed_items = future.result()
                    for it in feed_items:
                        # Deduplicate by link or SHA-256
                        key = it.link or it.sha256
                        if key and key not in collected_items:
                            collected_items[key] = it
                except Exception:
                    pass

        # Sort items by publication timestamp descending
        sorted_items = sorted(
            collected_items.values(),
            key=lambda x: x.published_at or "0000-00-00",
            reverse=True,
        )

        self._memory_cache = sorted_items
        self._last_poll_time = now_ts
        self._save_cache_to_disk()
        return self._memory_cache

    def search(
        self,
        query: str,
        max_results: int = 5,
        max_age_hours: int = 72,
    ) -> List[Dict[str, Any]]:
        """
        Searches cached RSS items using lexical and recency scoring.
        Returns result dicts compatible with JKAI search providers.
        """
        clean_q = str(query or "").strip().lower()
        if not clean_q:
            return []

        all_items = self.poll_all_feeds(force=False)
        if not all_items:
            return []

        now = datetime.datetime.now(datetime.timezone.utc)
        q_tokens = [tok for tok in re.findall(r"\w+", clean_q) if len(tok) >= 2]
        if not q_tokens:
            return []

        scored_items: List[tuple[float, RSSItem]] = []
        for it in all_items:
            # Check age limit
            if it.published_at:
                try:
                    pub_dt = datetime.datetime.fromisoformat(it.published_at)
                    age_hours = (now - pub_dt).total_seconds() / 3600.0
                    if age_hours > max_age_hours:
                        continue
                except Exception:
                    pass

            title_lower = it.title.lower()
            desc_lower = it.description.lower()

            # Exact phrase match boost
            score = 0.0
            has_phrase_match = False
            if clean_q in title_lower:
                score += 15.0
                has_phrase_match = True
            elif clean_q in desc_lower:
                score += 8.0
                has_phrase_match = True

            # Token overlap score
            matched_tokens = 0
            tokens_in_title = 0
            for tok in q_tokens:
                if tok in title_lower:
                    score += 4.0
                    matched_tokens += 1
                    tokens_in_title += 1
                elif tok in desc_lower:
                    score += 1.5
                    matched_tokens += 1

            # Match qualification:
            # 1. Exact phrase in title or description
            # 2. For single token: must match title or score >= 4.0
            # 3. For 2 tokens: both tokens must match, or exact phrase
            # 4. For >= 3 tokens: at least 50% of tokens must match AND at least 1 in title (or exact phrase)
            is_strong_match = False
            if has_phrase_match:
                is_strong_match = True
            elif len(q_tokens) == 1:
                is_strong_match = (matched_tokens == 1 and (tokens_in_title >= 1 or score >= 4.0))
            elif len(q_tokens) == 2:
                is_strong_match = (matched_tokens == 2)
            else:
                coverage = matched_tokens / len(q_tokens)
                is_strong_match = (coverage >= 0.5) and (tokens_in_title >= 1)

            if is_strong_match and score >= 6.0:
                # Recency boost (items under 12h get a bonus)
                if it.freshness == "fresh":
                    score += 5.0
                scored_items.append((score, it))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        retrieved_at = now.isoformat()
        results: List[Dict[str, Any]] = []
        for score, it in scored_items[:max_results]:
            snippet = it.description if len(it.description) > 30 else it.title
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."

            results.append(
                {
                    "title": it.title,
                    "url": it.link,
                    "snippet": snippet,
                    "source": "rss_direct",
                    "source_name": it.source_name,
                    "published_at": it.published_at,
                    "freshness": it.freshness,
                    "retrieved_at": retrieved_at,
                    "relevance_score": round(score, 2),
                }
            )

        return results


# Global singleton instance for easy in-process access
_default_poller: Optional[RSSFeedPoller] = None


def get_rss_poller() -> RSSFeedPoller:
    global _default_poller
    if _default_poller is None:
        _default_poller = RSSFeedPoller()
    return _default_poller


def search_rss_feeds(
    query: str,
    max_results: int = 5,
    max_age_hours: int = 72,
) -> List[Dict[str, Any]]:
    """Public helper to search fresh RSS items."""
    poller = get_rss_poller()
    return poller.search(query=query, max_results=max_results, max_age_hours=max_age_hours)
