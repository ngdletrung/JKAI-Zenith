# -*- coding: utf-8 -*-
"""
Test Suite: Slice A7.1 — DDG Bot-Detection Awareness & Resilient Attribution
Tests DuckDuckGo direct HTML scraping robustness:
- Explicit detection of HTTP 403 / 429 rate-limiting
- Anti-bot / CAPTCHA / Cloudflare challenge signature detection
- Clean separation between honest zero-results and bot-detection blocks
- Explicit error attribution in execute_real_web_search_sync
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from tools.web_search import (
    _search_duckduckgo_direct_html,
    DDGBotDetectionError,
    execute_real_web_search_sync,
)


class TestDDGBotDetectionAwareness:

    def test_ddg_direct_html_normal_results(self):
        """Verifies normal HTML with valid results is parsed cleanly."""
        sample_html = """
        <html>
        <body>
            <div class="web-result">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fmikrotik.com%2Fdocs">
                    <b>MikroTik</b> Documentation
                </a>
                <a class="result__snippet">Official guide for RouterOS configuration and firewall rules.</a>
            </div>
            <div class="web-result">
                <a class="result__a" href="https://wiki.mikrotik.com/wiki/Manual:IP/Firewall/Filter">
                    Manual:IP/Firewall/Filter - MikroTik Wiki
                </a>
                <a class="result__snippet">Detailed firewall filter documentation for RouterOS.</a>
            </div>
        </body>
        </html>
        """
        mock_fetch = {
            "ok": True,
            "status_code": 200,
            "text": sample_html,
        }

        with patch("core.security.ssrf_resolve_pin_guard.SSRFResolveAndPinGuard.fetch_with_revalidation", return_value=mock_fetch):
            results = _search_duckduckgo_direct_html("mikrotik routeros firewall", max_results=5)
            assert len(results) == 2
            assert results[0]["title"] == "MikroTik Documentation"
            assert results[0]["url"] == "https://mikrotik.com/docs"
            assert "firewall rules" in results[0]["snippet"]
            assert results[1]["url"] == "https://wiki.mikrotik.com/wiki/Manual:IP/Firewall/Filter"

    def test_ddg_direct_html_detects_http_403_and_429(self):
        """Verifies HTTP 403 / 429 status codes raise DDGBotDetectionError."""
        for code in (403, 429):
            mock_fetch = {
                "ok": False,
                "status_code": code,
                "text": "<html><body>Access Denied / Rate Limited</body></html>",
                "error": f"http_{code}",
            }
            with patch("core.security.ssrf_resolve_pin_guard.SSRFResolveAndPinGuard.fetch_with_revalidation", return_value=mock_fetch):
                with pytest.raises(DDGBotDetectionError) as exc_info:
                    _search_duckduckgo_direct_html("some query")
                assert str(code) in str(exc_info.value)

    def test_ddg_direct_html_detects_captcha_and_challenge_signatures(self):
        """Verifies anti-bot challenge signatures in HTTP 200 responses raise DDGBotDetectionError."""
        challenge_payloads = [
            "<html><body><h1>Anomaly Detected</h1><p>Unusual traffic from your IP.</p></body></html>",
            "<html><body>Checking your browser before accessing DuckDuckGo.</body></html>",
            "<html><body><div id='ddg-captcha'>Please complete the security check</div></body></html>",
            "<html><body><form id='challenge-form'>Are you a human?</form></body></html>",
            "<html><body>Bots are not allowed on this service</body></html>",
        ]

        for payload in challenge_payloads:
            mock_fetch = {
                "ok": True,
                "status_code": 200,
                "text": payload,
            }
            with patch("core.security.ssrf_resolve_pin_guard.SSRFResolveAndPinGuard.fetch_with_revalidation", return_value=mock_fetch):
                with pytest.raises(DDGBotDetectionError) as exc_info:
                    _search_duckduckgo_direct_html("some query")
                assert "chống bot" in str(exc_info.value).lower() or "bot" in str(exc_info.value).lower()

    def test_ddg_direct_html_distinguishes_honest_zero_results(self):
        """Verifies that an authentic empty search result does NOT raise bot detection."""
        zero_results_html = """
        <html>
        <body>
            <div class="results">
                <div class="no-results">
                    No results found for <b>xyzabc123nonexistentkeyword999</b>.
                </div>
            </div>
        </body>
        </html>
        """
        mock_fetch = {
            "ok": True,
            "status_code": 200,
            "text": zero_results_html,
        }
        with patch("core.security.ssrf_resolve_pin_guard.SSRFResolveAndPinGuard.fetch_with_revalidation", return_value=mock_fetch):
            results = _search_duckduckgo_direct_html("xyzabc123nonexistentkeyword999")
            assert results == []

    def test_execute_real_web_search_sync_records_bot_detection_telemetry(self, monkeypatch):
        """
        Verifies that when DDG is blocked by bot detection and other providers are unavailable,
        execute_real_web_search_sync transparently records ddg_bot_detected in its refusal details.
        """
        import tools.web_search as ws

        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        monkeypatch.setenv("ALLOW_DDG_HTML", "1")
        monkeypatch.setenv("JKAI_DISABLE_DDG_DIRECT_HTML", "0")
        monkeypatch.setenv("JKAI_DISABLE_RSS_DIRECT", "1")

        # Mock DDGS class to be non-stub so allow_direct triggers
        class _NonStubDDGS:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def text(self, *a, **k):
                return []

        monkeypatch.setattr(ws, "DDGS", _NonStubDDGS)

        challenge_html = "<html><body><h1>Anomaly Detected</h1><p>Our systems detected unusual traffic.</p></body></html>"
        mock_fetch = {
            "ok": True,
            "status_code": 200,
            "text": challenge_html,
        }

        with patch("core.security.ssrf_resolve_pin_guard.SSRFResolveAndPinGuard.fetch_with_revalidation", return_value=mock_fetch):
            res = execute_real_web_search_sync("realtime query", task_id="test_task")
            assert res["status"] == "unavailable"
            assert "ddg_bot_detected" in res["detail"]
            assert "Anomaly Detected" in res["detail"] or "chống bot" in res["detail"]
