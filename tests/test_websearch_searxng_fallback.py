# -*- coding: utf-8 -*-
"""Web search providers: ddgs-compat import, SearXNG fallback, honest refusal.

Boi canh: DuckDuckGo tra 0 ket qua tu mang nay + khong co TAVILY_API_KEY
-> search luon unavailable. Them kenh SearXNG tu chu (env SEARXNG_URL).
"""

from __future__ import annotations

import json
import os


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"results": []}

    def json(self):
        return self._payload


class _FakeClient:
    response = _FakeResp()

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, params=None, **k):
        assert url.startswith("http://searxng-test:8888/search")
        assert params and params.get("q")
        assert params.get("format") == "json"
        return _FakeClient.response

    def post(self, *a, **k):
        raise AssertionError("tavily must not be called without key")


def _run_search(monkeypatch, query="vnindex tuan qua"):
    import tools.web_search as ws
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SEARXNG_URL", "http://searxng-test:8888")
    monkeypatch.setattr("httpx.Client", _FakeClient)
    # Chan kenh DDG va RSS de test tap trung kenh SearXNG
    monkeypatch.setattr(ws, "DDGS", None, raising=False)
    monkeypatch.setenv("JKAI_DISABLE_RSS_DIRECT", "1")
    return ws.execute_real_web_search_sync(query, task_id="test")


def test_searxng_success_with_citations(monkeypatch):
    _FakeClient.response = _FakeResp(200, {"results": [
        {"title": "VN-Index rises", "url": "https://ex.com/a",
         "content": "VN-Index up 1.2 percent"},
    ]})
    import tools.web_search as ws
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SEARXNG_URL", "http://searxng-test:8888")
    monkeypatch.setattr("httpx.Client", _FakeClient)

    # Buoc DDG ve rong: gia lap DDGS tra rong
    class _EmptyDDG:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, *a, **k):
            return []

    import sys
    fake_mod = type(sys)("ddgs_stub")
    fake_mod.DDGS = _EmptyDDG
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)
    monkeypatch.setitem(sys.modules, "duckduckgo_search", fake_mod)

    res = ws.execute_real_web_search_sync("vnindex", task_id="test")
    assert res["status"] == "success"
    assert res["is_simulated"] is False
    assert res["results"][0]["source"] == "searxng"
    assert "http" in res["output"] and "Truy xuất" in res["output"] or "retriev" in res["output"].lower() or "Truy" in res["output"]


def test_searxng_down_gives_transparent_refusal(monkeypatch):
    _FakeClient.response = _FakeResp(500, {})
    res = _run_search(monkeypatch)
    assert res["status"] == "unavailable"
    assert res["is_simulated"] is False
    assert "searxng_http_500" in res["error"]


def test_no_providers_configured_refuses_honestly(monkeypatch):
    import tools.web_search as ws
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    import sys

    class _EmptyDDG:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, *a, **k):
            return []

    fake_mod = type(sys)("ddgs_stub2")
    fake_mod.DDGS = _EmptyDDG
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)
    monkeypatch.setitem(sys.modules, "duckduckgo_search", fake_mod)
    res = ws.execute_real_web_search_sync("vnindex", task_id="test")
    assert res["status"] == "unavailable"
    assert res["is_simulated"] is False


def test_ddgs_compat_import_order():
    src = open("tools/web_search.py", encoding="utf-8").read()
    assert "from ddgs import DDGS" in src
    for f in ("services/tools/web_search.py",
              "intelligence/skills/RESEARCH/SEARCH_WEB_GLOBAL/logic.py"):
        assert "from ddgs import DDGS" in open(f, encoding="utf-8").read(), f
