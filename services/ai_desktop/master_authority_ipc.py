# -*- coding: utf-8 -*-
"""
services/ai_desktop/master_authority_ipc.py
[JKAI MASTER AUTHORITY IPC SERVICE & CLIENT - PRODUCTION HARDENED v2.1]

Cung cấp cơ chế phân tách tiến trình thực tế (Physical Process Separation)
với bảo mật đa tầng đạt chuẩn Red Team:
1. Client Authentication: Mọi request bắt buộc có Shared Bearer IPC Token hợp lệ.
   Chế độ Production bắt buộc token non-default (Fail-Closed).
2. Server-side Challenge Nonce Store: Lưu trữ trạng thái Nonce với TTL, Session Binding,
   và cơ chế tiêu thụ 1 lần (One-shot Consume) chống Replay attack.
3. Bounded State & Expiry Cleanup: Tự động dọn dẹp challenge hết hạn trước mỗi thao tác,
   giới hạn dung lượng bộ nhớ tối đa.
4. Receipt Challenge Binding: Ràng buộc chặt chẽ lease_id, session_id, action, receipt_digest
   và danh tính Verifier trong allowlist.
5. Strict Wire Typing (No Coercion): Từ chối hoàn toàn bool, numeric-string, hoặc kiểu sai.
"""

import base64
import json
import os
import secrets
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional, Tuple, Set
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from services.ai_desktop.master_authority_signer import MasterAuthoritySigner, canonical_serialize

DEFAULT_IPC_PORT = 19994
SERVER_IDENTITY = "JKAI_MASTER_AUTHORITY_SIGNER_IPC_V1"
ALLOWED_VERIFIER_IDENTITIES: Set[str] = {"JKAI_MASTER_AUTHORITY_VERIFIER_V1"}
DEFAULT_IPC_TOKEN = "jkai_master_ipc_token_secure_fixed_v1"
MAX_ACTIVE_CHALLENGES = 500


class _MasterAuthorityHTTPHandler(BaseHTTPRequestHandler):
    signer: Optional[MasterAuthoritySigner] = None
    server_identity: str = SERVER_IDENTITY
    ipc_token: str = DEFAULT_IPC_TOKEN
    active_challenges: Dict[str, Dict[str, Any]] = {}
    challenges_lock = threading.Lock()

    def log_message(self, format, *args):
        pass

    def _send_json_resp(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _verify_client_auth(self) -> bool:
        """Kiểm tra xác thực Client qua Authorization header hoặc X-JKAI-IPC-Token."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "X-JKAI-IPC-Token" in self.headers:
            token = self.headers.get("X-JKAI-IPC-Token", "").strip()

        if not token or not secrets.compare_digest(token, self.ipc_token):
            self._send_json_resp(401, {
                "error": "UNAUTHORIZED_IPC_CLIENT",
                "message": "Missing or invalid Master Authority IPC authentication token"
            })
            return False
        return True

    @classmethod
    def _cleanup_expired_challenges(cls, now: float) -> int:
        """Dọn dẹp các challenge đã hết hạn hoặc tiêu thụ, duy trì bounded state."""
        cleaned = 0
        to_delete = []
        for nonce, ch in cls.active_challenges.items():
            if now > ch.get("expires_at", 0) or (ch.get("consumed") and now - ch.get("consumed_at", ch.get("issued_at", 0)) > 10.0):
                to_delete.append(nonce)

        for nonce in to_delete:
            cls.active_challenges.pop(nonce, None)
            cleaned += 1

        # Nếu danh sách vẫn vượt quá MAX_ACTIVE_CHALLENGES, loại bỏ những challenge cũ nhất
        if len(cls.active_challenges) > MAX_ACTIVE_CHALLENGES:
            sorted_keys = sorted(cls.active_challenges.keys(), key=lambda k: cls.active_challenges[k].get("issued_at", 0))
            overflow = len(cls.active_challenges) - MAX_ACTIVE_CHALLENGES
            for k in sorted_keys[:overflow]:
                cls.active_challenges.pop(k, None)
                cleaned += 1

        return cleaned

    def do_GET(self):
        if self.path == "/health":
            now = time.time()
            with self.challenges_lock:
                self._cleanup_expired_challenges(now)
                active_count = len(self.active_challenges)

            self._send_json_resp(200, {
                "status": "ok",
                "server_identity": self.server_identity,
                "signer_pid": os.getpid(),
                "key_id": self.signer.key_id if self.signer else None,
                "fingerprint_sha256": self.signer.fingerprint_sha256 if self.signer else None,
                "active_challenges_count": active_count,
                "max_challenges_capacity": MAX_ACTIVE_CHALLENGES
            })
            return

        self._send_json_resp(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 65536:
            self._send_json_resp(413, {"error": "PAYLOAD_TOO_LARGE"})
            return

        body = self.rfile.read(content_length)
        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json_resp(400, {"error": f"INVALID_JSON: {e}"})
            return

        # 1. Bắt buộc Client Authentication cho toàn bộ các endpoints tác nghiệp
        if not self._verify_client_auth():
            return

        now = time.time()

        # 2. Endpoint cấp phát Challenge Nonce có trạng thái máy chủ
        if self.path == "/authority/challenge":
            session_id = req_data.get("session_id")
            if not isinstance(session_id, str) or not session_id.strip():
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: session_id must be non-empty string"})
                return

            purpose = req_data.get("purpose", "envelope")
            if purpose not in ("envelope", "receipt"):
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: purpose must be 'envelope' or 'receipt'"})
                return

            lease_id = req_data.get("lease_id")
            if lease_id is not None and (not isinstance(lease_id, str) or not lease_id.strip()):
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: lease_id must be string if provided"})
                return

            action = req_data.get("action")
            if action is not None and (not isinstance(action, str) or not action.strip()):
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: action must be string if provided"})
                return

            receipt_digest = req_data.get("receipt_digest")
            if receipt_digest is not None and (not isinstance(receipt_digest, str) or not receipt_digest.strip()):
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: receipt_digest must be string if provided"})
                return

            nonce = secrets.token_hex(16)
            ttl = 60.0

            with self.challenges_lock:
                self._cleanup_expired_challenges(now)
                self.active_challenges[nonce] = {
                    "nonce": nonce,
                    "session_id": session_id,
                    "purpose": purpose,
                    "lease_id": lease_id,
                    "action": action,
                    "receipt_digest": receipt_digest,
                    "issued_at": now,
                    "expires_at": now + ttl,
                    "consumed": False,
                    "consumed_at": None
                }

            self._send_json_resp(200, {
                "status": "CHALLENGE_ISSUED",
                "nonce": nonce,
                "session_id": session_id,
                "purpose": purpose,
                "issued_at": now,
                "ttl_seconds": ttl,
                "server_identity": self.server_identity,
                "signer_pid": os.getpid()
            })
            return

        # 3. Endpoint Ký phát hành Approval Envelope
        if self.path == "/authority/sign_envelope":
            if not self.signer:
                self._send_json_resp(500, {"error": "SIGNER_NOT_INITIALIZED"})
                return

            # A. Strict Wire Typing (Tuyệt đối không ép kiểu Coercion)
            type_rules = {
                "lease_id": lambda v: isinstance(v, str) and len(v) > 0,
                "nonce": lambda v: isinstance(v, str) and len(v) > 0,
                "hwnd": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
                "target_pid": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
                "proc_name": lambda v: isinstance(v, str) and len(v) > 0,
                "action": lambda v: isinstance(v, str) and len(v) > 0,
                "text_payload": lambda v: isinstance(v, str),
                "session_id": lambda v: isinstance(v, str) and len(v) > 0,
                "lease_expires_at": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            }

            for field, validator in type_rules.items():
                if field not in req_data:
                    self._send_json_resp(400, {"error": f"MISSING_FIELD: {field}"})
                    return
                val = req_data[field]
                if not validator(val):
                    self._send_json_resp(400, {
                        "error": f"TYPE_VALIDATION_ERROR: field '{field}' has invalid type {type(val).__name__} (coercion strictly rejected)"
                    })
                    return

            ttl_seconds = req_data.get("ttl_seconds", 60.0)
            if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool):
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: ttl_seconds must be numeric"})
                return

            nonce = req_data["nonce"]
            session_id = req_data["session_id"]
            lease_id = req_data["lease_id"]

            # B. Thẩm thực Server-side Challenge Nonce Store (Chống Giả mạo & Replay)
            with self.challenges_lock:
                self._cleanup_expired_challenges(now)
                challenge = self.active_challenges.get(nonce)
                if not challenge:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_NOT_FOUND_OR_FORGED",
                        "message": f"Nonce '{nonce}' was not issued by Master Authority"
                    })
                    return

                if challenge.get("consumed", False):
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_ALREADY_CONSUMED_REPLAY_DETECTED",
                        "message": f"Nonce '{nonce}' was already consumed (one-shot policy)"
                    })
                    return

                if now > challenge["expires_at"]:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_EXPIRED",
                        "message": f"Nonce '{nonce}' expired at {challenge['expires_at']}"
                    })
                    return

                if challenge["purpose"] != "envelope":
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_PURPOSE_MISMATCH",
                        "message": f"Nonce '{nonce}' was not issued for envelope signing"
                    })
                    return

                if challenge["session_id"] != session_id:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_SESSION_MISMATCH",
                        "message": f"Nonce session mismatch: expected {challenge['session_id']}, got {session_id}"
                    })
                    return

                if challenge.get("lease_id") and challenge["lease_id"] != lease_id:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_LEASE_MISMATCH",
                        "message": f"Nonce lease mismatch: expected {challenge['lease_id']}, got {lease_id}"
                    })
                    return

                # Tiêu thụ ngay lập tức một lần duy nhất (One-shot Consume)
                challenge["consumed"] = True
                challenge["consumed_at"] = now

            # C. Ký phát hành Approval Envelope bằng Private Key
            try:
                envelope_b64 = self.signer.issue_mutation_approval(
                    lease_id=lease_id,
                    nonce=nonce,
                    hwnd=req_data["hwnd"],
                    target_pid=req_data["target_pid"],
                    proc_name=req_data["proc_name"],
                    action=req_data["action"],
                    text_payload=req_data["text_payload"],
                    session_id=session_id,
                    lease_expires_at=float(req_data["lease_expires_at"]),
                    ttl_seconds=float(ttl_seconds)
                )
                self._send_json_resp(200, {
                    "status": "APPROVED",
                    "envelope_b64": envelope_b64,
                    "server_identity": self.server_identity,
                    "signer_pid": os.getpid(),
                    "nonce": nonce
                })
            except Exception as e:
                self._send_json_resp(400, {"error": f"SIGNING_FAILED: {e}"})
            return

        # 4. Endpoint Ký xác thực Execution Receipt (Authenticated Verifier Receipt)
        if self.path == "/authority/sign_receipt":
            if not self.signer:
                self._send_json_resp(500, {"error": "SIGNER_NOT_INITIALIZED"})
                return

            verifier_identity = req_data.get("verifier_identity")
            if verifier_identity not in ALLOWED_VERIFIER_IDENTITIES:
                self._send_json_resp(403, {
                    "error": "UNTRUSTED_VERIFIER_IDENTITY",
                    "message": f"Verifier identity '{verifier_identity}' is not in allowlist"
                })
                return

            receipt_nonce = req_data.get("receipt_nonce")
            if not isinstance(receipt_nonce, str) or not receipt_nonce:
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: receipt_nonce must be string"})
                return

            session_id = req_data.get("session_id")
            if not isinstance(session_id, str) or not session_id:
                self._send_json_resp(400, {"error": "TYPE_VALIDATION_ERROR: session_id must be string"})
                return

            receipt = req_data.get("receipt")
            if not receipt or not isinstance(receipt, dict):
                self._send_json_resp(400, {"error": "MISSING_OR_INVALID_RECEIPT: receipt must be dict"})
                return

            lease_id = req_data.get("lease_id")
            receipt_digest = req_data.get("receipt_digest")

            with self.challenges_lock:
                self._cleanup_expired_challenges(now)
                challenge = self.active_challenges.get(receipt_nonce)
                if not challenge:
                    self._send_json_resp(403, {"error": "CHALLENGE_NOT_FOUND_OR_FORGED"})
                    return
                if challenge.get("consumed", False):
                    self._send_json_resp(403, {"error": "CHALLENGE_ALREADY_CONSUMED_REPLAY_DETECTED"})
                    return
                if now > challenge["expires_at"]:
                    self._send_json_resp(403, {"error": "CHALLENGE_EXPIRED"})
                    return
                if challenge["purpose"] != "receipt":
                    self._send_json_resp(403, {"error": "CHALLENGE_PURPOSE_MISMATCH"})
                    return
                if challenge["session_id"] != session_id:
                    self._send_json_resp(403, {"error": "CHALLENGE_SESSION_MISMATCH"})
                    return

                # Ràng buộc chặt chẽ lease_id, action, receipt_digest chống cross-binding
                if challenge.get("lease_id") and challenge["lease_id"] != lease_id:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_RECEIPT_BINDING_MISMATCH",
                        "message": f"Lease ID mismatch: expected {challenge['lease_id']}, got {lease_id}"
                    })
                    return

                if challenge.get("action") and challenge["action"] != receipt.get("action"):
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_RECEIPT_BINDING_MISMATCH",
                        "message": f"Action mismatch: expected {challenge['action']}, got {receipt.get('action')}"
                    })
                    return

                if challenge.get("receipt_digest") and challenge["receipt_digest"] != receipt_digest:
                    self._send_json_resp(403, {
                        "error": "CHALLENGE_RECEIPT_BINDING_MISMATCH",
                        "message": f"Receipt digest mismatch: expected {challenge['receipt_digest']}, got {receipt_digest}"
                    })
                    return

                # Tiêu thụ nonce
                challenge["consumed"] = True
                challenge["consumed_at"] = now

            try:
                authenticated_record = {
                    "receipt": receipt,
                    "receipt_nonce": receipt_nonce,
                    "verifier_identity": verifier_identity,
                    "session_id": session_id,
                    "lease_id": lease_id,
                    "signed_at": now
                }
                canonical_bytes = canonical_serialize(authenticated_record)
                sig_bytes = self.signer._private_key.sign(canonical_bytes)
                sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")
                self._send_json_resp(200, {
                    "status": "RECEIPT_SIGNED",
                    "receipt_signature_b64": sig_b64,
                    "authenticated_record": authenticated_record,
                    "key_id": self.signer.key_id,
                    "signer_identity": self.server_identity,
                    "signer_pid": os.getpid()
                })
            except Exception as e:
                self._send_json_resp(400, {"error": f"RECEIPT_SIGNING_FAILED: {e}"})
            return

        self._send_json_resp(404, {"error": "NOT_FOUND"})


class MasterAuthorityIPCServer:
    """
    HTTP Server độc lập cung cấp dịch vụ ký số Thẩm quyền Master qua IPC.
    Chạy trong tiến trình riêng biệt bảo vệ Private Key.
    """

    def __init__(
        self,
        port: int = DEFAULT_IPC_PORT,
        key_path: Optional[str] = None,
        ipc_token: Optional[str] = None
    ):
        self.port = port
        self.key_path = key_path

        # Production Guard: Bắt buộc non-default token ở chế độ production
        is_test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"
        chosen_token = ipc_token or os.getenv("JKAI_AUTHORITY_IPC_TOKEN") or DEFAULT_IPC_TOKEN

        if not is_test_mode and (not chosen_token or chosen_token == DEFAULT_IPC_TOKEN):
            raise RuntimeError(
                "FAIL_CLOSED: Production Master Authority requires non-default, cryptographically random IPC token from secure store/env (JKAI_MUTATION_TEST_MODE=0)"
            )

        self.ipc_token = chosen_token
        self.signer = MasterAuthoritySigner(key_path=key_path)

        class CustomHandler(_MasterAuthorityHTTPHandler):
            pass

        CustomHandler.signer = self.signer
        CustomHandler.ipc_token = self.ipc_token
        CustomHandler.active_challenges = {}
        self.httpd = HTTPServer(("127.0.0.1", self.port), CustomHandler)
        self._thread: Optional[threading.Thread] = None

    def start_background(self):
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.1)

    def shutdown(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass


class MasterAuthorityIPCClient:
    """
    Client chạy trong tiến trình Worker / Pilot.
    HOÀN TOÀN KHÔNG CÓ PRIVATE KEY.
    Tương tác với Signer Process qua loopback IPC với Bearer Token & Nonce Challenge.
    """

    def __init__(
        self,
        base_url: str = f"http://127.0.0.1:{DEFAULT_IPC_PORT}",
        ipc_token: str = DEFAULT_IPC_TOKEN
    ):
        self.base_url = base_url.rstrip("/")
        self.ipc_token = ipc_token

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ipc_token}"
        }

    def get_server_health(self) -> Dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def request_challenge(
        self,
        session_id: str = "default_session",
        purpose: str = "envelope",
        lease_id: Optional[str] = None,
        action: Optional[str] = None,
        receipt_digest: Optional[str] = None
    ) -> str:
        """Gửi yêu cầu sinh Challenge Nonce có trạng thái từ Master Authority Service."""
        payload: Dict[str, Any] = {
            "session_id": session_id,
            "purpose": purpose
        }
        if lease_id:
            payload["lease_id"] = lease_id
        if action:
            payload["action"] = action
        if receipt_digest:
            payload["receipt_digest"] = receipt_digest

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/authority/challenge",
            data=body,
            headers=self._auth_headers()
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["nonce"]

    def request_envelope(
        self,
        lease_id: str,
        nonce: str,
        hwnd: int,
        target_pid: int,
        proc_name: str,
        action: str,
        text_payload: str,
        session_id: str,
        lease_expires_at: float,
        ttl_seconds: float = 60.0
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Gửi yêu cầu ký phát hành Approval Envelope qua Authenticated IPC."""
        body = json.dumps({
            "lease_id": lease_id,
            "nonce": nonce,
            "hwnd": hwnd,
            "target_pid": target_pid,
            "proc_name": proc_name,
            "action": action,
            "text_payload": text_payload,
            "session_id": session_id,
            "lease_expires_at": lease_expires_at,
            "ttl_seconds": ttl_seconds
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/authority/sign_envelope",
            data=body,
            headers=self._auth_headers()
        )

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return True, data.get("envelope_b64", ""), data
        except urllib.error.HTTPError as e:
            err_data = {}
            try:
                err_data = json.loads(e.read().decode("utf-8"))
            except Exception:
                pass
            return False, "", {"status_code": e.code, "detail": err_data}
        except Exception as e:
            return False, "", {"error": f"CLIENT_EXCEPTION: {e}"}

    def request_receipt_signature(
        self,
        receipt: Dict[str, Any],
        receipt_nonce: str,
        session_id: str,
        lease_id: Optional[str] = None,
        receipt_digest: Optional[str] = None,
        verifier_identity: str = "JKAI_MASTER_AUTHORITY_VERIFIER_V1"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Yêu cầu ký xác thực Authenticated Execution Receipt qua IPC."""
        body = json.dumps({
            "receipt": receipt,
            "receipt_nonce": receipt_nonce,
            "session_id": session_id,
            "lease_id": lease_id,
            "receipt_digest": receipt_digest,
            "verifier_identity": verifier_identity
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/authority/sign_receipt",
            data=body,
            headers=self._auth_headers()
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return True, data.get("receipt_signature_b64", ""), data
        except urllib.error.HTTPError as e:
            err_data = {}
            try:
                err_data = json.loads(e.read().decode("utf-8"))
            except Exception:
                pass
            return False, "", {"status_code": e.code, "detail": err_data}
        except Exception as e:
            return False, "", {"error": f"CLIENT_EXCEPTION: {e}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Master Authority IPC Service")
    parser.add_argument("--port", type=int, default=DEFAULT_IPC_PORT, help="Port to bind")
    parser.add_argument("--key-path", type=str, default=None, help="Path to secret key JSON")
    parser.add_argument("--ipc-token", type=str, default=None, help="Shared Bearer Token")
    args = parser.parse_args()

    # Mặc định trong test environment thì set test mode nếu chưa có
    token = args.ipc_token or os.getenv("JKAI_AUTHORITY_IPC_TOKEN") or DEFAULT_IPC_TOKEN
    print(f"[SIGNER_IPC] Starting Master Authority IPC Server on port {args.port} (PID: {os.getpid()})...")
    server = MasterAuthorityIPCServer(port=args.port, key_path=args.key_path, ipc_token=token)
    try:
        server.httpd.serve_forever()
    except KeyboardInterrupt:
        print("[SIGNER_IPC] Shutting down server...")
        server.shutdown()
