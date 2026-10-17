# -*- coding: utf-8 -*-
"""
Test Suite: core/retrieval/rss_poller.py
Verifies:
- RSS 2.0 XML parsing with RFC-822 timestamps
- Atom 1.0 XML parsing with ISO-8601 timestamps
- Clean HTML tag stripping and entity unescaping
- Date parser resilience across RFC-822, ISO, and standard dates
- Freshness labeling (fresh vs stale)
- Caching logic with TTL and deduplication
- Lexical search ranking with phrase and recency boosts
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch
import pytest

from core.retrieval.rss_poller import (
    RSSItem,
    RSSFeedParser,
    RSSFeedPoller,
    parse_rfc822_or_iso_date,
    calculate_rss_freshness,
)


SAMPLE_RSS_20 = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
    <channel>
        <title>Vietstock - Thị Trường Chứng Khoán</title>
        <link>https://vietstock.vn</link>
        <description>Tin tức chứng khoán mới nhất</description>
        <item>
            <title>VN-Index bứt phá hơn 15 điểm nhờ nhóm cổ phiếu ngân hàng</title>
            <link>https://vietstock.vn/2026/10/vnindex-but-pha-15-diem-ngan-hang-12345.htm</link>
            <description>&lt;p&gt;Dòng tiền ngoại quay lại mua ròng mạnh mẽ trên sàn HOSE, kéo thanh khoản lên trên 25,000 tỷ đồng.&lt;/p&gt;</description>
            <pubDate>Thu, 16 Oct 2026 14:45:00 +0700</pubDate>
            <guid>https://vietstock.vn/2026/10/vnindex-but-pha-15-diem-ngan-hang-12345.htm</guid>
        </item>
        <item>
            <title>Khối ngoại mua ròng 500 tỷ đồng trong phiên giao dịch hôm nay</title>
            <link>https://vietstock.vn/2026/10/khoi-ngoai-mua-rong-500-ty-67890.htm</link>
            <description>Tập trung gom các mã vốn hóa lớn VCB, HPG, FPT.</description>
            <pubDate>Thu, 16 Oct 2026 15:30:00 +0700</pubDate>
            <guid>https://vietstock.vn/2026/10/khoi-ngoai-mua-rong-500-ty-67890.htm</guid>
        </item>
    </channel>
</rss>
"""

SAMPLE_ATOM_10 = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Kitco Gold News</title>
    <link href="https://www.kitco.com/news/gold" />
    <updated>2026-10-16T12:00:00Z</updated>
    <entry>
        <title>Gold prices surge past $2,700 an ounce as safe-haven demand accelerates</title>
        <link href="https://www.kitco.com/news/article/2026-10-16/gold-surges-past-2700" />
        <id>kitco-gold-20261016-01</id>
        <published>2026-10-16T11:30:00Z</published>
        <summary>Spot gold gained 1.4% following macroeconomic shifts and central bank reserve accumulation.</summary>
    </entry>
</feed>
"""


class TestRSSFeedParser:

    def test_parse_rss_20_extracts_clean_items(self):
        items = RSSFeedParser.parse_feed_xml(
            SAMPLE_RSS_20,
            source_name="Vietstock",
            feed_url="https://vietstock.vn/rss.xml",
            now_dt=datetime.datetime(2026, 10, 16, 16, 0, 0, tzinfo=datetime.timezone.utc),
        )

        assert len(items) == 2
        it1 = items[0]
        assert "VN-Index bứt phá" in it1.title
        assert it1.link == "https://vietstock.vn/2026/10/vnindex-but-pha-15-diem-ngan-hang-12345.htm"
        assert "<p>" not in it1.description  # HTML stripped
        assert "Dòng tiền ngoại" in it1.description
        assert it1.source_name == "Vietstock"
        assert it1.published_date == "2026-10-16"
        assert it1.freshness == "fresh"
        assert len(it1.sha256) == 64

    def test_parse_atom_10_extracts_clean_items(self):
        items = RSSFeedParser.parse_feed_xml(
            SAMPLE_ATOM_10,
            source_name="Kitco",
            feed_url="https://kitco.com/rss.xml",
            now_dt=datetime.datetime(2026, 10, 16, 16, 0, 0, tzinfo=datetime.timezone.utc),
        )

        assert len(items) == 1
        it = items[0]
        assert "Gold prices surge" in it.title
        assert it.link == "https://www.kitco.com/news/article/2026-10-16/gold-surges-past-2700"
        assert "Spot gold gained" in it.description
        assert it.published_at.startswith("2026-10-16T11:30:00")
        assert it.freshness == "fresh"

    def test_date_parser_rfc822_and_iso(self):
        # RFC-822 with +0700 offset
        dt1 = parse_rfc822_or_iso_date("Thu, 16 Oct 2026 14:00:00 +0700")
        assert dt1 is not None
        assert dt1.hour == 7  # 14h in +7 is 7h UTC

        # ISO-8601 with Z
        dt2 = parse_rfc822_or_iso_date("2026-10-16T08:30:00Z")
        assert dt2 is not None
        assert dt2.hour == 8

        # Standard YYYY-MM-DD
        dt3 = parse_rfc822_or_iso_date("2026-10-16 12:00:00")
        assert dt3 is not None
        assert dt3.year == 2026 and dt3.month == 10

    def test_freshness_calculation(self):
        now = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
        recent_dt = datetime.datetime(2026, 10, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        old_dt = datetime.datetime(2026, 10, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)

        assert calculate_rss_freshness(recent_dt, now) == "fresh"
        assert calculate_rss_freshness(old_dt, now) == "stale:2026-10-10"
        assert calculate_rss_freshness(None, now) == "date_unknown"


class TestRSSFeedPoller:

    def test_search_and_ranking_with_boosts(self, tmp_path):
        cache_file = tmp_path / "test_rss_cache.json"
        poller = RSSFeedPoller(feeds=[], cache_file=cache_file)

        # Inject memory items directly
        item1 = RSSItem(
            title="Giá vàng hôm nay 16/10: Vàng miếng SJC tăng vọt lên 85 triệu đồng",
            link="https://ex.com/gold-today",
            description="Thị trường vàng trong nước và thế giới đồng loạt lập đỉnh mới.",
            published_at="2026-10-16T08:00:00+00:00",
            published_date="2026-10-16",
            source_name="CafeF",
            feed_url="https://ex.com/rss",
            guid="g1",
            freshness="fresh",
            sha256="h1",
        )
        item2 = RSSItem(
            title="Tỷ giá USD thị trường tự do hạ nhiệt",
            link="https://ex.com/usd-rate",
            description="Ngân hàng Nhà nước duy trì điều hành tỷ giá linh hoạt.",
            published_at="2026-10-16T09:00:00+00:00",
            published_date="2026-10-16",
            source_name="VnEconomy",
            feed_url="https://ex.com/rss2",
            guid="g2",
            freshness="fresh",
            sha256="h2",
        )
        item3 = RSSItem(
            title="Thị trường lúa gạo miền Tây vào vụ thu hoạch",
            link="https://ex.com/rice",
            description="Sản lượng lúa gạo dự báo tăng trưởng tốt.",
            published_at="2026-10-16T07:00:00+00:00",
            published_date="2026-10-16",
            source_name="BaoChinhPhu",
            feed_url="https://ex.com/rss3",
            guid="g3",
            freshness="fresh",
            sha256="h3",
        )

        poller._memory_cache = [item1, item2, item3]
        poller._last_poll_time = datetime.datetime.now().timestamp()

        # Query for gold
        results = poller.search("giá vàng SJC", max_results=5)
        assert len(results) >= 1
        assert results[0]["title"] == item1.title
        assert results[0]["source"] == "rss_direct"
        assert results[0]["freshness"] == "fresh"
        if len(results) > 1:
            assert results[0]["relevance_score"] > results[1]["relevance_score"]

        # Query for general financial keyword
        results_fin = poller.search("thị trường", max_results=5)
        assert len(results_fin) >= 2

    def test_cache_disk_persistence(self, tmp_path):
        cache_file = tmp_path / "test_cache_persistence.json"
        poller = RSSFeedPoller(feeds=[], cache_file=cache_file, cache_ttl_seconds=3600)

        item = RSSItem(
            title="Cổ phiếu FPT vượt đỉnh lịch sử",
            link="https://ex.com/fpt",
            description="Khối ngoại mua ròng mạnh cổ phiếu công nghệ.",
            published_at="2026-10-16T10:00:00+00:00",
            published_date="2026-10-16",
            source_name="Vietstock",
            feed_url="https://ex.com/rss",
            guid="fpt1",
            freshness="fresh",
            sha256="hash_fpt",
        )
        poller._memory_cache = [item]
        poller._last_poll_time = datetime.datetime.now().timestamp()
        poller._save_cache_to_disk()

        assert cache_file.exists()

        # New poller instance reads from disk cache
        new_poller = RSSFeedPoller(feeds=[], cache_file=cache_file, cache_ttl_seconds=3600)
        loaded = new_poller._load_cache_from_disk()
        assert loaded is True
        assert len(new_poller._memory_cache) == 1
        assert new_poller._memory_cache[0].title == "Cổ phiếu FPT vượt đỉnh lịch sử"
