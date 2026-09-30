import pytest
import httpx
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BROWSER_HOST_URL = "http://127.0.0.1:8003"

@pytest.mark.asyncio
async def test_ai_browser_health():
    """Verify ai-browser Visual Satellite container is active with CloakBrowser Stealth Mode."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BROWSER_HOST_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "Visual Satellite ACTIVE" in data.get("status", "")
        assert "CloakBrowser" in data.get("engine", "")
        assert data.get("fingerprint") == "PATCHED"

@pytest.mark.asyncio
async def test_ai_browser_crawl_fast_scrape():
    """Verify fast structured scraping via Crawl4AI."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"url": "https://example.com", "extract_markdown": True}
        resp = await client.post(f"{BROWSER_HOST_URL}/crawl", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert data.get("engine") == "Crawl4AI"
        markdown = data.get("markdown", "")
        assert len(markdown) > 100
        assert "example" in markdown.lower() or "documentation" in markdown.lower()

@pytest.mark.asyncio
async def test_ai_browser_stealth_screenshot():
    """Verify stealth full-viewport screenshot using CloakBrowser binary."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"url": "https://example.com", "objective": "Capture test"}
        resp = await client.post(f"{BROWSER_HOST_URL}/screenshot", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "captured"
        assert data.get("engine") == "CloakBrowser-Stealth"
        assert data.get("filename", "").startswith("eye_")

def test_browser_action_tool_definition_routing():
    """Verify browser_action definition cleanly handles requests and network fallbacks."""
    from services.tools.definitions.browser_interact import browser_action
    import requests
    from unittest.mock import patch, MagicMock

    # Verify that browser_action calls the configured service and returns structured output
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success", "engine": "CloakBrowser-V6-Elite", "analysis": "Done"}

    with patch.object(requests, "post", return_value=mock_resp) as mock_post:
        res = browser_action(url="https://example.com", objective="Test routing")
        assert res.get("status") == "success"
        assert res.get("analysis") == "Done"
        mock_post.assert_called_once()
        # Verify it routed to port 8003 or 8000
        called_url = mock_post.call_args[0][0]
        assert "8003" in called_url or "ai-browser:8000" in called_url
