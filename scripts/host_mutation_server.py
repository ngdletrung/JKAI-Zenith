# -*- coding: utf-8 -*-
"""
scripts/host_mutation_server.py
[JKAI REAL HOST MUTATION IPC SERVER (PORT 9996) v2.5]

IPC Server chạy độc lập trên CỔNG 9996 để phục vụ tương tác an toàn với Host.
Tuyệt đối tách biệt khỏi CỔNG 9997 (Pure Read-Only Sampler).

Quy tắc bảo vệ:
1. Mặc định: JKAI_MUTATION_ENABLED = false (Khóa an toàn). Mọi yêu cầu mutate đều trả về DRY_RUN/BLOCKED.
2. Hai tầng xác thực mật mã:
   - Tầng 1: /lease/request bắt buộc có Master Auth Token hợp lệ.
   - Tầng 2: /mutate/type_text bắt buộc có Master Approval Signature hợp lệ.
3. Target Identity & Anti-TOCTOU Revalidation trước khi gửi ký tự.
4. Independent After-State Verifier xuất receipt sau khi thực thi.

Changelog v2.5:
- Thêm /test/schedule_crash_after_claim (TEST_MODE): inject crash ngay sau compound SQLite commit,
  trước khi native dispatch bắt đầu → chứng minh crash-after-claim thật sự.
- Structured event logging: lease_id, correlation_id, compound claim timestamp, PostMessageW events,
  watchdog events, cleanup result.
- Production guard: /watchdog/trigger, /watchdog/reset, /watchdog/schedule_mid_dispatch,
  /test/schedule_crash_after_claim đều trả 403 khi JKAI_MUTATION_TEST_MODE != "1".
"""

import os
import sys
import time
import json
import uuid
import base64
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional

# Đảm bảo stdout/stderr UTF-8 trên Windows (tránh cp1252 UnicodeEncodeError khi log)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scripts.master_approval_verifier import MasterApprovalVerifier
from scripts.host_mutation_worker import HostMutationWorker
from scripts.persistent_nonce_store import PersistentNonceStore
from scripts.target_identity_validator import TargetIdentityValidator
from scripts.host_after_state_verifier import HostAfterStateVerifier

DEFAULT_PORT = 9996
MAX_REQUEST_SIZE = 65536  # 64 KB Hardening Limit

class HostMutationHandler(BaseHTTPRequestHandler):
    worker: Optional[HostMutationWorker] = None
    after_verifier: Optional[HostAfterStateVerifier] = None

    def log_message(self, format, *args):
        # Bật logging đầy đủ khi TEST_MODE, tắt khi production để tránh làm bẩn console
        if os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1":
            try:
                sys.stdout.write("[SERVER] %s\n" % (format % args))
                sys.stdout.flush()
            except Exception:
                pass

    def _log_event(self, event_type: str, **kwargs):
        """Structured event logging với correlation_id, timestamp, lease_id, event_type."""
        if os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1":
            try:
                payload = {
                    "event": event_type,
                    "ts": time.time(),
                    "correlation_id": getattr(self, "_correlation_id", ""),
                    **kwargs
                }
                msg = f"[EVENT] {json.dumps(payload, ensure_ascii=True)}\n"
                sys.stdout.write(msg)
                sys.stdout.flush()
            except Exception:
                pass

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_GET(self):
        if self.path == "/health":
            actual_port = self.server.server_address[1]  # port thực tế server đang bind, không hardcode
            is_active, active_mode = self.worker.is_mutation_active() if self.worker else (False, "NO_WORKER")
            self._send_json(200, {
                "status": "ok",
                "port": actual_port,
                "mutation_enabled": is_active,
                "mutation_mode": active_mode,
                "worker_generation": self.worker.worker_generation if self.worker else "unknown",
                "active_leases": len(self.worker._active_leases) if self.worker else 0,
                "test_mode": os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            })
        elif self.path == "/receipt/last":
            # Handler instances are created per request, so the receipt must live
            # on the server object; an instance attribute would be lost immediately.
            last = getattr(self.server, "last_receipt", None)
            self._send_json(200, last or {"status": "NO_RECEIPT_YET"})
        else:
            self._send_json(404, {"error": "NOT_FOUND"})

    def _execute_ui_mutation(self, body: dict, expected_action: str):
        """
        Chuỗi thực thi chung cho các hành động UIA (click/scroll):
        preflight auth -> action-endpoint match -> before UIA hash -> attach -> execute
        -> after UIA hash. Trả về dict kết quả; khi bị chặn, response đã được gửi
        và trả về None.
        """
        approval_token = body.get("approval_token", "")
        lease_id = body.get("lease_id", "")
        signature = body.get("signature", "")

        if not self.worker:
            self._send_json(500, {"status": "SERVER_ERROR", "reason": "WORKER_NOT_INITIALIZED"})
            return None

        self._log_event("PREFLIGHT_START", lease_id=lease_id, action=expected_action)
        ok_auth, auth_reason, lease = self.worker.preflight_verify_authorization(
            lease_id=lease_id,
            signature=signature,
            master_approval_signature=approval_token
        )
        if not ok_auth or not lease:
            self._log_event("PREFLIGHT_DENIED", lease_id=lease_id, reason=auth_reason)
            self._send_json(403, {
                "status": "MUTATION_BLOCKED",
                "reason": auth_reason,
                "receipt": "NOT_EXECUTED_AUTH_FAILED"
            })
            return None

        if lease.get("action") != expected_action:
            self._log_event("PREFLIGHT_ACTION_MISMATCH", lease_id=lease_id,
                            action=lease.get("action"))
            self._send_json(403, {
                "status": "MUTATION_BLOCKED",
                "reason": f"ACTION_ENDPOINT_MISMATCH: lease action is {lease.get('action')}",
                "receipt": "NOT_EXECUTED_ACTION_ENDPOINT_MISMATCH"
            })
            return None

        self._log_event("PREFLIGHT_PASSED", lease_id=lease_id, action=expected_action)
        target_hwnd = lease.get("hwnd", 0)

        # Before-state: fresh UIA tree hash. Scroll offsets are not part of this
        # hash, so it is provenance for the dispatch, not proof of the effect;
        # the live test observes scroll position independently (Win32 GetScrollInfo).
        try:
            from services.ai_desktop.uia_tree_inspector import UIATreeInspector
            before_snapshot = UIATreeInspector(is_live_mode=True).inspect_tree(
                int(target_hwnd), force_fresh=True)
            before_hash = str(before_snapshot.snapshot_hash or "")
            if not before_hash or before_hash.startswith("empty_"):
                raise RuntimeError(f"UIA_TREE_EMPTY: {before_hash}")
        except Exception as exc:
            self._log_event("BEFORE_SNAPSHOT_FAILED", lease_id=lease_id, text=str(exc))
            self._send_json(403, {
                "status": "MUTATION_BLOCKED",
                "reason": f"BEFORE_SNAPSHOT_FAILED: {exc}",
                "receipt": "NOT_EXECUTED_BEFORE_SNAPSHOT_FAILED"
            })
            return None

        owner_token = lease.get("preflight_owner_token", "")
        ok_attach, attach_reason = self.worker.attach_before_snapshot(
            lease_id, owner_token, before_hash)
        if not ok_attach:
            self._log_event("SNAPSHOT_ATTACH_FAILED", lease_id=lease_id, reason=attach_reason)
            self._send_json(403, {
                "status": "MUTATION_BLOCKED",
                "reason": attach_reason,
                "receipt": "NOT_EXECUTED_SNAPSHOT_CORRELATION_FAILED"
            })
            return None

        try:
            result = self.worker.execute_with_lease(
                lease_id=lease_id,
                signature=signature,
                master_approval_signature=approval_token,
                owner_token=owner_token,
                before_snapshot_hash=before_hash
            )
        except RuntimeError as crash_err:
            crash_msg = str(crash_err)
            self._log_event("CRASH_INJECTED", lease_id=lease_id, msg=crash_msg[:120])
            self._send_json(500, {
                "status": "SERVER_CRASH_AFTER_COMPOUND_CLAIM",
                "error": crash_msg,
                "compound_claim_committed": True,
                "nonce_persisted_in_sqlite": True,
                "recovery": "RESTART_SERVER_THEN_REPLAY_MUST_YIELD_REPLAY_ATTACK_DETECTED"
            })
            return None

        self._log_event("EXECUTE_RESULT", lease_id=lease_id,
                        status=result.get("status"),
                        receipt=result.get("receipt"),
                        pattern=result.get("pattern_used"))

        after_hash = ""
        if result.get("status") == "EXECUTED":
            try:
                from services.ai_desktop.uia_tree_inspector import UIATreeInspector
                after_hash = str(UIATreeInspector(is_live_mode=True).inspect_tree(
                    int(target_hwnd), force_fresh=True).snapshot_hash or "")
            except Exception as exc:
                self._log_event("AFTER_SNAPSHOT_FAILED", lease_id=lease_id, text=str(exc))

        return {
            "result": result,
            "lease": lease,
            "target_hwnd": target_hwnd,
            "before_hash": before_hash,
            "after_hash": after_hash,
        }

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            self._send_json(400, {"error": "INVALID_CONTENT_LENGTH"})
            return

        if content_length <= 0:
            self._send_json(411, {"error": "LENGTH_REQUIRED"})
            return

        if content_length > MAX_REQUEST_SIZE:
            self._send_json(413, {"error": f"PAYLOAD_TOO_LARGE: max allowed is {MAX_REQUEST_SIZE} bytes"})
            return

        post_data = self.rfile.read(content_length)
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._send_json(400, {"error": "INVALID_JSON_BODY"})
            return

        # Per-request correlation ID cho event log
        self._correlation_id = uuid.uuid4().hex[:8]

        if self.path == "/mutation/activate":
            # Cơ chế One-Shot Master Activation Token (Finding 1, 2, 3, 4)
            # Yêu cầu token ký số Ed25519 chứa target_hwnd và session_id
            token = body.get("token", "")
            session_id = body.get("session_id", "")
            target_hwnd = body.get("target_hwnd", 0)

            if not self.worker:
                self._send_json(500, {"status": "SERVER_ERROR", "reason": "WORKER_NOT_INITIALIZED"})
                return

            ok_act, act_reason, act_details = self.worker.activate_one_shot(
                master_auth_token=token,
                session_id=session_id,
                target_hwnd=int(target_hwnd or 0)
            )
            if ok_act:
                self._log_event("ONE_SHOT_MUTATION_ACTIVATED", **act_details)
                self._send_json(200, {"status": "ONE_SHOT_ACTIVATED", "details": act_details})
            else:
                self._log_event("ONE_SHOT_ACTIVATION_DENIED", reason=act_reason)
                self._send_json(403, {"status": "ACTIVATION_DENIED", "reason": act_reason})

        elif self.path == "/lease/request":
            token = body.get("token", "")
            session_id = body.get("session_id", "")
            hwnd = body.get("hwnd", 0)
            action = body.get("action", "type")
            text = body.get("text", "")
            element_ref = body.get("element_ref", "")
            scroll_direction = body.get("scroll_direction", "")
            scroll_unit = body.get("scroll_unit", "")
            scroll_steps = body.get("scroll_steps", 0)

            try:
                lease = self.worker.request_one_time_lease(
                    hwnd=hwnd,
                    action=action,
                    expected_session_id=session_id,
                    text_payload=text,
                    element_ref=element_ref,
                    scroll_direction=scroll_direction,
                    scroll_unit=scroll_unit,
                    scroll_steps=scroll_steps,
                    master_auth_token=token
                )
                self._log_event("LEASE_GRANTED",
                                lease_id=lease.get("lease_id", ""),
                                hwnd=hwnd, action=action,
                                element_ref=element_ref,
                                text_len=len(text))
                self._send_json(200, {"status": "LEASE_GRANTED", "lease": lease})
            except Exception as e:
                self._log_event("LEASE_DENIED", reason=str(e), hwnd=hwnd)
                self._send_json(403, {"status": "LEASE_DENIED", "reason": str(e)})

        elif self.path == "/mutate/type_text":
            approval_token = body.get("approval_token", "")
            lease_id = body.get("lease_id", "")
            signature = body.get("signature", "")

            # 1. PREFLIGHT FULL AUTHORIZATION FIRST:
            # Xác thực 100% mật mã (HMAC lease, Ed25519 approval, Expiry, Session, Nonce) trước khi chạm vào bất kỳ HWND nào!
            if not self.worker:
                self._send_json(500, {"status": "SERVER_ERROR", "reason": "WORKER_NOT_INITIALIZED"})
                return

            self._log_event("PREFLIGHT_START", lease_id=lease_id)
            ok_auth, auth_reason, lease = self.worker.preflight_verify_authorization(
                lease_id=lease_id,
                signature=signature,
                master_approval_signature=approval_token
            )
            if not ok_auth or not lease:
                self._log_event("PREFLIGHT_DENIED", lease_id=lease_id, reason=auth_reason)
                self._send_json(403, {
                    "status": "MUTATION_BLOCKED",
                    "reason": auth_reason,
                    "receipt": "NOT_EXECUTED_AUTH_FAILED"
                })
                return

            self._log_event("PREFLIGHT_PASSED", lease_id=lease_id)

            # Target HWND được lấy an toàn 100% từ Lease đã xác thực mật mã
            target_hwnd = lease.get("hwnd", 0)

            # 2. Snapshot Before State độc lập (Chỉ sau khi đã preflight authorization thành công)
            before_snapshot = {}
            if self.after_verifier:
                before_snapshot = self.after_verifier.capture_snapshot(
                    target_hwnd, proc_name=lease.get("proc_name") or "notepad.exe")
                if not before_snapshot or not before_snapshot.get("read_success", False):
                    self._log_event("BEFORE_SNAPSHOT_FAILED", lease_id=lease_id,
                                    text=before_snapshot.get("text", ""))
                    self._send_json(403, {
                        "status": "MUTATION_BLOCKED",
                        "reason": f"BEFORE_SNAPSHOT_FAILED: {before_snapshot.get('text', 'Failed to read window buffer')}",
                        "receipt": "NOT_EXECUTED_BEFORE_SNAPSHOT_FAILED"
                    })
                    return
            else:
                self._send_json(500, {
                    "status": "MUTATION_BLOCKED",
                    "reason": "AFTER_STATE_VERIFIER_UNAVAILABLE",
                    "receipt": "NOT_EXECUTED_VERIFIER_UNAVAILABLE"
                })
                return

            # 2.1. Gắn hash before-snapshot vào lease (chỉ chủ preflight được gắn, chỉ một lần)
            owner_token = lease.get("preflight_owner_token", "")
            snapshot_hash = before_snapshot.get("hash", "")
            ok_attach, attach_reason = self.worker.attach_before_snapshot(lease_id, owner_token, snapshot_hash)
            if not ok_attach:
                self._log_event("SNAPSHOT_ATTACH_FAILED", lease_id=lease_id, reason=attach_reason)
                self._send_json(403, {
                    "status": "MUTATION_BLOCKED",
                    "reason": attach_reason,
                    "receipt": "NOT_EXECUTED_SNAPSHOT_CORRELATION_FAILED"
                })
                return

            self._log_event("BEFORE_SNAPSHOT_ATTACHED",
                            lease_id=lease_id, snapshot_hash=snapshot_hash[:16])

            # Văn bản kỳ vọng lấy từ lease đã ký, KHÔNG lấy từ client
            expected_text = lease.get("text_payload", "")

            # 3. Thực thi hành động / Tiêu thụ Nonce / Anti-TOCTOU Revalidation
            self._log_event("EXECUTE_START", lease_id=lease_id,
                            text_len=len(expected_text))
            try:
                result = self.worker.execute_with_lease(
                    lease_id=lease_id,
                    signature=signature,
                    master_approval_signature=approval_token,
                    owner_token=owner_token,
                    before_snapshot_hash=snapshot_hash
                )
            except RuntimeError as crash_err:
                # TEST_CRASH_INJECTED_AFTER_COMPOUND_CLAIM: nonce đã persist trong SQLite.
                # Server trả 500 để client biết crash xảy ra SAU compound claim.
                # Restart server → replay phải trả REPLAY_ATTACK_DETECTED.
                crash_msg = str(crash_err)
                self._log_event("CRASH_INJECTED", lease_id=lease_id, msg=crash_msg[:120])
                self._send_json(500, {
                    "status": "SERVER_CRASH_AFTER_COMPOUND_CLAIM",
                    "error": crash_msg,
                    "compound_claim_committed": True,
                    "nonce_persisted_in_sqlite": True,
                    "recovery": "RESTART_SERVER_THEN_REPLAY_MUST_YIELD_REPLAY_ATTACK_DETECTED"
                })
                return
            self._log_event("EXECUTE_RESULT", lease_id=lease_id,
                            status=result.get("status"),
                            receipt=result.get("receipt"),
                            units_sent=result.get("units_sent"))

            # 4. Trả kết quả minh bạch & kiểm chứng After-State
            if result.get("status") in ("MUTATION_DISABLED_DRY_RUN", "BLOCKED_BY_DEFAULT"):
                receipt = {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "receipt": "MUTATION_DISABLED_DRY_RUN_RECEIPT",
                    "state": "PRESERVED_UNMODIFIED",
                    "timestamp": time.time(),
                    "target_hwnd": target_hwnd,
                    "precondition_verified": True
                }
                self.server.last_receipt = receipt

                self._send_json(200, {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "auth_verified": True,
                    "dry_run": True,
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("status") in ("EXECUTED", "DELIVERED_VERIFIED", "DELIVERED_UNVERIFIED"):
                receipt = {}
                if self.after_verifier:
                    receipt = self.after_verifier.verify_action_result(
                        before_snapshot=before_snapshot,
                        hwnd=target_hwnd,
                        expected_mutation_text=expected_text,
                        proc_name=lease.get("proc_name") or "notepad.exe",
                        timeout_seconds=2.0
                    )
                    self.server.last_receipt = receipt
                    self._log_event("AFTER_STATE_VERIFIED", lease_id=lease_id,
                                    match=receipt.get("match"),
                                    after_hash=str(receipt.get("after_hash", ""))[:16])

                self._send_json(200, {
                    "status": "MUTATION_EXECUTED",
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("receipt") in ("CLAIMED_PARTIALLY_DELIVERED", "CLAIMED_NOT_DELIVERED", "CLAIMED_DELIVERY_UNCERTAIN"):
                # Partial/no/uncertain delivery — trả 200 với result đầy đủ để client có thể assert receipt enum
                self._log_event("PARTIAL_DELIVERY", lease_id=lease_id,
                                receipt=result.get("receipt"),
                                units_sent=result.get("units_sent", 0))
                self._send_json(200, {
                    "status": (
                        "MUTATION_DELIVERY_UNCERTAIN"
                        if result.get("receipt") == "CLAIMED_DELIVERY_UNCERTAIN"
                        else "MUTATION_PARTIAL_OR_NOT_DELIVERED"
                    ),
                    "result": result,
                    "receipt": result.get("receipt")
                })
            else:
                # Bị chặn do TOCTOU / Drift / Watchdog Stop Latch
                self._log_event("MUTATION_BLOCKED", lease_id=lease_id,
                                reason=result.get("receipt"))
                self._send_json(403, {
                    "status": "MUTATION_BLOCKED",
                    "result": result,
                    "receipt": "NOT_EXECUTED_TOCTOU_OR_WATCHDOG_BLOCKED"
                })

        elif self.path == "/mutate/click":
            ctx = self._execute_ui_mutation(body, expected_action="click")
            if ctx is None:
                return
            result = ctx["result"]
            lease = ctx["lease"]
            target_hwnd = ctx["target_hwnd"]
            before_hash = ctx["before_hash"]
            after_hash = ctx["after_hash"]

            if result.get("status") == "MUTATION_DISABLED_DRY_RUN":
                receipt = {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "receipt": "MUTATION_DISABLED_DRY_RUN_RECEIPT",
                    "action": "click",
                    "state": "PRESERVED_UNMODIFIED",
                    "timestamp": time.time(),
                    "target_hwnd": target_hwnd,
                    "element_identifier": lease.get("element_ref", ""),
                    "precondition_verified": True
                }
                self.server.last_receipt = receipt
                self._send_json(200, {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "auth_verified": True,
                    "dry_run": True,
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("status") == "EXECUTED":
                receipt = {
                    "status": "CLICK_INVOKED",
                    "receipt": "UIA_PATTERN_INVOKED",
                    "action": "click",
                    "target_hwnd": target_hwnd,
                    "element_identifier": lease.get("element_ref", ""),
                    "element_name": result.get("element_name", ""),
                    "element_automation_id": result.get("element_automation_id", ""),
                    "element_control_type": result.get("element_control_type", ""),
                    "pattern_used": result.get("pattern_used", ""),
                    "invoked": bool(result.get("invoked")),
                    "before_snapshot_hash": before_hash,
                    "after_snapshot_hash": after_hash,
                    "observed_state_changed": bool(after_hash) and after_hash != before_hash,
                    "observation_note": (
                        "UIA tree hash excludes scroll offsets; scroll effects need an "
                        "independent ScrollPattern observer."
                    ),
                    "timestamp": time.time(),
                }
                self.server.last_receipt = receipt
                self._send_json(200, {
                    "status": "MUTATION_EXECUTED",
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("receipt") in ("CLAIMED_PARTIALLY_DELIVERED", "CLAIMED_NOT_DELIVERED", "CLAIMED_DELIVERY_UNCERTAIN"):
                self._log_event("CLICK_NOT_DELIVERED", lease_id=lease.get("lease_id", ""),
                                receipt=result.get("receipt"),
                                reason=result.get("reason"))
                self._send_json(200, {
                    "status": (
                        "MUTATION_DELIVERY_UNCERTAIN"
                        if result.get("receipt") == "CLAIMED_DELIVERY_UNCERTAIN"
                        else "MUTATION_PARTIAL_OR_NOT_DELIVERED"
                    ),
                    "result": result,
                    "receipt": result.get("receipt")
                })
            else:
                self._log_event("MUTATION_BLOCKED", lease_id=lease.get("lease_id", ""),
                                reason=result.get("receipt"))
                self._send_json(403, {
                    "status": "MUTATION_BLOCKED",
                    "result": result,
                    "receipt": "NOT_EXECUTED_TOCTOU_OR_WATCHDOG_BLOCKED"
                })

        elif self.path == "/mutate/scroll":
            ctx = self._execute_ui_mutation(body, expected_action="scroll")
            if ctx is None:
                return
            result = ctx["result"]
            lease = ctx["lease"]
            target_hwnd = ctx["target_hwnd"]
            before_hash = ctx["before_hash"]
            after_hash = ctx["after_hash"]

            if result.get("status") == "MUTATION_DISABLED_DRY_RUN":
                receipt = {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "receipt": "MUTATION_DISABLED_DRY_RUN_RECEIPT",
                    "action": "scroll",
                    "state": "PRESERVED_UNMODIFIED",
                    "timestamp": time.time(),
                    "target_hwnd": target_hwnd,
                    "element_identifier": lease.get("element_ref", ""),
                    "scroll_direction": lease.get("scroll_direction", ""),
                    "scroll_unit": lease.get("scroll_unit", ""),
                    "scroll_steps": lease.get("scroll_steps", 0),
                    "precondition_verified": True
                }
                self.server.last_receipt = receipt
                self._send_json(200, {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "auth_verified": True,
                    "dry_run": True,
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("status") == "EXECUTED":
                receipt = {
                    "status": "SCROLL_INVOKED",
                    "receipt": "UIA_SCROLL_PATTERN_INVOKED",
                    "action": "scroll",
                    "target_hwnd": target_hwnd,
                    "element_identifier": lease.get("element_ref", ""),
                    "element_name": result.get("element_name", ""),
                    "element_automation_id": result.get("element_automation_id", ""),
                    "element_control_type": result.get("element_control_type", ""),
                    "pattern_used": result.get("pattern_used", ""),
                    "scrolled": bool(result.get("scrolled")),
                    "scroll_direction": result.get("scroll_direction", ""),
                    "scroll_unit": result.get("scroll_unit", ""),
                    "scroll_steps_requested": result.get("scroll_steps_requested", 0),
                    "scroll_steps_applied": result.get("scroll_steps_applied", 0),
                    "watchdog_stopped": bool(result.get("watchdog_stopped")),
                    "vertical_percent_before": result.get("vertical_percent_before"),
                    "vertical_percent_after": result.get("vertical_percent_after"),
                    "before_snapshot_hash": before_hash,
                    "after_snapshot_hash": after_hash,
                    "observed_state_changed": bool(after_hash) and after_hash != before_hash,
                    "observation_note": (
                        "UIA tree hash excludes scroll offsets; scroll effect is proven by "
                        "ScrollPattern percent delta and Win32 GetScrollInfo nPos."
                    ),
                    "timestamp": time.time(),
                }
                self.server.last_receipt = receipt
                self._send_json(200, {
                    "status": "MUTATION_EXECUTED",
                    "result": result,
                    "receipt": receipt
                })
            elif result.get("receipt") in ("CLAIMED_PARTIALLY_DELIVERED", "CLAIMED_NOT_DELIVERED", "CLAIMED_DELIVERY_UNCERTAIN"):
                self._log_event("SCROLL_NOT_DELIVERED", lease_id=lease.get("lease_id", ""),
                                receipt=result.get("receipt"),
                                reason=result.get("reason"))
                self._send_json(200, {
                    "status": (
                        "MUTATION_DELIVERY_UNCERTAIN"
                        if result.get("receipt") == "CLAIMED_DELIVERY_UNCERTAIN"
                        else "MUTATION_PARTIAL_OR_NOT_DELIVERED"
                    ),
                    "result": result,
                    "receipt": result.get("receipt")
                })
            else:
                self._log_event("MUTATION_BLOCKED", lease_id=lease.get("lease_id", ""),
                                reason=result.get("receipt"))
                self._send_json(403, {
                    "status": "MUTATION_BLOCKED",
                    "result": result,
                    "receipt": "NOT_EXECUTED_TOCTOU_OR_WATCHDOG_BLOCKED"
                })

        elif self.path == "/mutate/revoke_lease":
            lease_id = body.get("lease_id")
            revoked = self.worker.revoke_lease(lease_id)
            self._send_json(200, {"status": "REVOKED" if revoked else "NOT_FOUND"})

        elif self.path == "/watchdog/trigger":
            # CHỈ cho phép trong TEST MODE — không bao giờ expose trên production
            test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            if not test_mode:
                self._send_json(403, {"error": "TEST_ENDPOINT_DISABLED_IN_PRODUCTION"})
                return
            reason = body.get("reason", "TEST_WATCHDOG_TRIGGER")
            if self.worker and self.worker.watchdog:
                latency_ms = self.worker.watchdog.trigger_stop(reason)
                self._log_event("WATCHDOG_TRIGGERED", reason=reason, latency_ms=latency_ms)
                self._send_json(200, {"status": "WATCHDOG_TRIGGERED", "reason": reason, "latency_ms": latency_ms})
            else:
                self._send_json(500, {"error": "WATCHDOG_NOT_AVAILABLE"})

        elif self.path == "/watchdog/schedule_mid_dispatch":
            # CHỈ TEST MODE: Hẹn trigger watchdog sau N ký tự được gửi.
            # Server set biến _stop_after_chars trên worker; dispatch loop kiểm tra và trigger.
            test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            if not test_mode:
                self._send_json(403, {"error": "TEST_ENDPOINT_DISABLED_IN_PRODUCTION"})
                return
            stop_after = int(body.get("stop_after_chars", 3))
            reason = body.get("reason", "TEST_STOP_MID_DISPATCH")
            if self.worker:
                self.worker._test_stop_after_chars = max(1, stop_after)
                self.worker._test_stop_reason = reason
                self._log_event("MID_DISPATCH_SCHEDULED",
                                stop_after_chars=stop_after, reason=reason)
                self._send_json(200, {"status": "MID_DISPATCH_STOP_SCHEDULED",
                                      "stop_after_chars": stop_after, "reason": reason})
            else:
                self._send_json(500, {"error": "WORKER_NOT_AVAILABLE"})

        elif self.path == "/watchdog/reset":
            # CHỈ cho phép trong TEST MODE
            test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            if not test_mode:
                self._send_json(403, {"error": "TEST_ENDPOINT_DISABLED_IN_PRODUCTION"})
                return
            token = body.get("token", "TEST_RESET")
            if self.worker and self.worker.watchdog:
                ok = self.worker.watchdog.reset_latch(token)
                self._log_event("WATCHDOG_RESET", ok=ok)
                self._send_json(200, {"status": "WATCHDOG_RESET" if ok else "WATCHDOG_RESET_FAILED"})
            else:
                self._send_json(500, {"error": "WATCHDOG_NOT_AVAILABLE"})

        elif self.path == "/test/schedule_crash_after_claim":
            # CHỈ TEST MODE: Hẹn inject crash (RuntimeError) ngay sau compound SQLite commit thành công,
            # TRƯỚC khi native PostMessageW dispatch bắt đầu. Dùng để chứng minh:
            # crash sau claim → restart → replay bị REPLAY_ATTACK_DETECTED (nonce đã persist trong SQLite).
            test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            if not test_mode:
                self._send_json(403, {"error": "TEST_ENDPOINT_DISABLED_IN_PRODUCTION"})
                return
            if self.worker:
                self.worker._test_crash_after_claim = True
                self._log_event("CRASH_AFTER_CLAIM_SCHEDULED")
                self._send_json(200, {
                    "status": "CRASH_AFTER_CLAIM_SCHEDULED",
                    "description": (
                        "Next execute_with_lease call will raise RuntimeError "
                        "immediately after compound SQLite commit, before PostMessageW. "
                        "Server will return 500. Restart server; replay must yield REPLAY_ATTACK_DETECTED."
                    )
                })
            else:
                self._send_json(500, {"error": "WORKER_NOT_AVAILABLE"})

        elif self.path == "/test/set_mutation_enabled":
            # CHỈ TEST MODE: Cho phép chuyển đổi biến worker.mutation_enabled giữa True/False trong harness test.
            # Dùng để kiểm thử chuyển đổi giữa Global Env Mode và One-Shot Activation Mode.
            test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
            if not test_mode:
                self._send_json(403, {"error": "TEST_ENDPOINT_DISABLED_IN_PRODUCTION"})
                return
            enabled = bool(body.get("enabled", False))
            if self.worker:
                self.worker.mutation_enabled = enabled
                self._log_event("TEST_MUTATION_ENABLED_SET", enabled=enabled)
                self._send_json(200, {"status": "OK", "mutation_enabled": enabled})
            else:
                self._send_json(500, {"error": "WORKER_NOT_AVAILABLE"})

        else:
            self._send_json(404, {"error": "NOT_FOUND"})

def create_mutation_server(
    port: int = DEFAULT_PORT,
    worker: Optional[HostMutationWorker] = None,
    start_watchdog: bool = False
) -> ThreadingHTTPServer:
    worker_instance = worker or HostMutationWorker()
    # Đường IPC: bắt buộc preflight owner token + before-snapshot correlation
    worker_instance.require_preflight_owner = True
    # Khi bật gõ phím thật, watchdog ESC/F12/góc (0,0) BẮT BUỘC phải chạy
    if start_watchdog or worker_instance.mutation_enabled:
        worker_instance.watchdog.start_monitoring()
    HostMutationHandler.worker = worker_instance
    HostMutationHandler.after_verifier = HostAfterStateVerifier()
    server = ThreadingHTTPServer(("127.0.0.1", port), HostMutationHandler)
    server.daemon_threads = True
    server.last_receipt = None
    return server

if __name__ == "__main__":
    port = int(os.getenv("JKAI_MUTATION_PORT", str(DEFAULT_PORT)))
    server = create_mutation_server(port=port, start_watchdog=True)
    print(f"[MUTATION_SERVER] Running on http://127.0.0.1:{port} (MUTATION_ENABLED={HostMutationHandler.worker.mutation_enabled}, WATCHDOG=ON)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[MUTATION_SERVER] Shutting down.")
        server.server_close()
    except Exception as exc:
        import traceback
        sys.stderr.write(f"[MUTATION_SERVER] FATAL CRASH: {exc}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        server.server_close()
