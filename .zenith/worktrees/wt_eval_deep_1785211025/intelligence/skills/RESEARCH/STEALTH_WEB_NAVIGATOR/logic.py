"""
# ═══════════════════════════════════════════════════════════════════
# [ZENITH FILE DIRECTIVE] STEALTH_WEB_NAVIGATOR — Logic v1.0
# Skill: STEALTH_WEB_NAVIGATOR | Domain: RESEARCH
# Purpose: Anti-bot stealth browsing + autonomous pathfinding via
#          CloakBrowser + browser_use Agent (Visual Satellite service).
# Author: Antigravity Architect | MSI v16.8
# ═══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import sys
import logging
import httpx
import asyncio

SYS_PATH_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if SYS_PATH_DIR not in sys.path:
    sys.path.append(SYS_PATH_DIR)

from core.utils.engine import engine

log = logging.getLogger("JKAI.StealthNav")

# ── Service endpoint ──────────────────────────────────────────────────
_BROWSER_SVC_URL = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000")
_TIMEOUT = 180.0  # seconds — allow sufficient time for agent to navigate


async def STEALTH_WEB_NAVIGATOR(
    url: str,
    objective: str,
    task_id: str = "sys",
    trace_id: str = "system",
    headless: bool = True,
    humanize: bool = False,
    **kwargs,
) -> dict:
    """
    🕵️ [STEALTH-NAV]: Deploys the CloakBrowser stealth agent against the target URL.

    The agent autonomously navigates the site (tự dò đường): clicking, scrolling,
    form-filling, and data extraction — while the CloakBrowser binary handles
    all fingerprint-level bot detection bypass.

    Args:
        url:        Target URL to navigate.
        objective:  Natural language description of what to extract or accomplish.
        headless:   Run in headless mode (default True).
        humanize:   Enable Bézier mouse + rhythmic typing (reserved for future CloakBrowser ver).

    Returns:
        dict with status, analysis (agent result), and screenshot filename.
    """
    engine.publish_mission_log(
        "STEALTH_NAV",
        f"🕵️ [CLOAK-LAUNCH]: Kích hoạt Đặc Vụ Ẩn Danh → `{url}`\n"
        f"🎯 Nhiệm vụ: {objective}",
        task_id, trace_id,
    )

    payload = {
        "url": url,
        "objective": objective,
        "headless": headless,
        "humanize": humanize,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_BROWSER_SVC_URL}/browse", json=payload)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "success":
            engine.publish_mission_log(
                "STEALTH_NAV",
                f"✅ [CLOAK-SUCCESS]: Đặc vụ hoàn thành nhiệm vụ.\n"
                f"📊 Kết quả: {str(data.get('analysis', ''))[:300]}",
                task_id, trace_id,
            )
        else:
            engine.publish_mission_log(
                "STEALTH_NAV",
                f"⚠️ [CLOAK-PARTIAL]: Agent trả về trạng thái không rõ: {data}",
                task_id, trace_id,
            )

        return data

    except httpx.TimeoutException:
        msg = f"[CLOAK-TIMEOUT]: Đặc vụ vượt quá {_TIMEOUT}s — trang đích có thể đang xử lý."
        log.error(msg)
        engine.publish_mission_log("STEALTH_NAV", f"⏱️ {msg}", task_id, trace_id)
        return {"status": "error", "msg": msg}

    except Exception as e:
        msg = f"[CLOAK-ERR]: {e}"
        log.exception(msg)
        engine.publish_mission_log("STEALTH_NAV", f"❌ {msg}", task_id, trace_id)
        return {"status": "error", "msg": str(e)}


async def stealth_browse(
    url: str,
    objective: str,
    task_id: str = "sys",
    trace_id: str = "system",
    **kwargs,
) -> dict:
    """💎 [ALIAS]: Primary entry point — stealth agent browse."""
    return await STEALTH_WEB_NAVIGATOR(url, objective, task_id, trace_id, **kwargs)


async def stealth_screenshot(
    url: str,
    task_id: str = "sys",
    trace_id: str = "system",
) -> dict:
    """
    📸 [STEALTH-SNAP]: Captures a screenshot of the target URL via CloakBrowser.
    Zero bot-detection penalty — eliminates incognito-mode Trust Score deduction.
    """
    engine.publish_mission_log(
        "STEALTH_NAV",
        f"📸 [CLOAK-SNAP]: Chụp ảnh ẩn danh → `{url}`",
        task_id, trace_id,
    )

    payload = {"url": url, "objective": "screenshot"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{_BROWSER_SVC_URL}/screenshot", json=payload)
            resp.raise_for_status()
            data = resp.json()

        engine.publish_mission_log(
            "STEALTH_NAV",
            f"✅ [SNAP-DONE]: Ảnh đã chụp → `{data.get('filename', 'unknown')}`",
            task_id, trace_id,
        )
        return data

    except Exception as e:
        log.exception(f"[STEALTH-SNAP-ERR] {e}")
        return {"status": "error", "msg": str(e)}
