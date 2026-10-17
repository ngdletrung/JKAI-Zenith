# -*- coding: utf-8 -*-
"""
Test Suite: Sovereign Search Cascade
Verifies the 4-tier sovereign search hierarchy:
1. RSS Tươi (Direct Sovereign Feeds)
2. SearXNG (Self-Hosted Sovereign Metasearch)
3. DuckDuckGo Direct (Hardened với Bot-Detection Awareness)
4. Tavily API (Commercial Fallback)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest
import tools.web_search as ws


class TestSovereignSearchCascade:

    def test_cascade_tier_1_rss_hit_takes_precedence(self, monkeypatch):
        """When RSS feed has matching fresh items, it resolves immediately without hitting downstream."""
        monkeypatch.setenv("JKAI_DISABLE_RSS_DIRECT", "0")
        monkeypatch.setenv("SEARXNG_URL", "http://searxng:8080")
        monkeypatch.setenv("TAVILY_API_KEY", "mock_key")

        fake_rss_item = {
            "title": "Giá vàng SJC tăng kỷ lục",
            "url": "https://cafef.vn/gia-vang-tang.chn",
            "snippet": "Vàng SJC lập đỉnh 85 triệu đồng/lượng",
            "source": "rss_direct",
            "published_at": "2026-10-16T12:00:00Z",
            "freshness": "fresh",
            "retrieved_at": "2026-10-16T12:05:00Z",
        }

        with patch("core.retrieval.rss_poller.search_rss_feeds", return_value=[fake_rss_item]):
            # Downstream should not be called
            with patch("httpx.Client") as mock_client:
                res = ws.execute_real_web_search_sync("giá vàng SJC")
                assert res["status"] == "success"
                assert len(res["results"]) == 1
                assert res["results"][0]["source"] == "rss_direct"
                assert res["results"][0]["title"] == "Giá vàng SJC tăng kỷ lục"
                # SearXNG / Tavily http client should NOT have been invoked
                assert not mock_client.called

    def test_cascade_tier_2_searxng_fallback_when_rss_misses(self, monkeypatch):
        """When RSS misses, cascade smoothly falls back to SearXNG."""
        monkeypatch.setenv("JKAI_DISABLE_RSS_DIRECT", "0")
        monkeypatch.setenv("SEARXNG_URL", "http://searxng:8080")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        mock_searx_resp = MagicMock()
        mock_searx_resp.status_code = 200
        mock_searx_resp.json.return_value = {
            "results": [
                {
                    "title": "MikroTik RouterOS 7.16 Released",
                    "url": "https://forum.mikrotik.com/t/7-16",
                    "content": "Release notes for RouterOS version 7.16.",
                }
            ]
        }
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value.get.return_value = mock_searx_resp
        mock_http_client.__exit__.return_value = False

        with patch("core.retrieval.rss_poller.search_rss_feeds", return_value=[]):
            with patch("httpx.Client", return_value=mock_http_client):
                res = ws.execute_real_web_search_sync("MikroTik RouterOS 7.16")
                assert res["status"] == "success"
                assert len(res["results"]) == 1
                assert res["results"][0]["source"] == "searxng"

    def test_cascade_tier_3_ddg_fallback_when_searxng_misses(self, monkeypatch):
        """When RSS and SearXNG miss or unconfigured, cascade falls back to DDG."""
        monkeypatch.setenv("JKAI_DISABLE_RSS_DIRECT", "0")
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("ALLOW_DDG_HTML", "1")
        monkeypatch.setenv("JKAI_DISABLE_DDG_DIRECT_HTML", "0")

        # Mock non-stub DDGS
        class _NonStubDDGS:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def text(self, *a, **k):
                return []

        monkeypatch.setattr(ws, "DDGS", _NonStubDDGS)

        fake_ddg_results = [
            {
                "title": "Linux Kernel 6.12 Release",
                "url": "https://kernel.org/6.12",
                "snippet": "New LTS kernel release",
                "source": "duckduckgo",
            }
        ]

        with patch("core.retrieval.rss_poller.search_rss_feeds", return_value=[]):
            with patch("tools.web_search._search_duckduckgo_direct_html", return_value=fake_ddg_results):
                res = ws.execute_real_web_search_sync("Linux Kernel 6.12")
                assert res["status"] == "success"
                assert len(res["results"]) == 1
                assert res["results"][0]["source"] == "duckduckgo"
