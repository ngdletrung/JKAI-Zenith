# ═══════════════════════════════════════════════════════════════════
# [ZENITH FILE DIRECTIVE] JKAI Visual Satellite — Stealth Engine v2.0
# Service: ai-browser
# Role: Neural Eye + CloakBrowser Stealth Integration
# Author: Antigravity Architect | MSI v16.8
# ═══════════════════════════════════════════════════════════════════
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time as _time
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from langchain_ollama import ChatOllama
from pydantic import BaseModel

# ── Project Path ─────────────────────────────────────────────────────
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# ── CloakBrowser local package path ──────────────────────────────────
_cloak_dir = os.path.join(os.path.dirname(__file__), "cloakbrowser")
if _cloak_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_cloak_dir))

from core.utils.engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-browser")

# ═══════════════════════════════════════════════════════════════════
# ⚙️  STEALTH BROWSER FACTORY
# Monkey-patch browser_use.Browser._setup_browser to inject
# CloakBrowser binary + stealth fingerprint args transparently.
# ═══════════════════════════════════════════════════════════════════
def _build_stealth_browser_class(headless: bool = True) -> Any:
    """
    Returns a StealthBrowser subclass that overrides _setup_browser,
    replacing the stock Playwright Chromium with the CloakBrowser
    patched binary and stealth fingerprint arguments.
    """
    from browser_use.browser.service import Browser
    from cloakbrowser.download import ensure_binary
    from cloakbrowser.config import get_default_stealth_args, IGNORE_DEFAULT_ARGS

    class StealthBrowser(Browser):
        """
        [STEALTH-LAYER] Drop-in replacement for browser_use.Browser.
        Routes all Playwright Chromium launches through the CloakBrowser
        binary, enabling full fingerprint-level bot detection bypass
        (Cloudflare Turnstile, reCAPTCHA v3 Enterprise, DataDome, Akamai).
        """

        async def _setup_browser(self, playwright):
            """Override: use CloakBrowser stealth binary instead of stock Chromium."""
            try:
                binary_path = ensure_binary()
                logger.info(f"[STEALTH-INIT] CloakBrowser binary: {binary_path}")

                stealth_args = get_default_stealth_args()
                if headless:
                    stealth_args = [a for a in stealth_args if not a.startswith("--headless")] + ["--headless=new"]

                browser = await playwright.chromium.launch(
                    executable_path=binary_path,
                    headless=headless,
                    args=stealth_args + [
                        "--no-sandbox",
                        "--disable-popup-blocking",
                        "--lang=vi-VN",
                    ],
                    ignore_default_args=IGNORE_DEFAULT_ARGS,
                )
                logger.info("[STEALTH-ACTIVE] Neural Eye now operating via CloakBrowser.")
                return browser
            except Exception as e:
                logger.error(f"[STEALTH-INIT-FAIL] CloakBrowser launch failed: {e}. Falling back to stock Playwright.")
                # Graceful fallback to parent implementation
                return await super()._setup_browser(playwright)

    StealthBrowser.__name__ = "StealthBrowser"
    return StealthBrowser


# ═══════════════════════════════════════════════════════════════════
# 🚀 FASTAPI APP
# ═══════════════════════════════════════════════════════════════════
app = FastAPI(
    title="JKAI Visual Satellite — CloakBrowser Neural Eye",
    version="2.0.0",
    description="Anti-bot stealth web navigation engine for JKAI Zenith OS."
)


# ─── Request Models ──────────────────────────────────────────────────
class BrowseRequest(BaseModel):
    objective: str
    url: str = "https://www.google.com"
    headless: bool = True
    humanize: bool = False  # Reserved: enable Bézier mouse/rhythmic typing in future ver


class VisionRequest(BaseModel):
    image_path: Optional[str] = None
    image_data: Optional[str] = None  # Base64 data
    prompt: str = "Analyze this interface for any UI/UX inconsistencies."


# ─── Health ──────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "Visual Satellite ACTIVE — CloakBrowser Stealth Mode",
        "engine": "CloakBrowser v2",
        "fingerprint": "PATCHED",
    }


# ═══════════════════════════════════════════════════════════════════
# 🕵️  /browse — STEALTH AGENT BROWSE
# Uses browser_use Agent with StealthBrowser for full anti-bot bypass.
# ═══════════════════════════════════════════════════════════════════
@app.post("/browse")
async def browse(req: BrowseRequest):
    logger.info(f"[STEALTH-BROWSE] Objective: {req.objective} | URL: {req.url}")

    try:
        # ── 1. Load LLM config from rule_hardware.md (PLANNER role) ──
        config = engine.get_role_config("PLANNER")
        model_name = config["model"]
        options = config["options"]
        logger.info(f"[BRAIN-SYNC] Model: {model_name} | CTX: {options.get('num_ctx')} | GPU: {options.get('num_gpu')}")

        llm = ChatOllama(
            model=model_name,
            base_url=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
            num_ctx=options.get("num_ctx"),
            temperature=options.get("temperature"),
            num_gpu=options.get("num_gpu"),
            num_thread=options.get("num_thread"),
        )

        # ── 2. GPU reservation via AI Steward ──────────────────────────
        steward_url = os.getenv("STEWARD_URL", "http://ai-control-plane:8000/gpu/request")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(steward_url, json={"service": "ollama", "model": model_name})
        except Exception:
            pass  # Non-critical

        # ── 3. Load domain-specific skills from Neural Eye registry ────
        skills_context = ""
        try:
            registry_path = "/intelligence/skills/neural_eye/registry.json"
            if os.path.exists(registry_path):
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                    for sid, info in registry.get("skills", {}).items():
                        if info["domain"] in req.url:
                            skills_context += f"\n- [{info['domain']}]: {info['capability']}"
            if skills_context:
                logger.info(f"[NEURAL-EYE] Domain skills loaded: {skills_context.strip()}")
        except Exception as e:
            logger.warning(f"[NEURAL-EYE-REGISTRY-ERR] {e}")

        # ── 4. Build full task prompt ────────────────────────────────────
        full_task = f"Go to {req.url} and {req.objective}"
        if skills_context:
            full_task += f"\n\nDomain skill context:\n{skills_context}\nUse these skills if applicable."

        # ── 5. Launch Agent with CloakBrowser Stealth ─────────────────
        from browser_use import Agent
        from browser_use.controller.service import Controller

        StealthBrowser = _build_stealth_browser_class(headless=req.headless)

        controller = Controller(headless=req.headless)
        controller.browser = StealthBrowser(headless=req.headless)

        agent = Agent(
            task=full_task,
            llm=llm,
            controller=controller,
        )

        logger.info("[STEALTH-LAUNCH] Agent ignition via CloakBrowser — bypassing anti-bot layer.")
        result = await agent.run()
        final_result = result.final_result()

        # ── 6. Screenshot proof ──────────────────────────────────────────
        ts = int(_time.time())
        screenshot_dir = os.getenv("WORKSPACE_ROOT", "/workspace") + "/services/mission-control/frontend/public/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = f"{screenshot_dir}/browse_{ts}.png"
        screenshot_filename = None
        try:
            page = await controller.browser.get_current_page()
            await page.screenshot(path=screenshot_path, full_page=False)
            screenshot_filename = f"browse_{ts}.png"
            logger.info(f"[EYE-SNAP] Screenshot captured: {screenshot_filename}")
        except Exception as snap_err:
            logger.warning(f"[EYE-SNAP-WARN] Screenshot failed: {snap_err}")

        # ── 7. Release GPU ────────────────────────────────────────────────
        steward_release_url = os.getenv("STEWARD_RELEASE_URL", "http://ai-control-plane:8000/gpu/release")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(steward_release_url, json={"service": "ollama"})
        except Exception:
            pass

        return {
            "status": "success",
            "engine": "CloakBrowser-Stealth",
            "objective": req.objective,
            "url": req.url,
            "analysis": final_result,
            "screenshot": screenshot_filename,
        }

    except Exception as e:
        logger.error(f"[BROWSE-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 📸  /screenshot — STEALTH SCREENSHOT
# Uses CloakBrowser binary directly for fingerprint-clean snapshots.
# ═══════════════════════════════════════════════════════════════════
@app.post("/screenshot")
async def take_screenshot(req: BrowseRequest):
    """
    [NEURAL-EYE] Captures a full-viewport screenshot using CloakBrowser.
    Eliminates incognito-mode detection penalties (-10% Trust Score on BrowserScan).
    """
    logger.info(f"[EYE-SNAP] CloakBrowser capturing: {req.url}")
    try:
        from cloakbrowser.download import ensure_binary
        from cloakbrowser.config import get_default_stealth_args, IGNORE_DEFAULT_ARGS
        from playwright.async_api import async_playwright

        binary_path = ensure_binary()
        stealth_args = get_default_stealth_args()
        stealth_args = [a for a in stealth_args if not a.startswith("--headless")] + ["--headless=new"]

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                executable_path=binary_path,
                headless=True,
                args=stealth_args + ["--no-sandbox", "--lang=vi-VN"],
                ignore_default_args=IGNORE_DEFAULT_ARGS,
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
            )
            page = await context.new_page()

            await page.goto(req.url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            filename = f"eye_{int(asyncio.get_event_loop().time())}.png"
            output_path = f"/app/screenshots/{filename}"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            await page.screenshot(path=output_path, full_page=False)
            await browser.close()

        logger.info(f"[EYE-SNAP] Captured: {filename}")
        return {
            "status": "captured",
            "engine": "CloakBrowser-Stealth",
            "filename": filename,
            "url": req.url,
            "msg": "Neural Eye has captured the target via stealth channel.",
        }

    except Exception as e:
        logger.error(f"[EYE-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 👁️  /vision — NEURAL VISION ANALYSIS
# ═══════════════════════════════════════════════════════════════════
@app.post("/vision")
async def analyze_vision(req: VisionRequest):
    """
    [NEURAL-VISION] Analyzes an image using the VISION role model (Moondream).
    """
    logger.info(f"[VISION-START] Analyzing image: {req.image_path}")
    try:
        config = engine.get_role_config("VISION")
        model_name = config.get("model", "moondream:latest")

        img_b64 = ""
        if req.image_data:
            img_b64 = req.image_data
            if "," in img_b64:
                img_b64 = img_b64.split(",")[1]
        elif req.image_path:
            image_full_path = f"/app/screenshots/{req.image_path}"
            if not os.path.exists(image_full_path):
                image_full_path = req.image_path
            with open(image_full_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode("utf-8")

        if not img_b64:
            raise Exception("No image data found.")

        ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        payload = {
            "model": model_name,
            "prompt": req.prompt,
            "stream": False,
            "images": [img_b64],
            "options": {
                "num_ctx": config.get("options", {}).get("num_ctx"),
                "num_gpu": config.get("options", {}).get("num_gpu"),
                "num_thread": config.get("options", {}).get("num_thread"),
                "temperature": config.get("options", {}).get("temperature"),
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{ollama_url}/api/generate", json=payload)
            if resp.status_code == 200:
                analysis = resp.json().get("response", "Cannot analyze image content.")
                return {
                    "status": "success",
                    "analysis": analysis,
                    "model": model_name,
                }
            else:
                raise Exception(f"Ollama Vision error: {resp.status_code}")

    except Exception as e:
        logger.error(f"[VISION-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 🛠️  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
