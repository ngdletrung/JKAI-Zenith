import asyncio
import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger("jkai.tools.browser")

_FAST_READER_CACHE = None
_SEMANTIC_ACTUATOR_CACHE = None


def _get_browser_base_url() -> str:
    """Xác định Base URL của ai-browser service."""
    if "BROWSER_SERVICE_URL" in os.environ:
        raw = os.environ["BROWSER_SERVICE_URL"].rstrip("/")
        if raw.endswith("/browse"):
            return raw[:-7]
        return raw

    if os.path.exists("/.dockerenv"):
        return "http://ai-browser:8000"
    return "http://127.0.0.1:8003"


def _get_direct_fast_reader():
    """In-process fallback loader cho FastWebReader."""
    global _FAST_READER_CACHE
    if _FAST_READER_CACHE is not None:
        return _FAST_READER_CACHE
    try:
        reader_path = Path(__file__).resolve().parents[2] / "ai-browser" / "fast_web_reader.py"
        if reader_path.exists():
            spec = importlib.util.spec_from_file_location("fast_web_reader", str(reader_path))
            if spec and spec.loader:
                import sys
                mod = importlib.util.module_from_spec(spec)
                sys.modules["fast_web_reader"] = mod
                spec.loader.exec_module(mod)
                _FAST_READER_CACHE = mod.FastWebReader()
                return _FAST_READER_CACHE
    except Exception as e:
        logger.debug("[BROWSER-DEF] In-process FastWebReader loader warning: %s", e)
    return None


def _get_direct_semantic_actuator():
    """In-process fallback loader cho SemanticBrowserActuator."""
    global _SEMANTIC_ACTUATOR_CACHE
    if _SEMANTIC_ACTUATOR_CACHE is not None:
        return _SEMANTIC_ACTUATOR_CACHE
    try:
        actuator_path = Path(__file__).resolve().parents[2] / "ai-browser" / "semantic_actuator.py"
        if actuator_path.exists():
            spec = importlib.util.spec_from_file_location("semantic_actuator", str(actuator_path))
            if spec and spec.loader:
                import sys
                mod = importlib.util.module_from_spec(spec)
                sys.modules["semantic_actuator"] = mod
                spec.loader.exec_module(mod)
                _SEMANTIC_ACTUATOR_CACHE = mod.SemanticBrowserActuator()
                return _SEMANTIC_ACTUATOR_CACHE
    except Exception as e:
        logger.debug("[BROWSER-DEF] In-process SemanticBrowserActuator loader warning: %s", e)
    return None


def web_read(
    url: str,
    filter_keyword: Optional[str] = None,
    extract_outline: bool = False,
    prefer_llms_txt: bool = True,
    use_envelope: bool = True,
) -> Dict[str, Any]:
    """
    [FAST DOC READER] Đọc nhanh tài liệu web không cần khởi chạy Chromium (< 100ms, 0MB VRAM).
    Có pre-flight HEAD probe, ancestor llms.txt, và đóng gói Untrusted Reference Envelope.
    """
    logger.info("[BROWSER-DEF] web_read: %s | filter=%s", url, filter_keyword)
    base_url = _get_browser_base_url()

    # 1. Thử qua HTTP Service
    try:
        resp = requests.post(
            f"{base_url}/read",
            json={
                "url": url,
                "filter": filter_keyword,
                "outline": extract_outline,
                "prefer_llms_txt": prefer_llms_txt,
                "use_envelope": use_envelope,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as http_err:
        logger.debug("[BROWSER-DEF] HTTP /read unreachable: %s. Thử fallback in-process.", http_err)

    # 2. In-process fallback
    reader = _get_direct_fast_reader()
    if reader:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(
                    reader.read(
                        url=url,
                        filter_keyword=filter_keyword,
                        extract_outline=extract_outline,
                        prefer_llms_txt=prefer_llms_txt,
                        use_envelope=use_envelope,
                    )
                )
                return {
                    "url": getattr(res, "url", url),
                    "content": getattr(res, "content", ""),
                    "content_type": getattr(res, "content_type", "text/plain"),
                    "source_strategy": getattr(res, "source_type", "direct"),
                    "latency_ms": getattr(res, "elapsed_ms", 0.0),
                    "chars": getattr(res, "chars", 0),
                    "lines": getattr(res, "lines", 0),
                    "error": getattr(res, "error", None),
                    "status": "success" if not getattr(res, "error", None) else "error",
                }
            finally:
                loop.close()
        except Exception as direct_err:
            return {"status": "error", "message": f"Direct FastWebReader error: {direct_err}"}

    return {"status": "error", "message": "Không thể kết nối dịch vụ đọc web và in-process reader không khả dụng."}


def browser_observe(url: Optional[str] = None, goal: Optional[str] = None) -> Dict[str, Any]:
    """
    [SEMANTIC A11Y SNAPSHOT] Quét cây Accessibility Tree của DOM thành mã định danh @e1..@eN.
    Bảo toàn 99% context window cho local SLM (3B/4B), tích hợp A11y Quality Gate.
    """
    logger.info("[BROWSER-DEF] browser_observe: url=%s | goal=%s", url, goal)
    base_url = _get_browser_base_url()

    try:
        resp = requests.post(
            f"{base_url}/observe",
            json={"url": url, "goal": goal},
            timeout=45,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"Browser Observe error HTTP {resp.status_code}: {resp.text}"}
    except Exception as http_err:
        logger.debug("[BROWSER-DEF] HTTP /observe unreachable: %s. Thử fallback in-process.", http_err)

    actuator = _get_direct_semantic_actuator()
    if actuator:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                page = loop.run_until_complete(actuator.get_or_create_page(url))
                res = loop.run_until_complete(actuator.observe(page, goal))
                return {
                    "status": "success",
                    "url": res.url,
                    "title": res.title,
                    "element_count": res.element_count,
                    "snapshot": res.snapshot,
                    "quality_gate": res.quality_gate,
                    "scan_latency_ms": res.scan_latency_ms,
                }
            finally:
                loop.close()
        except Exception as direct_err:
            return {"status": "error", "message": f"Direct SemanticBrowserActuator observe error: {direct_err}"}

    return {"status": "error", "message": "Không thể kết nối Browser Actuator và in-process actuator không khả dụng."}


def browser_act(
    element_ref: Optional[str] = None,
    action: str = "click",
    value: Optional[str] = None,
    confirm: bool = False,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    [3-TIER SELF-HEALING ACTION] Tương tác qua ref @eN với cơ chế tự sửa selector 3 tầng:
    Tier 1 (Cache: 0ms) -> Tier 2 (Semantic Fingerprint: <5ms CPU) -> Tier 3 (Local SLM).
    Bảo vệ Credential Shield qua [SECRET_MASKED].
    """
    logger.info("[BROWSER-DEF] browser_act: action=%s ref=%s", action, element_ref)
    base_url = _get_browser_base_url()

    payload = {
        "element_ref": element_ref,
        "action": action,
        "value": value,
        "confirm": confirm,
        "force_refresh": force_refresh,
    }

    try:
        resp = requests.post(f"{base_url}/act", json=payload, timeout=45)
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"Browser Act error HTTP {resp.status_code}: {resp.text}"}
    except Exception as http_err:
        logger.debug("[BROWSER-DEF] HTTP /act unreachable: %s. Thử fallback in-process.", http_err)

    actuator = _get_direct_semantic_actuator()
    if actuator:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from services.ai_browser.semantic_actuator import ActRequest
                page = loop.run_until_complete(actuator.get_or_create_page())
                req_obj = ActRequest(
                    element_ref=element_ref,
                    action=action,
                    value=value,
                    confirm=confirm,
                    force_refresh=force_refresh,
                )
                res = loop.run_until_complete(actuator.act(page, req_obj))
                return {
                    "success": res.success,
                    "action": res.action,
                    "element_ref": res.element_ref,
                    "healing_tier_used": res.healing_tier_used,
                    "message": res.message,
                    "status": "success" if res.success else "error",
                }
            finally:
                loop.close()
        except Exception as direct_err:
            return {"status": "error", "message": f"Direct SemanticBrowserActuator act error: {direct_err}"}

    return {"status": "error", "message": "Không thể kết nối Browser Actuator và in-process actuator không khả dụng."}


def browser_extract(goal: str, schema_definition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    [STRUCTURED EXTRACTION] Trích xuất dữ liệu có cấu trúc tuân thủ schema JSON / Pydantic.
    """
    logger.info("[BROWSER-DEF] browser_extract: goal=%s", goal)
    base_url = _get_browser_base_url()

    try:
        resp = requests.post(
            f"{base_url}/extract",
            json={"goal": goal, "schema_definition": schema_definition},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"Browser Extract error HTTP {resp.status_code}: {resp.text}"}
    except Exception as http_err:
        logger.debug("[BROWSER-DEF] HTTP /extract unreachable: %s", http_err)

    return {"status": "error", "message": f"Không thể kết nối Browser Extract endpoint: {http_err}"}


def browser_action(url: str, objective: str) -> Dict[str, Any]:
    """
    [LEGACY COMPATIBILITY & VISUAL SATELLITE] Tương thích ngược với CloakBrowser visual flow.
    """
    logger.info("[JKAI-BROWSER-DEF] Requesting interaction on: %s | objective: %s", url, objective)
    base_url = _get_browser_base_url()

    try:
        resp = requests.post(
            f"{base_url}/browse",
            json={"url": url, "objective": objective},
            timeout=300,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"Browser Agent Error {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Không thể kết nối tới Browser Agent: {str(e)}"}
