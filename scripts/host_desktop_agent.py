# -*- coding: utf-8 -*-
"""
scripts/host_desktop_agent.py
[D3: OUTBOUND-ONLY HOST DESKTOP AGENT]

Consumes read-only desktop requests from Redis Streams
(`jkai:desktop:requests`) and publishes receipts to `jkai:desktop:receipts`.
It never listens on a port: containers cannot reach host mutation surfaces, and
the agent only makes outbound Redis connections.

Scope (D3):
  - `observe`: enumerate visible windows (optionally UIA elements, optionally
    read-only Tesseract OCR behind `JKAI_OCR_ENABLED=1`). Read-only.
  - `act`: policy-validation only. The agent NEVER mutates the OS here; live
    execution stays with the single mutation owner (host_mutation_server, 9996)
    behind Master approval. A live `type_text` request is staged as a PENDING
    record (target hwnd/pid/proc + text digest) that only
    `scripts/master_desktop_approve.py` can sign and execute. Receipts are
    MUTATION_DISABLED / DRY_RUN_VALIDATED / APPROVAL_REQUIRED.

Receipts are appended to a hash-chained JSONL audit file before publication
(Q6). HMAC is attached when JKAI_DESKTOP_AUDIT_SECRET is configured.

Safety:
  - `JKAI_MUTATION_ENABLED` is re-checked here; container claims are not trusted.
  - Duplicate `request_id` values are rejected via PersistentNonceStore, so an
    unacknowledged redelivery cannot execute twice.
  - Unknown schema/kind is rejected with a typed receipt, never ignored silently.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("jkai.host_desktop_agent")

from core.security.desktop_approvals import (  # noqa: E402
    PendingApprovalStore,
    canonical_digest,
    desktop_redis_client,
)

REQUESTS_STREAM = os.getenv("JKAI_DESKTOP_REQUESTS_STREAM", "jkai:desktop:requests")
RECEIPTS_STREAM = os.getenv("JKAI_DESKTOP_RECEIPTS_STREAM", "jkai:desktop:receipts")
GROUP = os.getenv("JKAI_DESKTOP_GROUP", "host-desktop-agent")
SCHEMA_OBSERVE = "jkai.desktop.observe.v1"
SCHEMA_ACT = "jkai.desktop.act.v1"
REQUEST_TTL_SECONDS = 86400.0


def _policy_path() -> Path:
    override = os.getenv("JKAI_DESKTOP_POLICY_PATH", "").strip()
    if override:
        return Path(override)
    return ROOT / "config" / "security" / "desktop_app_allowlist.json"


def _load_policy_module():
    """Reuse the container policy SSoT instead of duplicating validation rules."""
    path = ROOT / "services" / "tools" / "definitions" / "desktop_control.py"
    spec = importlib.util.spec_from_file_location("jkai_desktop_control_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def enumerate_windows() -> list:
    import psutil
    import win32gui
    import win32process

    foreground = win32gui.GetForegroundWindow()
    windows = []

    def visit(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        rect = win32gui.GetWindowRect(hwnd)
        width, height = rect[2] - rect[0], rect[3] - rect[1]
        if not title or width <= 100 or height <= 100:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process_name = psutil.Process(pid).name()
        except Exception:
            process_name = "unknown"
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "process_name": process_name,
            "pid": pid,
            "rect": list(rect),
            "is_foreground": hwnd == foreground,
            "is_minimized": bool(win32gui.IsIconic(hwnd)),
        })
        return True

    win32gui.EnumWindows(visit, None)
    return windows


def inspect_elements(hwnd: int, limit: int = 50) -> Dict[str, Any]:
    from services.ai_desktop import UIATreeInspector

    snapshot = UIATreeInspector(is_live_mode=True).inspect_tree(int(hwnd))
    return {
        "snapshot_hash": snapshot.snapshot_hash,
        "engine": snapshot.engine,
        "elements": [
            {
                "ref": el.ref,
                "name": el.name,
                "control_type": el.control_type,
                "automation_id": el.automation_id,
                "rect": list(el.rect),
                "center": list(el.center),
                "is_enabled": el.is_enabled,
            }
            for el in snapshot.elements[:max(1, min(limit, 200))]
        ],
    }


class DesktopAudit:
    """Append-only hash chain for every published receipt."""

    def __init__(self, path: Optional[Path] = None, secret: str = "") -> None:
        self.path = path or Path(os.getenv(
            "JKAI_DESKTOP_AUDIT_PATH", str(ROOT / "var" / "audit" / "desktop_receipts.jsonl")
        ))
        self.secret = secret.encode("utf-8") if secret else b""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        last = ""
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        if not last:
            return "GENESIS"
        try:
            return json.loads(last).get("receipt_hash", "GENESIS")
        except Exception:
            return "GENESIS"

    def append(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        prev = self._last_hash()
        body = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        receipt_hash = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
        record = {
            "ts": time.time(),
            "request_id": receipt.get("request_id", ""),
            "kind": receipt.get("kind", ""),
            "status": receipt.get("status", ""),
            "receipt": receipt.get("receipt", ""),
            "payload_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "prev_hash": prev,
            "receipt_hash": receipt_hash,
            "hmac": (
                hmac.new(self.secret, receipt_hash.encode("utf-8"), hashlib.sha256).hexdigest()
                if self.secret else None
            ),
        }
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


def _default_audit() -> "DesktopAudit":
    return DesktopAudit(secret=os.getenv("JKAI_DESKTOP_AUDIT_SECRET", "").strip())


class DesktopRequestHandler:
    """Pure request -> receipt logic; no Redis, easy to test."""

    def __init__(self, audit: Optional[DesktopAudit] = None,
                 pending_store: Optional[PendingApprovalStore] = None) -> None:
        self.audit = audit or _default_audit()
        self.pending = pending_store or PendingApprovalStore()
        from scripts.host_mutation_worker import PersistentNonceStore

        self._nonce_store = PersistentNonceStore()

    def _base(self, request: Dict[str, Any], kind: str) -> Dict[str, Any]:
        return {
            "schema": "jkai.desktop.receipt.v1",
            "kind": kind,
            "request_id": str(request.get("request_id", "")),
            "task_id": str(request.get("task_id", "")),
            "source": "redis:host_desktop_agent",
            "ts": time.time(),
        }

    def _finish(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        receipt["audit"] = self.audit.append(receipt)
        return receipt

    def _consume_once(self, request_id: str) -> bool:
        if not request_id:
            return False
        try:
            return bool(self._nonce_store.check_and_use_nonce(
                f"deskreq_{request_id}", scope="desktop_request", ttl_seconds=REQUEST_TTL_SECONDS
            ))
        except Exception as exc:
            logger.warning("[AGENT] nonce check failed closed: %s", exc)
            return False

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            return self._finish({**self._base({}, "unknown"), "status": "rejected",
                                 "error": "REQUEST_INVALID", "executed": False})

        request_id = str(request.get("request_id", "")).strip()
        schema = str(request.get("schema", "")).strip()
        kind = str(request.get("kind", "")).strip().lower()
        if not kind:
            kind = "observe" if schema == SCHEMA_OBSERVE else "act" if schema == SCHEMA_ACT else ""

        base = self._base(request, kind or "unknown")
        if schema not in (SCHEMA_OBSERVE, SCHEMA_ACT) or not request_id:
            return self._finish({**base, "status": "rejected", "error": "SCHEMA_INVALID",
                                 "executed": False, "receipt": "REJECTED_SCHEMA_INVALID"})
        if not self._consume_once(request_id):
            return self._finish({**base, "status": "rejected", "error": "REPLAY_REJECTED",
                                 "executed": False, "receipt": "REPLAY_REJECTED"})

        try:
            if kind == "observe":
                return self._finish(self._observe(request, base))
            if kind == "act":
                return self._finish(self._act(request, base))
        except Exception as exc:
            logger.exception("[AGENT] handler failed: %s", exc)
            return self._finish({**base, "status": "failed", "error": "AGENT_ERROR",
                                 "detail": str(exc), "executed": False,
                                 "receipt": "AGENT_ERROR"})
        return self._finish({**base, "status": "rejected", "error": "KIND_UNSUPPORTED",
                             "executed": False, "receipt": "REJECTED_KIND_UNSUPPORTED"})

    # ---------------------------------------------------------------- observe
    def _observe(self, request: Dict[str, Any], base: Dict[str, Any]) -> Dict[str, Any]:
        app = str(request.get("app", "") or "").strip()
        limit = max(1, min(int(request.get("limit", 50) or 50), 200))
        windows = enumerate_windows()
        if app:
            needle = app.lower()
            windows = [
                w for w in windows
                if needle in str(w.get("process_name", "")).lower() or needle in str(w.get("title", "")).lower()
            ]
        windows.sort(key=lambda w: (not bool(w.get("is_foreground")), str(w.get("title", "")).lower()))
        windows = windows[:limit]

        result: Dict[str, Any] = {
            **base,
            "status": "success",
            "error": None,
            "executed": False,
            "count": len(windows),
            "windows": windows,
            "receipt": "OBSERVE_OK",
            "state": "PRESERVED_UNMODIFIED",
        }
        if bool(request.get("include_elements")) and windows:
            hwnd = windows[0].get("hwnd")
            if hwnd:
                try:
                    snapshot = inspect_elements(int(hwnd), limit)
                    result["elements"] = snapshot["elements"]
                    result["snapshot_hash"] = snapshot["snapshot_hash"]
                    result["elements_source_hwnd"] = int(hwnd)
                except Exception as exc:
                    result["elements_error"] = str(exc)
        if bool(request.get("include_ocr")) and windows:
            result["ocr"] = self._observe_ocr(request, windows[0])
        return result

    def _observe_ocr(self, request: Dict[str, Any], window: Dict[str, Any]) -> Dict[str, Any]:
        """Optional read-only OCR of the first matched window; never mutates."""
        hwnd = window.get("hwnd")
        if os.getenv("JKAI_OCR_ENABLED", "0").strip() != "1":
            return {"status": "DISABLED", "reason": "JKAI_OCR_ENABLED_NOT_SET", "hwnd": hwnd}
        if not hwnd:
            return {"status": "ERROR", "code": "OCR_HWND_INVALID", "detail": "window has no hwnd"}
        try:
            from services.ai_desktop.ocr_observer import OCRObserver, OCRObserverError
        except Exception as exc:
            return {
                "status": "UNAVAILABLE",
                "reason": f"OCR_IMPORT_FAILED: {type(exc).__name__}",
                "hwnd": int(hwnd),
            }

        observer = OCRObserver()
        available, detail = observer.availability()
        if not available:
            return {"status": "UNAVAILABLE", "reason": detail, "hwnd": int(hwnd)}

        language = str(request.get("ocr_language", "eng") or "eng").strip()
        raw_region = request.get("ocr_region")
        region: Optional[Tuple[int, int, int, int]] = None
        if isinstance(raw_region, (list, tuple)) and len(raw_region) == 4:
            region = tuple(raw_region)  # type: ignore[assignment]
        try:
            payload = observer.observe(int(hwnd), language=language, region=region).as_dict()
        except OCRObserverError as exc:
            return {
                "status": "ERROR",
                "code": exc.code,
                "detail": exc.detail,
                "hwnd": int(hwnd),
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "code": "OCR_OBSERVER_ERROR",
                "detail": str(exc),
                "hwnd": int(hwnd),
            }
        payload["status"] = "OK"
        payload["sensitive"] = True
        payload["text_sha256"] = hashlib.sha256(payload["text"].encode("utf-8")).hexdigest()
        return payload

    # -------------------------------------------------------------------- act
    def _act(self, request: Dict[str, Any], base: Dict[str, Any]) -> Dict[str, Any]:
        module = _load_policy_module()
        policy, policy_path, policy_error = module._load_policy()
        if policy is None:
            return {**base, "status": "rejected", "error": "POLICY_UNAVAILABLE",
                    "detail": policy_error, "executed": False,
                    "receipt": "REJECTED_POLICY_UNAVAILABLE"}

        action = str(request.get("action", "")).lower()
        app = str(request.get("app", ""))
        text = str(request.get("text", ""))
        element_ref = str(request.get("element_ref", ""))
        scroll_direction = str(request.get("scroll_direction", "") or "")
        scroll_unit = str(request.get("scroll_unit", "") or "")
        try:
            scroll_steps = int(request.get("scroll_steps", 0) or 0)
        except (TypeError, ValueError):
            scroll_steps = -1
        allowed, _rule, policy_reason = module._check_policy(
            policy, app, action, text, element_ref,
            scroll_direction=scroll_direction, scroll_unit=scroll_unit,
            scroll_steps=scroll_steps)
        if not allowed:
            return {**base, "status": "rejected", "error": policy_reason,
                    "policy_path": str(policy_path), "executed": False,
                    "receipt": f"REJECTED_{policy_reason}"}

        if os.getenv("JKAI_MUTATION_ENABLED", "0").strip() != "1":
            return {**base, "status": "rejected", "error": "MUTATION_DISABLED",
                    "mutation_enabled": False, "policy_path": str(policy_path),
                    "executed": False, "receipt": "MUTATION_DISABLED_DRY_RUN",
                    "state": "PRESERVED_UNMODIFIED"}

        if bool(request.get("dry_run", True)):
            return {**base, "status": "dry_run_validated", "error": None,
                    "mutation_enabled": True, "policy_path": str(policy_path),
                    "executed": False, "receipt": "DRY_RUN_VALIDATED",
                    "state": "PRESERVED_UNMODIFIED"}

        if action not in ("type_text", "click", "scroll"):
            return {**base, "status": "rejected", "error": "LIVE_ACTION_UNSUPPORTED",
                    "detail": "Only type_text, click and scroll have live executors on the 9996 owner.",
                    "executed": False, "receipt": "REJECTED_LIVE_ACTION_UNSUPPORTED"}

        target = self._resolve_target(app)
        if target is None:
            return {**base, "status": "rejected", "error": "TARGET_NOT_FOUND",
                    "detail": f"No visible window matched app '{app}'.",
                    "executed": False, "receipt": "REJECTED_TARGET_NOT_FOUND"}

        approval_record = {
            "request_id": base["request_id"],
            "kind": "act",
            "task_id": base["task_id"],
            "action": action,
            "app": app,
            "element_ref": element_ref,
            "scroll_direction": scroll_direction,
            "scroll_unit": scroll_unit,
            "scroll_steps": scroll_steps,
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "expected_postcondition": str(request.get("expected_postcondition", "")),
            "hwnd": int(target["hwnd"]),
            "pid": int(target.get("pid", 0)),
            "proc_name": str(target.get("process_name", "")),
            "worker": "host_desktop_agent",
            "requested_at": time.time(),
        }
        approval_record["request_digest"] = canonical_digest(approval_record)
        stored = self.pending.put(approval_record)
        return {**base, "status": "approval_required", "error": "APPROVAL_REQUIRED",
                "mutation_enabled": True, "policy_path": str(policy_path),
                "executed": False, "receipt": "APPROVAL_REQUIRED",
                "approval_id": stored["request_id"],
                "request_digest": stored["request_digest"],
                "target": {"hwnd": stored["hwnd"], "pid": stored["pid"],
                           "proc_name": stored["proc_name"]},
                "expires_at": stored["expires_at"],
                "detail": "Awaiting Master-signed Ed25519 approval via scripts/master_desktop_approve.py."}

    @staticmethod
    def _resolve_target(app: str) -> Optional[Dict[str, Any]]:
        needle = (app or "").strip().lower()
        stem = needle[:-4] if needle.endswith(".exe") else needle
        matches = []
        for window in enumerate_windows():
            name = str(window.get("process_name", "")).lower()
            name_stem = name[:-4] if name.endswith(".exe") else name
            if stem and (stem == name_stem or stem in name or needle in str(window.get("title", "")).lower()):
                matches.append(window)
        if not matches:
            return None
        matches.sort(key=lambda w: not bool(w.get("is_foreground")))
        return matches[0]


def _redis_client():
    return desktop_redis_client(role="agent")


def _ensure_group(client) -> None:
    try:
        client.xgroup_create(REQUESTS_STREAM, GROUP, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _acl_startup_guard() -> None:
    """Refuse to serve with a missing/drifted ACL when enforcement is required."""
    required = os.getenv("JKAI_DESKTOP_ACL_REQUIRED", "0").strip() == "1"
    try:
        from scripts.check_redis_acl_loaded import check_acl

        result = check_acl(require_loaded=required, users=["agent"])
    except Exception as exc:
        if required:
            raise SystemExit(f"FAIL_CLOSED: desktop Redis ACL guard failed: {exc}")
        logger.warning("[AGENT] desktop Redis ACL guard unavailable: %s", exc)
        return
    if not result["ok"]:
        detail = json.dumps(result, ensure_ascii=False, default=str)
        if required:
            raise SystemExit(f"FAIL_CLOSED: desktop Redis ACL guard: {detail}")
        logger.warning("[AGENT] desktop Redis ACL not enforced: %s", detail)
        return
    if result["loaded"]:
        logger.info("[AGENT] desktop Redis ACL verified (aclfile=%s)", result["aclfile"])
    else:
        logger.warning("[AGENT] desktop Redis ACL is runtime-only (no aclfile); "
                       "restarting Redis would drop it")


def serve(consumer: Optional[str] = None, block_ms: int = 1000) -> None:
    _acl_startup_guard()
    client = _redis_client()
    _ensure_group(client)
    handler = DesktopRequestHandler()
    consumer_name = consumer or os.getenv("JKAI_DESKTOP_CONSUMER", f"host-{socket.gethostname()}")

    if os.getenv("JKAI_MUTATION_ENABLED", "0").strip() == "1":
        logger.warning("[AGENT] JKAI_MUTATION_ENABLED=1 — live act requests stage PENDING approvals "
                       "for scripts/master_desktop_approve.py; the agent never mutates the OS itself.")
    logger.info("[AGENT] consuming %s as %s (group=%s); receipts -> %s",
                REQUESTS_STREAM, consumer_name, GROUP, RECEIPTS_STREAM)

    while True:
        entries = client.xreadgroup(GROUP, consumer_name, {REQUESTS_STREAM: ">"},
                                    count=10, block=block_ms)
        if not entries:
            continue
        for _stream, messages in entries:
            for message_id, fields in messages:
                try:
                    payload = json.loads(fields.get("payload") or "{}")
                    receipt = handler.handle(payload)
                    client.xadd(RECEIPTS_STREAM, {
                        "request_id": receipt.get("request_id", ""),
                        "kind": receipt.get("kind", ""),
                        "payload": json.dumps(receipt, ensure_ascii=False),
                    })
                except Exception as exc:
                    logger.exception("[AGENT] message %s failed: %s", message_id, exc)
                finally:
                    client.xack(REQUESTS_STREAM, GROUP, message_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    serve()
