# ═══════════════════════════════════════════════════════════════════
# [ZENITH FILE DIRECTIVE] JKAI Visual Satellite — Stealth Engine v2.0
# Service: ai-browser
# Role: Neural Eye + CloakBrowser Stealth Integration
# Author: Antigravity Architect | MSI v16.8
# ═══════════════════════════════════════════════════════════════════
from __future__ import annotations

import asyncio
import base64
import hashlib
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
try:
    from browser_use import Agent, Browser, BrowserConfig, BrowserContext, BrowserContextConfig
except ImportError:
    from browser_use import Agent
    try:
        from browser_use.browser.browser import Browser, BrowserConfig
    except (ImportError, ModuleNotFoundError):
        from browser_use.browser import Browser, BrowserConfig
    
    try:
        from browser_use.browser.context import BrowserContext, BrowserContextConfig
    except (ImportError, ModuleNotFoundError):
        from browser_use.context import BrowserContext, BrowserContextConfig
from browser_use.controller.service import Controller

# ── Project Path ─────────────────────────────────────────────────────
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# ── CloakBrowser local package path ──────────────────────────────────
_cloak_dir = os.path.join(os.path.dirname(__file__), "cloakbrowser")
if _cloak_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_cloak_dir))

from core.utils.engine import engine
from tools.web_search import validate_egress_url_ssrf_safe

# ── Semantic Actuator & Fast Web Reader Modules ──
try:
    from fast_web_reader import FastWebReader, FastReadResult
    from semantic_actuator import (
        SemanticBrowserActuator,
        ActRequest,
        ActResponse,
        ObserveResponse,
        ExtractRequest,
        ExtractResponse,
        validate_cdp_loopback_target,
    )
except ImportError:
    from services.ai_browser.fast_web_reader import FastWebReader, FastReadResult
    from services.ai_browser.semantic_actuator import (
        SemanticBrowserActuator,
        ActRequest,
        ActResponse,
        ObserveResponse,
        ExtractRequest,
        ExtractResponse,
        validate_cdp_loopback_target,
    )

fast_reader = FastWebReader()
semantic_actuator = SemanticBrowserActuator()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-browser")

# ═══════════════════════════════════════════════════════════════════
# ⚙️  STEALTH BROWSER FACTORY
# Monkey-patch browser_use.Browser._setup_browser to inject
# CloakBrowser binary + stealth fingerprint args transparently.
# ═══════════════════════════════════════════════════════════════════
def get_stealth_browser(headless: bool = True) -> Browser:
    """
    [STEALTH-FACTORY] Returns a Browser instance configured with CloakBrowser
    stealth fingerprinting and anti-bot bypass logic.
    """
    from cloakbrowser.download import ensure_binary
    from cloakbrowser.config import get_default_stealth_args, IGNORE_DEFAULT_ARGS

    binary_path = ensure_binary()
    logger.info(f"[STEALTH-INIT] CloakBrowser binary: {binary_path}")

    stealth_args = get_default_stealth_args()
    if headless:
        stealth_args = [a for a in stealth_args if not a.startswith("--headless")] + ["--headless=new"]

    # Integrate with V6 BrowserConfig
    config = BrowserConfig(
        headless=headless,
        disable_security=True,
        extra_chromium_args=stealth_args + [
            "--no-sandbox",
            "--disable-popup-blocking",
            "--lang=vi-VN",
        ],
        chrome_instance_path=binary_path # browser-use 0.1.30+ uses this for custom binary
    )
    
    return Browser(config=config)


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
    objective: Optional[str] = "Quan sát trực quan và chụp màn hình trang web"
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
    ssrf_check = validate_egress_url_ssrf_safe(req.url)
    if not ssrf_check.get("allowed"):
        logger.warning(f"❌ [SSRF-BLOCKED] /browse rejected URL: {req.url}")
        raise HTTPException(status_code=403, detail=ssrf_check.get("msg", "SSRF blocked"))

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

        # ── 5. Launch Agent with CloakBrowser Stealth & Vision ─────────
        browser = get_stealth_browser(headless=req.headless)
        
        # Configure context for V6 standard
        context_config = BrowserContextConfig(
            browser_window_size={'width': 1920, 'height': 1080},
            locale='vi-VN',
            highlight_elements=True
        )
        
        # New V6 Multimodal Controller
        controller = Controller()

        agent = Agent(
            task=full_task,
            llm=llm,
            browser=browser,
            use_vision=True, # [V6-ENABLE]: Native Multimodal Reasoning
            controller=controller
        )

        logger.info("[STEALTH-LAUNCH] Agent ignition via CloakBrowser V6 — Multimodal Vision ACTIVE.")
        history = await agent.run()
        final_result = history.final_result()

        # ── 6. Screenshot proof (Improved for V6) ──────────────────────────
        ts = int(_time.time())
        screenshot_dir = os.getenv("WORKSPACE_ROOT", "/workspace") + "/services/mission-control/frontend/public/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_filename = f"browse_{ts}.png"
        screenshot_path = f"{screenshot_dir}/{screenshot_filename}"
        
        screenshot_sha256 = None
        dom_path = None
        dom_sha256 = None
        captured_at = None
        try:
            async with await browser.new_context() as context:
                page = await context.new_page()
                await page.goto(req.url)
                await page.screenshot(path=screenshot_path, full_page=True)
                dom = await page.content()
            dom_filename = f"browse_{ts}.html"
            dom_path = os.path.join(screenshot_dir, dom_filename)
            with open(dom_path, "w", encoding="utf-8") as dom_file:
                dom_file.write(dom)
            screenshot_sha256 = hashlib.sha256(open(screenshot_path, "rb").read()).hexdigest()
            dom_sha256 = hashlib.sha256(dom.encode("utf-8")).hexdigest()
            captured_at = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
            logger.info(f"[EVIDENCE-BUNDLE] screenshot={screenshot_filename} dom={dom_filename}")
        except Exception as snap_err:
            logger.warning(f"[EYE-SNAP-WARN] Screenshot/evidence failed: {snap_err}")

        # ── 7. Release GPU ────────────────────────────────────────────────
        steward_release_url = os.getenv("STEWARD_RELEASE_URL", "http://ai-control-plane:8000/gpu/release")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(steward_release_url, json={"service": "ollama"})
        except Exception:
            pass

        return {
            "status": "success",
            "engine": "CloakBrowser-V6-Elite",
            "objective": req.objective,
            "url": req.url,
            "analysis": final_result,
            "screenshot": screenshot_filename,
            "screenshot_sha256": screenshot_sha256,
            "dom_path": dom_filename if dom_path else None,
            "dom_sha256": dom_sha256,
            "captured_at": captured_at,
            "evidence_complete": bool(screenshot_sha256 and dom_sha256 and captured_at),
            "multimodal": True
        }

    except Exception as e:
        logger.error(f"[BROWSE-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interact")
async def interact(req: BrowseRequest):
    """
    [COMPAT-ALIAS] Endpoint alias for /browse to satisfy tool definitions.
    """
    return await browse(req)


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
    ssrf_check = validate_egress_url_ssrf_safe(req.url)
    if not ssrf_check.get("allowed"):
        logger.warning(f"❌ [SSRF-BLOCKED] /screenshot rejected URL: {req.url}")
        raise HTTPException(status_code=403, detail=ssrf_check.get("msg", "SSRF blocked"))

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

            try:
                await page.goto(req.url, wait_until="domcontentloaded", timeout=15000)
            except Exception as nav_e:
                logger.warning(f"[EYE-WARN] Navigation timeout: {nav_e}. Proceeding with screenshot...")
            await asyncio.sleep(2)

            # 📜 [PRE-SCROLL-HYDRATION]: Cuộn mồi để kích hoạt toàn bộ ảnh lười (lazy-load)
            try:
                await page.evaluate("""async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 500;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= Math.min(scrollHeight, 10000)) {
                                clearInterval(timer);
                                window.scrollTo(0, 0);
                                resolve();
                            }
                        }, 40);
                    });
                }""")
                await asyncio.sleep(1)
            except Exception as scroll_e:
                logger.debug(f"[SCROLL-HYDRATE-WARN] {scroll_e}")

            filename = f"eye_{int(asyncio.get_event_loop().time())}.png"
            output_path = f"/app/screenshots/{filename}"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 📸 [FULL-PAGE-CAPTURE]: Chụp trọn vẹn toàn bộ chiều dài trang web
            await page.screenshot(path=output_path, full_page=True, timeout=20000)
            await browser.close()

            # Copy to workspace and storage for direct Explorer visibility
            import shutil
            for shared_dir in ["/workspace", "/storage", "/workspace/outputs"]:
                try:
                    if os.path.exists(shared_dir):
                        shutil.copy2(output_path, os.path.join(shared_dir, filename))
                except Exception as cp_err:
                    logger.debug(f"[EYE-COPY-WARN] Could not copy to {shared_dir}: {cp_err}")

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
# 🕷️  /crawl — CRAWL4AI DEEP TEXT EXTRACTOR
# Uses Crawl4AI for extremely fast, structured markdown scraping thieu Master.
# ═══════════════════════════════════════════════════════════════════
class CrawlRequest(BaseModel):
    url: str
    extract_markdown: bool = True
    word_count_threshold: int = 10


def _check_browser_allowlist(url: str) -> Optional[str]:
    """Domain allowlist cho ai-browser (BROWSER_ALLOWED_DOMAINS, rỗng = cho phép hết + warn)."""
    allow = [d.strip().lower() for d in os.getenv("BROWSER_ALLOWED_DOMAINS", "").split(",") if d.strip()]
    if not allow:
        return None
    try:
        from urllib.parse import urlparse as _up
        host = (_up(url).hostname or "").lower()
    except Exception:
        return "URL không hợp lệ"
    if not any(host == d or host.endswith("." + d) for d in allow):
        return f"Domain '{host}' không thuộc allowlist ai-browser"
    return None


@app.post("/crawl")
async def crawl(req: CrawlRequest):
    """
    [CRAWL4AI-SATELLITE] Performs fast, clean web scraping using Crawl4AI thieu Master.
    Falls back gracefully to Playwright text extraction if crawl4ai is not installed.
    """
    logger.info(f"[CRAWL4AI] Crawling URL: {req.url}")
    ssrf_check = validate_egress_url_ssrf_safe(req.url)
    if not ssrf_check.get("allowed"):
        logger.warning(f"❌ [SSRF-BLOCKED] /crawl rejected URL: {req.url}")
        raise HTTPException(status_code=403, detail=ssrf_check.get("msg", "SSRF blocked"))
    allow_err = _check_browser_allowlist(req.url)
    if allow_err:
        logger.warning(f"❌ [ALLOWLIST-BLOCKED] /crawl rejected URL: {req.url}")
        raise HTTPException(status_code=403, detail=allow_err)

    import hashlib as _hashlib
    try:
        from tools.web_search import extract_published_at as _extract_date
    except Exception:
        _extract_date = lambda html, url: ""  # noqa: E731

    def _snapshot(md_content: str, engine_name: str, extra: Optional[dict] = None):
        body = {
            "status": "success",
            "engine": engine_name,
            "url": req.url,
            "markdown": md_content,
            "sha256": _hashlib.sha256(md_content.encode("utf-8")).hexdigest(),
            "chars": len(md_content),
            "attribution": "This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).",
        }
        if extra:
            body.update(extra)
        return body

    try:
        try:
            # Attempt to import and use Crawl4AI (tolerant buddy 0.4.x ↔ 0.9.x API)
            from crawl4ai import AsyncWebCrawler
            try:
                from crawl4ai import CrawlerRunConfig, CacheMode
                config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    word_count_threshold=req.word_count_threshold
                )
                _run_kwargs = {"config": config}
            except Exception:
                _run_kwargs = {}

            logger.info("[CRAWL4AI] Initializing AsyncWebCrawler thieu Master...")
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=req.url, **_run_kwargs)

                # Retrieve structured markdown (markdown_v2 may not exist on all versions)
                md_content = getattr(result, "markdown", "") or ""
                _md2 = getattr(result, "markdown_v2", None)
                if _md2 and getattr(_md2, "raw_markdown", None):
                    md_content = _md2.raw_markdown

                logger.info(f"[CRAWL4AI] Scraped {len(md_content)} characters thieu Master.")
                return _snapshot(md_content, "Crawl4AI", {
                    "text": (getattr(result, "extracted_content", "") or md_content[:2000]),
                    "published_at": _extract_date(md_content, req.url),
                })
        except ImportError:
            # Graceful fallback using Playwright
            logger.warning("[CRAWL4AI] Crawl4AI not installed. Falling back to Playwright...")
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(req.url, wait_until="networkidle", timeout=30000)

                # Simple markdown converter
                title = await page.title()
                body_text = await page.locator("body").inner_text()

                # Format a clean basic markdown representation
                md_content = f"# {title}\n\n{body_text}"
                await browser.close()

                logger.info(f"[PLAYWRIGHT-FALLBACK] Scraped {len(md_content)} characters thieu Master.")
                return _snapshot(md_content, "Playwright Fallback", {
                    "text": body_text[:2000],
                })
    except Exception as e:
        logger.error(f"[CRAWL-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# ⚡  /read — FAST HEADLESS DOCUMENT & WEB READER
# Ultra-fast doc extraction without Chromium (< 100ms, zero GPU/VRAM).
# ═══════════════════════════════════════════════════════════════════
class ReadRequest(BaseModel):
    url: str
    filter: Optional[str] = None
    outline: bool = False
    prefer_llms_txt: bool = True
    use_envelope: bool = True


@app.post("/read")
async def read_headless_doc(req: ReadRequest):
    """
    [FAST-WEB-READER] High-speed headless document reader (< 100ms, zero browser).
    Pre-flight probes, checks ancestor llms.txt, and frames in untrusted reference envelopes.
    """
    res = await fast_reader.read(
        url=req.url,
        filter_keyword=req.filter,
        extract_outline=req.outline,
        prefer_llms_txt=req.prefer_llms_txt,
        use_envelope=req.use_envelope,
    )
    return res


# ═══════════════════════════════════════════════════════════════════
# 🔍  /observe — SEMANTIC A11Y SNAPSHOT & QUALITY GATE
# Maps interactive DOM to @e1..@eN references (cuts tokens by 85%).
# ═══════════════════════════════════════════════════════════════════
class ObserveReq(BaseModel):
    url: Optional[str] = None
    goal: Optional[str] = None


@app.post("/observe")
async def observe_a11y_tree(req: ObserveReq):
    """
    [SEMANTIC-OBSERVE] Scans DOM Accessibility Tree into @e1..@eN references.
    Includes A11y Quality Gate (Shadow DOM & Canvas detection).
    """
    if req.url:
        ssrf = validate_egress_url_ssrf_safe(req.url)
        if not ssrf.get("allowed"):
            raise HTTPException(status_code=403, detail=ssrf.get("msg", "SSRF blocked"))
    try:
        page = await semantic_actuator.get_or_create_page(req.url)
        return await semantic_actuator.observe(page, req.goal)
    except Exception as e:
        logger.error(f"[OBSERVE-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 🦾  /act — 3-TIER SELF-HEALING ACTION & CREDENTIAL SHIELD
# Interacts via @eN ref or selector with Cache -> Semantic -> LLM recovery.
# ═══════════════════════════════════════════════════════════════════
@app.post("/act")
async def act_element_semantic(req: ActRequest):
    """
    [SEMANTIC-ACT] 3-Tier Self-Healing interaction (Cache -> Semantic -> LLM).
    Includes credential masking and fresh snapshot invalidation.
    """
    try:
        page = await semantic_actuator.get_or_create_page()
        return await semantic_actuator.act(page, req)
    except Exception as e:
        logger.error(f"[ACT-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 📊  /extract — SCHEMA-VALIDATED STRUCTURED EXTRACTION
# ═══════════════════════════════════════════════════════════════════
@app.post("/extract")
async def extract_structured_data(req: ExtractRequest):
    """
    [SEMANTIC-EXTRACT] Schema-validated structured extraction using Pydantic / JSON schema.
    """
    try:
        page = await semantic_actuator.get_or_create_page()
        return await semantic_actuator.extract(page, req.goal, req.schema_definition)
    except Exception as e:
        logger.error(f"[EXTRACT-ERR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# 🛑  /session/close — CLEAN SESSION TERMINATION
# ═══════════════════════════════════════════════════════════════════
@app.post("/session/close")
async def close_browser_session():
    """Đóng browser session và giải phóng tài nguyên."""
    await semantic_actuator.close_session()
    return {"status": "closed", "msg": "Session closed cleanly."}


@app.get("/screenshots/{filename}")
async def serve_screenshot(filename: str):
    """Phục vụ trực tiếp ảnh chụp màn hình cho Mission Control và Web UI."""
    from fastapi.responses import FileResponse
    safe_name = os.path.basename(filename)
    path = f"/app/screenshots/{safe_name}"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Screenshot not found")


# ═══════════════════════════════════════════════════════════════════
# 🛠️  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
