# -*- coding: utf-8 -*-
"""
tests/live/live_e2e_isolated_desktop.py
[D7/D8/D9' LIVE PILOT: TRUE ISOLATED DESKTOP SINGLE MUTATION OWNER]

Chạy thủ công (không thuộc pytest mặc định):
    python -m tests.live.live_e2e_isolated_desktop --mode dry
    python -m tests.live.live_e2e_isolated_desktop --mode native
    python -m tests.live.live_e2e_isolated_desktop --mode wordpad
    python -m tests.live.live_e2e_isolated_desktop --mode drill
    python -m tests.live.live_e2e_isolated_desktop --mode click
    python -m tests.live.live_e2e_isolated_desktop --mode scroll

Toàn bộ thành phần mutation (host_desktop_agent, host_mutation_server, target
Notepad/WordPad) được khởi chạy BÊN TRONG một Windows Desktop ảo disposable. Không
thành phần nào chạm desktop của Master, và ``JKAI_MUTATION_ENABLED=1`` chỉ tồn
tại trong env của các tiến trình con thuộc desktop cô lập — ``.env`` không đổi.

D7: agent + mutation owner + target cùng desktop cô lập.
D8: observe -> dry-run -> Master approval -> live type_text -> after-state hash
    -> receipt HMAC + hash-chained audit -> DELIVERED_VERIFIED -> plaintext scrubbed.
D9': như D8 nhưng target là WordPad (RICHEDIT50W) — chứng minh policy SSoT +
    resolver text control không bị trói cứng vào Notepad.
D10: đóng sandbox, xác minh mọi PID bị Kernel Job Object tiêu diệt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.security.desktop_approvals import (  # noqa: E402
    APPROVALS_KEY,
    RECEIPTS_STREAM,
    desktop_redis_client,
)
from scripts.master_approval_signer import MasterApprovalSigner  # noqa: E402
from services.ai_desktop import IsolatedDesktopSandbox  # noqa: E402
from tests.sandbox_desktop_helper import run_in_sandbox  # noqa: E402

REQUESTS_STREAM = os.getenv("JKAI_DESKTOP_REQUESTS_STREAM", "jkai:desktop:requests")
TEXT = "JKAI D7D8 isolated desktop verified"
TEXT_WORDPAD = "JKAI D9P WordPad isolated desktop verified"
CLICK_ELEMENT = "Line down"
SCROLL_ELEMENT = "Text Editor"
SCROLL_DIRECTION = "down"
SCROLL_UNIT = "page"
SCROLL_STEPS = 3
SEED_LINES = 300
# wordpad.exe is not on PATH on Windows 10; the binary lives under Program Files.
WORDPAD_EXE = r"C:\Program Files\Windows NT\Accessories\wordpad.exe"
SESSION = f"live_isolated_{uuid.uuid4().hex[:10]}"
ARTIFACT_DIR = ROOT / "tests" / "live" / "artifacts"


# ─────────────────────────── Utilities ────────────────────────────────────────

def find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_json(method: str, base: str, path: str, payload=None, timeout=10):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        base + path, data=body, method=method,
        headers={"Content-Type": "application/json", "Connection": "close"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            return int(exc.code), json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            return int(exc.code), {"error": f"HTTP_{exc.code}"}
    except Exception as exc:
        return 0, {"error": "CONNECTION_ERROR", "detail": str(exc)}


def wait_server(base: str, timeout=20.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        status, health = http_json("GET", base, "/health")
        if status == 200:
            return health
        last = health
        time.sleep(0.2)
    raise RuntimeError(f"MUTATION_SERVER_NOT_READY: {last}")


class StreamDrainer:
    """Đọc stdout của tiến trình sandbox bằng luồng nền để tránh đầy pipe buffer."""

    def __init__(self, stream):
        self.lines = []
        self._stream = stream
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            for line in iter(self._stream.readline, ""):
                if not line:
                    break
                self.lines.append(line)
        except Exception:
            pass

    def text(self) -> str:
        return "".join(self.lines)


def find_desktop_window(sandbox, pid: int, timeout=8.0, prefer_class: str | None = None):
    import ctypes
    from ctypes import wintypes

    import win32gui

    user32 = ctypes.windll.user32
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []
        preferred = []

        def visit(hwnd, _):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid and win32gui.IsWindowVisible(hwnd):
                found.append(hwnd)
                if prefer_class and win32gui.GetClassName(hwnd) == prefer_class:
                    preferred.append(hwnd)
            return True

        try:
            win32gui.EnumDesktopWindows(sandbox.h_desktop, visit, 0)
        except Exception:
            pass
        if preferred:
            return preferred[0]
        if found:
            return found[0]
        time.sleep(0.1)
    return None


def publish_request(client, payload: dict) -> dict:
    client.xadd(REQUESTS_STREAM, {"payload": json.dumps(payload, ensure_ascii=False)})
    return payload


def wait_receipt(client, request_id: str, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            rows = client.xrevrange(RECEIPTS_STREAM, count=200)
        except Exception:
            rows = []
        for _entry_id, fields in rows:
            if str(fields.get("request_id", "")) != request_id:
                continue
            try:
                return json.loads(fields.get("payload") or "{}")
            except Exception:
                continue
        time.sleep(0.15)
    return None


def verify_audit_chain(path: Path, secret: str) -> dict:
    """Xác minh hash-chain (prev_hash) + HMAC của file audit JSONL."""
    import hmac as hmac_lib

    records = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    records.append({"__parse_error__": True})

    chain_ok = True
    prev = "GENESIS"
    hmac_ok = True
    for record in records:
        if record.get("__parse_error__"):
            chain_ok = False
            continue
        if record.get("prev_hash") != prev:
            chain_ok = False
        prev = record.get("receipt_hash", "")
        digest = record.get("hmac")
        if secret:
            expected = hmac_lib.new(secret.encode("utf-8"), str(record.get("receipt_hash", "")).encode("utf-8"), hashlib.sha256).hexdigest()
            if not digest or not hmac_lib.compare_digest(str(digest), expected):
                hmac_ok = False
        elif digest:
            pass
    return {
        "path": str(path),
        "exists": path.exists(),
        "record_count": len(records),
        "chain_ok": chain_ok,
        "hmac_present": all(bool(r.get("hmac")) for r in records) if records else False,
        "hmac_ok": hmac_ok if secret else None,
        "statuses": [r.get("status", "") for r in records],
    }


def write_artifact(evidence: dict) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = evidence.get("run_id", uuid.uuid4().hex[:12])
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = ARTIFACT_DIR / f"isolated_{ts}_{run_id}.json"
    canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False)
    path.write_text(canonical, encoding="utf-8")
    (path.with_suffix(".sha256")).write_text(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest() + "\n", encoding="utf-8"
    )
    return path


# ─────────────────────────── Pilot ────────────────────────────────────────────

def run(mode: str) -> int:
    run_id = uuid.uuid4().hex[:12]
    started = time.time()
    base_port = find_free_port()
    base = f"http://127.0.0.1:{base_port}"
    artifact_dir = ARTIFACT_DIR / f"iso_{run_id}"
    agent_audit = artifact_dir / "desktop_receipts.jsonl"
    approval_audit = artifact_dir / "desktop_approvals.jsonl"

    wordpad_mode = mode == "wordpad"
    target_proc = "wordpad.exe" if wordpad_mode else "notepad.exe"
    target_exe = WORDPAD_EXE if wordpad_mode else "notepad.exe"
    target_stem = "wordpad" if wordpad_mode else "notepad"
    text = TEXT_WORDPAD if wordpad_mode else TEXT

    private_key, public_key = MasterApprovalSigner.generate_keypair()
    tools = desktop_redis_client("tools")
    master = desktop_redis_client("master")

    evidence = {
        "run_id": run_id,
        "mode": mode,
        "git_revision": git_revision(),
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "session_id": SESSION,
        "target_proc": target_proc,
        "env_mutation_enabled_parent": os.getenv("JKAI_MUTATION_ENABLED", "0"),
        "text_length": len(text),
        "steps": {},
        "verdict": "INCOMPLETE",
    }

    sandbox = IsolatedDesktopSandbox(enable_job_object=True)
    drainers = []
    pids = {}
    try:
        sandbox.create()
        evidence["desktop_name"] = sandbox.desktop_name

        target = sandbox.spawn_process([target_exe])
        pids[target_stem] = target.pid
        target_hwnd = find_desktop_window(
            sandbox, target.pid, timeout=15.0,
            prefer_class="WordPadClass" if wordpad_mode else None,
        )
        if not target_hwnd:
            raise RuntimeError(f"{target_proc.upper()}_WINDOW_NOT_FOUND")
        evidence["steps"]["target"] = {"hwnd": int(target_hwnd), "pid": target.pid, "proc": target_proc}

        before = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})
        if mode in ("click", "scroll"):
            # Harness setup only: fill the editor so the scrollbar is live. The
            # mutation under test is the Master-approved click/scroll, never this seed.
            seed = "\r\n".join(f"JKAI line {index:03d}" for index in range(1, SEED_LINES + 1))
            run_in_sandbox(sandbox, {"op": "send_text", "hwnd": before["control_hwnd"], "text": seed})
            before = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})
        before_text = before["text"]
        control_window = run_in_sandbox(sandbox, {"op": "read_window", "hwnd": before["control_hwnd"]})
        control_class = control_window["window"]["class_name"]
        if wordpad_mode:
            assert control_class.lower() == "richedit50w", f"UNEXPECTED_WORDPAD_CONTROL: {control_class}"
        before_capture = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})
        evidence["steps"]["before_state"] = {
            "text_length": len(before_text),
            "text_sha256": sha256_text(before_text),
            "control_hwnd": before["control_hwnd"],
            "control_class": control_class,
            "screenshot": {
                "pixel_hash": before_capture.get("pixel_hash"),
                "dhash": before_capture.get("dhash"),
                "is_live_capture": before_capture.get("is_live_capture"),
            },
        }

        host_env = dict(os.environ)
        host_env.update({
            "PYTHONIOENCODING": "utf-8",
            "JKAI_MUTATION_ENABLED": "1",
            "JKAI_MUTATION_PORT": str(base_port),
            "JKAI_MUTATION_TEST_MODE": "1",
            "JKAI_MASTER_PUBLIC_KEY": public_key,
            "JKAI_MUTATION_SECRET": os.urandom(24).hex(),
            "JKAI_DESKTOP_AUDIT_PATH": str(agent_audit),
            "JKAI_DESKTOP_CONSUMER": f"iso-agent-{run_id}",
            "JKAI_DESKTOP_REQUESTS_STREAM": REQUESTS_STREAM,
            "JKAI_DESKTOP_RECEIPTS_STREAM": RECEIPTS_STREAM,
        })
        host_env.pop("JKAI_MASTER_PRIVATE_KEY", None)

        server = sandbox.spawn_process([sys.executable, "-m", "scripts.host_mutation_server"], env=host_env)
        pids["server"] = server.pid
        drainers.append(StreamDrainer(server.stdout))
        health = wait_server(base)
        evidence["steps"]["server_health"] = {
            "mutation_enabled": bool(health.get("mutation_enabled")),
            "test_mode": bool(health.get("test_mode")),
        }
        if mode != "dry" and not health.get("mutation_enabled"):
            raise RuntimeError("SERVER_NOT_MUTATION_ENABLED")

        agent = sandbox.spawn_process([sys.executable, "-m", "scripts.host_desktop_agent"], env=host_env)
        pids["agent"] = agent.pid
        drainers.append(StreamDrainer(agent.stdout))
        time.sleep(2.0)

        # ── Observe ─────────────────────────────────────────────────────────
        observe_id = uuid.uuid4().hex
        publish_request(tools, {
            "schema": "jkai.desktop.observe.v1", "kind": "observe",
            "request_id": observe_id, "app": target_stem,
        })
        observe = wait_receipt(tools, observe_id) or {}
        names = [str(w.get("process_name", "")).lower() for w in observe.get("windows", [])]
        evidence["steps"]["observe"] = {
            "status": observe.get("status"),
            "count": observe.get("count"),
            f"{target_stem}_visible": any(target_stem in n for n in names),
            "state": observe.get("state"),
            "audit_hmac_present": bool((observe.get("audit") or {}).get("hmac")),
        }
        assert observe.get("status") == "success", observe
        assert any(target_stem in n for n in names), names

        # ── Agent dry-run (policy validated, no pending record) ─────────────
        if mode not in ("click", "scroll"):
            dry_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": dry_id,
                "task_id": f"d8-{run_id}", "action": "type_text", "app": target_proc,
                "text": text, "expected_postcondition": f"expected_text:{text}", "dry_run": True,
            })
            dry = wait_receipt(tools, dry_id) or {}
            evidence["steps"]["dry_run"] = {
                "status": dry.get("status"),
                "receipt": dry.get("receipt"),
                "state": dry.get("state"),
                "executed": dry.get("executed"),
                "audit_hmac_present": bool((dry.get("audit") or {}).get("hmac")),
            }
            assert dry.get("receipt") == "DRY_RUN_VALIDATED", dry
            assert dry.get("state") == "PRESERVED_UNMODIFIED", dry
            assert dry.get("executed") is False, dry

        if mode == "dry":
            evidence["steps"]["containment"] = {"mode": "dry", "pids": dict(pids)}
            evidence["verdict"] = "D7_DRY_PASS"
            return 0

        # ── Master approval CLI (private key process-local) ─────────────────
        approve_env = dict(os.environ)
        approve_env.update({
            "PYTHONIOENCODING": "utf-8",
            "JKAI_MASTER_PRIVATE_KEY": private_key,
            "JKAI_MASTER_PUBLIC_KEY": public_key,
            "JKAI_MUTATION_URL": base,
            "JKAI_DESKTOP_APPROVAL_AUDIT_PATH": str(approval_audit),
        })

        if mode == "click":
            # D11: policy-validated click -> Master approval -> UIA InvokePattern
            # on the leased HWND -> independent scroll observation. UIA
            # ScrollPattern percent is integer-coarse here (a one-line scroll is
            # ~0.38%), so the exact Win32 GetScrollInfo position is the proof.
            scroll_before = run_in_sandbox(sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            uia_before = run_in_sandbox(
                sandbox, {"op": "uia_scroll", "hwnd": target_hwnd, "identifier": "Text Editor"}
            )
            evidence["steps"]["scroll_before"] = {"win32": scroll_before, "uia": uia_before}
            vertical_before = scroll_before.get("vertical") or {}
            assert vertical_before.get("available") is True, scroll_before
            assert int(vertical_before.get("max", 0)) > int(vertical_before.get("page", 0)), scroll_before
            assert uia_before.get("found") and uia_before.get("scroll_supported"), uia_before

            # Negative: a non-allowlisted element is rejected by policy before any
            # lease/approval exists, and must leave the editor untouched.
            negative_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": negative_id,
                "task_id": f"d11-{run_id}", "action": "click", "app": target_proc,
                "element_ref": "Close", "dry_run": False,
            })
            negative = wait_receipt(tools, negative_id) or {}
            scroll_after_negative = run_in_sandbox(
                sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            evidence["steps"]["negative_not_allowlisted"] = {
                "status": negative.get("status"),
                "receipt": negative.get("receipt"),
                "executed": negative.get("executed"),
                "scroll_pos": (scroll_after_negative.get("vertical") or {}).get("pos"),
            }
            assert negative.get("receipt") == "REJECTED_ELEMENT_NOT_ALLOWLISTED", negative
            assert negative.get("executed") is False, negative
            assert (scroll_after_negative.get("vertical") or {}).get("pos") == vertical_before.get("pos"), (
                "REJECTED_CLICK_SCROLLED_EDITOR")

            click_dry_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": click_dry_id,
                "task_id": f"d11-{run_id}", "action": "click", "app": target_proc,
                "element_ref": CLICK_ELEMENT, "dry_run": True,
            })
            click_dry = wait_receipt(tools, click_dry_id) or {}
            evidence["steps"]["click_dry_run"] = {
                "status": click_dry.get("status"),
                "receipt": click_dry.get("receipt"),
                "state": click_dry.get("state"),
                "executed": click_dry.get("executed"),
            }
            assert click_dry.get("receipt") == "DRY_RUN_VALIDATED", click_dry
            assert click_dry.get("state") == "PRESERVED_UNMODIFIED", click_dry
            assert click_dry.get("executed") is False, click_dry

            click_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": click_id,
                "task_id": f"d11-{run_id}", "action": "click", "app": target_proc,
                "element_ref": CLICK_ELEMENT, "dry_run": False,
            })
            staged = wait_receipt(tools, click_id) or {}
            evidence["steps"]["staged"] = {
                "status": staged.get("status"),
                "receipt": staged.get("receipt"),
                "approval_id": staged.get("approval_id"),
                "target": staged.get("target"),
                "element_ref": CLICK_ELEMENT,
            }
            assert staged.get("receipt") == "APPROVAL_REQUIRED", staged
            assert staged.get("approval_id") == click_id, staged

            pending_before = json.loads(master.hget(APPROVALS_KEY, click_id) or "{}")
            evidence["steps"]["pending_before_approval"] = {
                "status": pending_before.get("status"),
                "action": pending_before.get("action"),
                "element_ref": pending_before.get("element_ref"),
                "text_length": len(pending_before.get("text", "")),
                "request_digest_present": bool(pending_before.get("request_digest")),
                "hwnd": pending_before.get("hwnd"),
                "pid": pending_before.get("pid"),
            }
            assert pending_before.get("element_ref") == CLICK_ELEMENT, "PENDING_ELEMENT_REF_MISSING"

            approve = sandbox.spawn_process([
                sys.executable, "-m", "scripts.master_desktop_approve",
                "approve", click_id, "--confirm", "--json",
            ], env=approve_env)
            pids["approve"] = approve.pid
            out, err = approve.communicate(timeout=60)
            evidence["steps"]["approve_exit_code"] = approve.returncode
            try:
                approve_result = json.loads(out)
            except Exception:
                approve_result = {"unparsed_stdout": out, "stderr": err}
            server_receipt = approve_result.get("server_receipt")
            receipt_status = server_receipt.get("status") if isinstance(server_receipt, dict) else server_receipt
            evidence["steps"]["approve"] = {
                "status": approve_result.get("status"),
                "executed": approve_result.get("executed"),
                "server_status": approve_result.get("server_status"),
                "server_receipt_status": receipt_status,
                "server_receipt_receipt": server_receipt.get("receipt") if isinstance(server_receipt, dict) else None,
                "pattern_used": server_receipt.get("pattern_used") if isinstance(server_receipt, dict) else None,
                "invoked": server_receipt.get("invoked") if isinstance(server_receipt, dict) else None,
                "element_name": server_receipt.get("element_name") if isinstance(server_receipt, dict) else None,
                "before_snapshot_hash": server_receipt.get("before_snapshot_hash") if isinstance(server_receipt, dict) else None,
                "after_snapshot_hash": server_receipt.get("after_snapshot_hash") if isinstance(server_receipt, dict) else None,
                "observed_state_changed": server_receipt.get("observed_state_changed") if isinstance(server_receipt, dict) else None,
                "lease_id_present": bool(approve_result.get("lease_id")),
                "worker_generation": approve_result.get("worker_generation"),
                "audit_hmac_present": bool((approve_result.get("audit") or {}).get("hmac")),
            }
            assert approve.returncode == 0, (out, err)
            assert approve_result.get("status") == "APPROVED_EXECUTED", approve_result
            assert approve_result.get("server_status") == "MUTATION_EXECUTED", approve_result
            assert approve_result.get("executed") is True, approve_result
            assert isinstance(server_receipt, dict), approve_result
            assert server_receipt.get("status") == "CLICK_INVOKED", server_receipt
            assert server_receipt.get("receipt") == "UIA_PATTERN_INVOKED", server_receipt
            assert server_receipt.get("invoked") is True, server_receipt
            assert server_receipt.get("pattern_used") == "InvokePattern", server_receipt
            assert server_receipt.get("element_name") == CLICK_ELEMENT, server_receipt

            scroll_after = run_in_sandbox(sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            uia_after = run_in_sandbox(
                sandbox, {"op": "uia_scroll", "hwnd": target_hwnd, "identifier": "Text Editor"}
            )
            after_text = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})["text"]
            after_capture = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})
            pos_before = int((scroll_before.get("vertical") or {}).get("pos", 0))
            pos_after = int((scroll_after.get("vertical") or {}).get("pos", 0))
            evidence["steps"]["scroll_after"] = {"win32": scroll_after, "uia": uia_after}
            evidence["steps"]["after_state"] = {
                "scroll_pos_before": pos_before,
                "scroll_pos_after": pos_after,
                "scroll_advanced": pos_after > pos_before,
                "uia_vertical_percent_before": uia_before.get("vertical_percent"),
                "uia_vertical_percent_after": uia_after.get("vertical_percent"),
                "text_unchanged": after_text == before_text,
                "text_length": len(after_text),
                "text_sha256": sha256_text(after_text),
                "screenshot": {
                    "pixel_changed": after_capture.get("pixel_hash") != before_capture.get("pixel_hash"),
                    "dhash_changed": after_capture.get("dhash") != before_capture.get("dhash"),
                    "is_live_capture": after_capture.get("is_live_capture"),
                },
            }
            assert pos_after > pos_before, evidence["steps"]["after_state"]
            assert after_text == before_text, "CLICK_MUTATED_TEXT_CONTENT"

            pending_after = json.loads(master.hget(APPROVALS_KEY, click_id) or "{}")
            evidence["steps"]["pending_after_approval"] = {
                "status": pending_after.get("status"),
                "text_length": len(pending_after.get("text", "")),
                "text_scrubbed": bool(pending_after.get("text_scrubbed")),
                "executed": bool(pending_after.get("executed")),
            }
            assert pending_after.get("status") == "APPROVED_EXECUTED", pending_after
            assert pending_after.get("text", "") == "", "PLAINTEXT_NOT_SCRUBBED"
            assert pending_after.get("text_scrubbed") is True, pending_after

            audit_secret = os.getenv("JKAI_DESKTOP_AUDIT_SECRET", "").strip()
            agent_chain = verify_audit_chain(agent_audit, audit_secret)
            approval_chain = verify_audit_chain(approval_audit, audit_secret)
            evidence["steps"]["audit"] = {
                "secret_configured": bool(audit_secret),
                "agent": agent_chain,
                "approval": approval_chain,
            }
            assert audit_secret, "JKAI_DESKTOP_AUDIT_SECRET missing: receipts would have hmac=null"
            assert agent_chain["chain_ok"] and agent_chain["hmac_ok"], agent_chain
            assert approval_chain["chain_ok"] and approval_chain["hmac_ok"], approval_chain
            assert agent_chain["hmac_present"] and approval_chain["hmac_present"]

            evidence["steps"]["job_stats"] = sandbox.get_job_stats()
            evidence["verdict"] = "D11_CLICK_PASS"
            return 0

        if mode == "scroll":
            # D12: policy-validated scroll -> Master approval -> UIA ScrollPattern
            # on the leased HWND -> independent Win32 GetScrollInfo observation.
            # UIA percent is coarse, so exact nPos is the proof of the effect.
            scroll_before = run_in_sandbox(sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            uia_before = run_in_sandbox(
                sandbox, {"op": "uia_scroll", "hwnd": target_hwnd, "identifier": SCROLL_ELEMENT}
            )
            evidence["steps"]["scroll_before"] = {"win32": scroll_before, "uia": uia_before}
            vertical_before = scroll_before.get("vertical") or {}
            assert vertical_before.get("available") is True, scroll_before
            assert int(vertical_before.get("max", 0)) > int(vertical_before.get("page", 0)), scroll_before
            assert uia_before.get("found") and uia_before.get("scroll_supported"), uia_before
            assert uia_before.get("vertically_scrollable"), uia_before

            # Negative 1: non-allowlisted element is rejected before any lease.
            negative_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": negative_id,
                "task_id": f"d12-{run_id}", "action": "scroll", "app": target_proc,
                "element_ref": "Close", "scroll_direction": SCROLL_DIRECTION,
                "scroll_unit": SCROLL_UNIT, "scroll_steps": SCROLL_STEPS, "dry_run": False,
            })
            negative = wait_receipt(tools, negative_id) or {}
            # Negative 2: out-of-range steps fails policy for an allowlisted element.
            bad_steps_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": bad_steps_id,
                "task_id": f"d12-{run_id}", "action": "scroll", "app": target_proc,
                "element_ref": SCROLL_ELEMENT, "scroll_direction": SCROLL_DIRECTION,
                "scroll_unit": SCROLL_UNIT, "scroll_steps": 6, "dry_run": False,
            })
            bad_steps = wait_receipt(tools, bad_steps_id) or {}
            scroll_after_negative = run_in_sandbox(
                sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            evidence["steps"]["negative_not_allowlisted"] = {
                "status": negative.get("status"),
                "receipt": negative.get("receipt"),
                "executed": negative.get("executed"),
                "scroll_pos": (scroll_after_negative.get("vertical") or {}).get("pos"),
            }
            evidence["steps"]["negative_bad_steps"] = {
                "status": bad_steps.get("status"),
                "receipt": bad_steps.get("receipt"),
                "executed": bad_steps.get("executed"),
            }
            assert negative.get("receipt") == "REJECTED_ELEMENT_NOT_ALLOWLISTED", negative
            assert negative.get("executed") is False, negative
            assert bad_steps.get("receipt") == "REJECTED_SCROLL_STEPS_INVALID", bad_steps
            assert bad_steps.get("executed") is False, bad_steps
            assert (scroll_after_negative.get("vertical") or {}).get("pos") == vertical_before.get("pos"), (
                "REJECTED_SCROLL_MUTATED_EDITOR")

            scroll_dry_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": scroll_dry_id,
                "task_id": f"d12-{run_id}", "action": "scroll", "app": target_proc,
                "element_ref": SCROLL_ELEMENT, "scroll_direction": SCROLL_DIRECTION,
                "scroll_unit": SCROLL_UNIT, "scroll_steps": SCROLL_STEPS, "dry_run": True,
            })
            scroll_dry = wait_receipt(tools, scroll_dry_id) or {}
            evidence["steps"]["scroll_dry_run"] = {
                "status": scroll_dry.get("status"),
                "receipt": scroll_dry.get("receipt"),
                "state": scroll_dry.get("state"),
                "executed": scroll_dry.get("executed"),
            }
            assert scroll_dry.get("receipt") == "DRY_RUN_VALIDATED", scroll_dry
            assert scroll_dry.get("state") == "PRESERVED_UNMODIFIED", scroll_dry
            assert scroll_dry.get("executed") is False, scroll_dry

            scroll_id = uuid.uuid4().hex
            publish_request(tools, {
                "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": scroll_id,
                "task_id": f"d12-{run_id}", "action": "scroll", "app": target_proc,
                "element_ref": SCROLL_ELEMENT, "scroll_direction": SCROLL_DIRECTION,
                "scroll_unit": SCROLL_UNIT, "scroll_steps": SCROLL_STEPS, "dry_run": False,
            })
            staged = wait_receipt(tools, scroll_id) or {}
            evidence["steps"]["staged"] = {
                "status": staged.get("status"),
                "receipt": staged.get("receipt"),
                "approval_id": staged.get("approval_id"),
                "target": staged.get("target"),
                "element_ref": SCROLL_ELEMENT,
            }
            assert staged.get("receipt") == "APPROVAL_REQUIRED", staged
            assert staged.get("approval_id") == scroll_id, staged

            pending_before = json.loads(master.hget(APPROVALS_KEY, scroll_id) or "{}")
            evidence["steps"]["pending_before_approval"] = {
                "status": pending_before.get("status"),
                "action": pending_before.get("action"),
                "element_ref": pending_before.get("element_ref"),
                "scroll_direction": pending_before.get("scroll_direction"),
                "scroll_unit": pending_before.get("scroll_unit"),
                "scroll_steps": pending_before.get("scroll_steps"),
                "request_digest_present": bool(pending_before.get("request_digest")),
                "hwnd": pending_before.get("hwnd"),
                "pid": pending_before.get("pid"),
            }
            assert pending_before.get("element_ref") == SCROLL_ELEMENT, "PENDING_ELEMENT_REF_MISSING"
            assert pending_before.get("scroll_direction") == SCROLL_DIRECTION, pending_before
            assert pending_before.get("scroll_unit") == SCROLL_UNIT, pending_before
            assert pending_before.get("scroll_steps") == SCROLL_STEPS, pending_before

            approve = sandbox.spawn_process([
                sys.executable, "-m", "scripts.master_desktop_approve",
                "approve", scroll_id, "--confirm", "--json",
            ], env=approve_env)
            pids["approve"] = approve.pid
            out, err = approve.communicate(timeout=60)
            evidence["steps"]["approve_exit_code"] = approve.returncode
            try:
                approve_result = json.loads(out)
            except Exception:
                approve_result = {"unparsed_stdout": out, "stderr": err}
            server_receipt = approve_result.get("server_receipt")
            receipt_status = server_receipt.get("status") if isinstance(server_receipt, dict) else server_receipt
            evidence["steps"]["approve"] = {
                "status": approve_result.get("status"),
                "executed": approve_result.get("executed"),
                "server_status": approve_result.get("server_status"),
                "server_receipt_status": receipt_status,
                "server_receipt_receipt": server_receipt.get("receipt") if isinstance(server_receipt, dict) else None,
                "pattern_used": server_receipt.get("pattern_used") if isinstance(server_receipt, dict) else None,
                "scrolled": server_receipt.get("scrolled") if isinstance(server_receipt, dict) else None,
                "scroll_steps_requested": server_receipt.get("scroll_steps_requested") if isinstance(server_receipt, dict) else None,
                "scroll_steps_applied": server_receipt.get("scroll_steps_applied") if isinstance(server_receipt, dict) else None,
                "watchdog_stopped": server_receipt.get("watchdog_stopped") if isinstance(server_receipt, dict) else None,
                "element_name": server_receipt.get("element_name") if isinstance(server_receipt, dict) else None,
                "before_snapshot_hash": server_receipt.get("before_snapshot_hash") if isinstance(server_receipt, dict) else None,
                "after_snapshot_hash": server_receipt.get("after_snapshot_hash") if isinstance(server_receipt, dict) else None,
                "lease_id_present": bool(approve_result.get("lease_id")),
                "worker_generation": approve_result.get("worker_generation"),
                "audit_hmac_present": bool((approve_result.get("audit") or {}).get("hmac")),
            }
            assert approve.returncode == 0, (out, err)
            assert approve_result.get("status") == "APPROVED_EXECUTED", approve_result
            assert approve_result.get("server_status") == "MUTATION_EXECUTED", approve_result
            assert approve_result.get("executed") is True, approve_result
            assert isinstance(server_receipt, dict), approve_result
            assert server_receipt.get("status") == "SCROLL_INVOKED", server_receipt
            assert server_receipt.get("receipt") == "UIA_SCROLL_PATTERN_INVOKED", server_receipt
            assert server_receipt.get("scrolled") is True, server_receipt
            assert server_receipt.get("pattern_used") == "ScrollPattern", server_receipt
            assert server_receipt.get("scroll_direction") == SCROLL_DIRECTION, server_receipt
            assert server_receipt.get("scroll_unit") == SCROLL_UNIT, server_receipt
            assert server_receipt.get("scroll_steps_requested") == SCROLL_STEPS, server_receipt
            assert server_receipt.get("scroll_steps_applied") == SCROLL_STEPS, server_receipt
            assert server_receipt.get("watchdog_stopped") is False, server_receipt
            assert server_receipt.get("element_name") == SCROLL_ELEMENT, server_receipt

            scroll_after = run_in_sandbox(sandbox, {"op": "scroll_info", "hwnd": target_hwnd})
            uia_after = run_in_sandbox(
                sandbox, {"op": "uia_scroll", "hwnd": target_hwnd, "identifier": SCROLL_ELEMENT}
            )
            after_text = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})["text"]
            after_capture = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})
            pos_before = int((scroll_before.get("vertical") or {}).get("pos", 0))
            pos_after = int((scroll_after.get("vertical") or {}).get("pos", 0))
            evidence["steps"]["scroll_after"] = {"win32": scroll_after, "uia": uia_after}
            evidence["steps"]["after_state"] = {
                "scroll_pos_before": pos_before,
                "scroll_pos_after": pos_after,
                "scroll_advance": pos_after - pos_before,
                "scroll_advanced": pos_after > pos_before,
                "uia_vertical_percent_before": uia_before.get("vertical_percent"),
                "uia_vertical_percent_after": uia_after.get("vertical_percent"),
                "text_unchanged": after_text == before_text,
                "text_length": len(after_text),
                "text_sha256": sha256_text(after_text),
                "screenshot": {
                    "pixel_changed": after_capture.get("pixel_hash") != before_capture.get("pixel_hash"),
                    "dhash_changed": after_capture.get("dhash") != before_capture.get("dhash"),
                    "is_live_capture": after_capture.get("is_live_capture"),
                },
            }
            assert pos_after > pos_before, evidence["steps"]["after_state"]
            assert after_text == before_text, "SCROLL_MUTATED_TEXT_CONTENT"

            pending_after = json.loads(master.hget(APPROVALS_KEY, scroll_id) or "{}")
            evidence["steps"]["pending_after_approval"] = {
                "status": pending_after.get("status"),
                "text_length": len(pending_after.get("text", "")),
                "text_scrubbed": bool(pending_after.get("text_scrubbed")),
                "executed": bool(pending_after.get("executed")),
            }
            assert pending_after.get("status") == "APPROVED_EXECUTED", pending_after
            assert pending_after.get("text", "") == "", "PLAINTEXT_NOT_SCRUBBED"
            assert pending_after.get("text_scrubbed") is True, pending_after

            audit_secret = os.getenv("JKAI_DESKTOP_AUDIT_SECRET", "").strip()
            agent_chain = verify_audit_chain(agent_audit, audit_secret)
            approval_chain = verify_audit_chain(approval_audit, audit_secret)
            evidence["steps"]["audit"] = {
                "secret_configured": bool(audit_secret),
                "agent": agent_chain,
                "approval": approval_chain,
            }
            assert audit_secret, "JKAI_DESKTOP_AUDIT_SECRET missing: receipts would have hmac=null"
            assert agent_chain["chain_ok"] and agent_chain["hmac_ok"], agent_chain
            assert approval_chain["chain_ok"] and approval_chain["hmac_ok"], approval_chain
            assert agent_chain["hmac_present"] and approval_chain["hmac_present"]

            evidence["steps"]["job_stats"] = sandbox.get_job_stats()
            evidence["verdict"] = "D12_SCROLL_PASS"
            return 0

        # ── Agent live request -> PENDING approval ──────────────────────────
        live_id = uuid.uuid4().hex
        publish_request(tools, {
            "schema": "jkai.desktop.act.v1", "kind": "act", "request_id": live_id,
            "task_id": f"d8-{run_id}", "action": "type_text", "app": target_proc,
            "text": text, "expected_postcondition": f"expected_text:{text}", "dry_run": False,
        })
        staged = wait_receipt(tools, live_id) or {}
        evidence["steps"]["staged"] = {
            "status": staged.get("status"),
            "receipt": staged.get("receipt"),
            "approval_id": staged.get("approval_id"),
            "target": staged.get("target"),
        }
        assert staged.get("receipt") == "APPROVAL_REQUIRED", staged
        assert staged.get("approval_id") == live_id, staged

        pending_before = json.loads(master.hget(APPROVALS_KEY, live_id) or "{}")
        evidence["steps"]["pending_before_approval"] = {
            "status": pending_before.get("status"),
            "text_length": len(pending_before.get("text", "")),
            "text_sha256": sha256_text(pending_before.get("text", "")),
            "request_digest_present": bool(pending_before.get("request_digest")),
            "hwnd": pending_before.get("hwnd"),
            "pid": pending_before.get("pid"),
        }
        assert pending_before.get("text") == text, "PENDING_TEXT_MISSING"

        if mode == "drill":
            # D10: Master rejects a staged mutation. Nothing may reach the target,
            # the approved-once path must refuse a later approve, and closing the
            # sandbox must still terminate every PID (checked in `finally`).
            reject = sandbox.spawn_process([
                sys.executable, "-m", "scripts.master_desktop_approve",
                "reject", live_id, "--confirm", "--reason", "D10_ROLLBACK_DRILL", "--json",
            ], env=approve_env)
            pids["reject"] = reject.pid
            out, err = reject.communicate(timeout=60)
            try:
                reject_result = json.loads(out)
            except Exception:
                reject_result = {"unparsed_stdout": out, "stderr": err}
            evidence["steps"]["reject"] = {
                "exit_code": reject.returncode,
                "status": reject_result.get("status"),
                "executed": reject_result.get("executed"),
                "detail": reject_result.get("detail"),
                "audit_hmac_present": bool((reject_result.get("audit") or {}).get("hmac")),
            }
            assert reject.returncode == 0, (out, err)
            assert reject_result.get("status") == "REJECTED_BY_MASTER", reject_result
            assert reject_result.get("executed") is False, reject_result

            post_reject_text = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})["text"]
            post_reject_capture = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})
            evidence["steps"]["post_reject_state"] = {
                "text_unchanged": post_reject_text == before_text,
                "text_length": len(post_reject_text),
                "text_sha256": sha256_text(post_reject_text),
                "screenshot": {
                    "pixel_changed": post_reject_capture.get("pixel_hash") != before_capture.get("pixel_hash"),
                    "dhash_changed": post_reject_capture.get("dhash") != before_capture.get("dhash"),
                },
            }
            assert post_reject_text == before_text, f"REJECTED_MUTATION_STILL_APPLIED: {post_reject_text!r}"
            assert post_reject_capture.get("dhash") == before_capture.get("dhash"), "REJECTED_MUTATION_CHANGED_VISUALS"

            replay = sandbox.spawn_process([
                sys.executable, "-m", "scripts.master_desktop_approve",
                "approve", live_id, "--confirm", "--json",
            ], env=approve_env)
            pids["replay"] = replay.pid
            replay_out, replay_err = replay.communicate(timeout=60)
            try:
                replay_result = json.loads(replay_out)
            except Exception:
                replay_result = {"unparsed_stdout": replay_out, "stderr": replay_err}
            evidence["steps"]["approve_after_reject"] = {
                "exit_code": replay.returncode,
                "status": replay_result.get("status"),
                "error": replay_result.get("error"),
            }
            assert replay.returncode != 0, replay_out
            assert replay_result.get("error") == "NOT_PENDING", replay_result
            post_replay_text = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})["text"]
            assert post_replay_text == before_text, f"LATE_APPROVAL_APPLIED_MUTATION: {post_replay_text!r}"

            audit_secret = os.getenv("JKAI_DESKTOP_AUDIT_SECRET", "").strip()
            agent_chain = verify_audit_chain(agent_audit, audit_secret)
            approval_chain = verify_audit_chain(approval_audit, audit_secret)
            evidence["steps"]["audit"] = {
                "secret_configured": bool(audit_secret),
                "agent": agent_chain,
                "approval": approval_chain,
            }
            assert audit_secret, "JKAI_DESKTOP_AUDIT_SECRET missing: receipts would have hmac=null"
            assert agent_chain["chain_ok"] and agent_chain["hmac_ok"], agent_chain
            assert approval_chain["chain_ok"] and approval_chain["hmac_ok"], approval_chain
            assert "REJECTED_BY_MASTER" in approval_chain["statuses"], approval_chain

            evidence["steps"]["job_stats"] = sandbox.get_job_stats()
            evidence["verdict"] = "D10_DRILL_PASS"
            return 0

        approve = sandbox.spawn_process([
            sys.executable, "-m", "scripts.master_desktop_approve",
            "approve", live_id, "--confirm", "--json",
        ], env=approve_env)
        pids["approve"] = approve.pid
        out, err = approve.communicate(timeout=60)
        evidence["steps"]["approve_exit_code"] = approve.returncode
        try:
            approve_result = json.loads(out)
        except Exception:
            approve_result = {"unparsed_stdout": out, "stderr": err}
        server_receipt = approve_result.get("server_receipt")
        receipt_status = server_receipt.get("status") if isinstance(server_receipt, dict) else server_receipt
        evidence["steps"]["approve"] = {
            "status": approve_result.get("status"),
            "executed": approve_result.get("executed"),
            "server_status": approve_result.get("server_status"),
            "server_receipt_status": receipt_status,
            "server_receipt_match": server_receipt.get("match") if isinstance(server_receipt, dict) else None,
            "server_receipt_after_hash": server_receipt.get("after_hash") if isinstance(server_receipt, dict) else None,
            "server_receipt_expected_sha256": server_receipt.get("expected_text_sha256") if isinstance(server_receipt, dict) else None,
            "lease_id_present": bool(approve_result.get("lease_id")),
            "worker_generation": approve_result.get("worker_generation"),
            "audit_hmac_present": bool((approve_result.get("audit") or {}).get("hmac")),
        }
        assert approve.returncode == 0, (out, err)
        assert approve_result.get("status") == "APPROVED_EXECUTED", approve_result
        assert approve_result.get("server_status") == "MUTATION_EXECUTED", approve_result
        assert receipt_status == "VERIFIED_MATCH", approve_result
        assert approve_result.get("executed") is True, approve_result
        assert isinstance(server_receipt, dict) and server_receipt.get("match") is True, approve_result
        assert server_receipt.get("expected_text_sha256") == sha256_text(text), approve_result

        # ── Independent after-state hash from inside the desktop ────────────
        after = run_in_sandbox(sandbox, {"op": "get_text", "hwnd": target_hwnd})
        after_text = after["text"]
        after_capture = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})
        expected = before_text + text
        evidence["steps"]["after_state"] = {
            "text_length": len(after_text),
            "text_sha256": sha256_text(after_text),
            "expected_sha256": sha256_text(expected),
            "match": after_text == expected,
            "before_hash": sha256_text(before_text),
            "screenshot": {
                "pixel_hash": after_capture.get("pixel_hash"),
                "dhash": after_capture.get("dhash"),
                "is_live_capture": after_capture.get("is_live_capture"),
                "pixel_changed": after_capture.get("pixel_hash") != before_capture.get("pixel_hash"),
                "dhash_changed": after_capture.get("dhash") != before_capture.get("dhash"),
            },
        }
        assert after_text == expected, f"AFTER_STATE_MISMATCH: {after_text!r}"
        after_shot = evidence["steps"]["after_state"]["screenshot"]
        if after_shot["is_live_capture"] and before_capture.get("is_live_capture"):
            assert after_shot["pixel_changed"], "SCREENSHOT_UNCHANGED_AFTER_MUTATION"

        last_status, last_receipt = http_json("GET", base, "/receipt/last")
        evidence["steps"]["server_last_receipt"] = {
            "http": last_status,
            "keys": sorted(last_receipt.keys()) if isinstance(last_receipt, dict) else None,
            "status": last_receipt.get("status") if isinstance(last_receipt, dict) else None,
            "match": last_receipt.get("match") if isinstance(last_receipt, dict) else None,
        }

        # ── Plaintext scrub + audit chains ──────────────────────────────────
        pending_after = json.loads(master.hget(APPROVALS_KEY, live_id) or "{}")
        evidence["steps"]["pending_after_approval"] = {
            "status": pending_after.get("status"),
            "text_length": len(pending_after.get("text", "")),
            "text_scrubbed": bool(pending_after.get("text_scrubbed")),
            "executed": bool(pending_after.get("executed")),
        }
        assert pending_after.get("text", "") == "", "PLAINTEXT_NOT_SCRUBBED"
        assert pending_after.get("text_scrubbed") is True, pending_after

        audit_secret = os.getenv("JKAI_DESKTOP_AUDIT_SECRET", "").strip()
        agent_chain = verify_audit_chain(agent_audit, audit_secret)
        approval_chain = verify_audit_chain(approval_audit, audit_secret)
        evidence["steps"]["audit"] = {
            "secret_configured": bool(audit_secret),
            "agent": agent_chain,
            "approval": approval_chain,
        }
        assert audit_secret, "JKAI_DESKTOP_AUDIT_SECRET missing: receipts would have hmac=null"
        assert agent_chain["chain_ok"] and agent_chain["hmac_ok"], agent_chain
        assert approval_chain["chain_ok"] and approval_chain["hmac_ok"], approval_chain
        assert agent_chain["hmac_present"] and approval_chain["hmac_present"]

        evidence["steps"]["job_stats"] = sandbox.get_job_stats()
        evidence["verdict"] = "D9P_PASS" if wordpad_mode else "D8_PASS"
        return 0
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        for index, drainer in enumerate(drainers):
            evidence[f"log_{index}"] = drainer.text()[-4000:]
        raise
    finally:
        try:
            sandbox.close()
        except Exception as exc:  # noqa: BLE001
            evidence["close_error"] = str(exc)

        # ── D10 containment: mọi PID phải bị Kernel Job Object tiêu diệt ────
        import psutil

        time.sleep(1.0)
        alive = {name: pid for name, pid in pids.items() if psutil.pid_exists(pid)}
        evidence["steps"]["containment"] = {
            "pids": dict(pids),
            "alive_after_close": alive,
            "all_terminated": not alive,
            "desktop_closed": sandbox.h_desktop is None,
        }
        if evidence.get("verdict") == "D11_CLICK_PASS" and alive:
            evidence["verdict"] = "D11_CLICK_CONTAINMENT_FAILED"
        elif evidence.get("verdict") == "D12_SCROLL_PASS" and alive:
            evidence["verdict"] = "D12_SCROLL_CONTAINMENT_FAILED"
        elif evidence.get("verdict") == "D10_DRILL_PASS" and alive:
            evidence["verdict"] = "D10_DRILL_CONTAINMENT_FAILED"
        elif evidence.get("verdict") == "D9P_PASS" and alive:
            evidence["verdict"] = "D9P_CONTAINMENT_FAILED"
        elif evidence.get("verdict") == "D8_PASS" and alive:
            evidence["verdict"] = "D8_CONTAINMENT_FAILED"
        elif evidence.get("verdict") == "D7_DRY_PASS" and alive:
            evidence["verdict"] = "D7_CONTAINMENT_FAILED"

        path = write_artifact(evidence)
        print(f"[EVIDENCE] {path}")
        print(f"[VERDICT] {evidence['verdict']}  containment={evidence['steps'].get('containment')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry", "native", "wordpad", "drill", "click", "scroll"], default="dry")
    args = parser.parse_args()
    try:
        return run(args.mode)
    except AssertionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
