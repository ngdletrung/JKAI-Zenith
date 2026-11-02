# -*- coding: utf-8 -*-
"""
tests/test_signer_verifier_process_separation.py
[JKAI RED TEAM AUDIT - PROCESS SEPARATION & AUTHENTICATED IPC HARDENED TESTS]

Tuân thủ toàn bộ 6 điều kiện sửa bắt buộc từ LƯỢT 325 của OpenCode Red Team Auditor:
1. Server-side Nonce Challenge Store: Lưu TTL, session binding, one-shot consume policy.
2. Signer Server từ chối ký request có nonce giả hoặc nonce replay (HTTP 403) trước khi ký.
3. Authenticated Verifier Receipt: Yêu cầu challenge riêng, verifier identity allowlist, session binding.
4. Client Authentication: Bắt buộc Bearer IPC Token hợp lệ; reject unauthorized (HTTP 401).
5. Strict Wire Typing: Từ chối hoàn toàn bool, numeric-string coercion (HTTP 400).
6. Physical Process Separation: Signer OS Subprocess độc lập (PID khác biệt), Verifier không có Private Key.
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import pytest

from services.ai_desktop.master_authority_ipc import (
    MasterAuthorityIPCClient,
    DEFAULT_IPC_TOKEN
)
from services.ai_desktop.master_authority_verifier import MasterAuthorityVerifier
from cryptography.hazmat.primitives.asymmetric import ed25519

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_IPC_PORT = 19992
TEST_IPC_TOKEN = "test_bearer_token_secret_32_bytes_ok"


@pytest.fixture(scope="module")
def independent_signer_subprocess():
    """Khởi chạy Master Authority Signer trong một OS Subprocess hoàn toàn tách biệt."""
    cmd = [
        sys.executable,
        "-m",
        "services.ai_desktop.master_authority_ipc",
        "--port",
        str(TEST_IPC_PORT),
        "--ipc-token",
        TEST_IPC_TOKEN
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "JKAI_MUTATION_TEST_MODE": "1"},
        text=True
    )
    # Chờ server khởi động
    client = MasterAuthorityIPCClient(
        base_url=f"http://127.0.0.1:{TEST_IPC_PORT}",
        ipc_token=TEST_IPC_TOKEN
    )
    max_wait = 10.0
    start = time.time()
    server_ready = False
    while time.time() - start < max_wait:
        try:
            health = client.get_server_health()
            if health.get("status") == "ok":
                server_ready = True
                break
        except Exception:
            time.sleep(0.2)

    assert server_ready, f"Signer subprocess không thể khởi động trên cổng {TEST_IPC_PORT}"
    yield client, proc.pid

    # Dọn dẹp tiến trình
    proc.terminate()
    try:
        proc.wait(timeout=3.0)
    except Exception:
        proc.kill()


def test_process_separation_independent_pid(independent_signer_subprocess):
    """Chứng minh Signer chạy ở PID độc lập so với tiến trình hiện tại (Verifier/Test)."""
    client, signer_pid = independent_signer_subprocess
    current_pid = os.getpid()

    health = client.get_server_health()
    assert health["signer_pid"] == signer_pid
    assert signer_pid != current_pid, f"Signer PID ({signer_pid}) phải khác Test/Verifier PID ({current_pid})"
    assert health["key_id"] == "master_primary_v1"
    assert health["status"] == "ok"


def test_server_rejects_unauthorized_ipc_client(independent_signer_subprocess):
    """Mục 4: IPC Server từ chối mọi request không có Token hoặc Token sai (HTTP 401)."""
    # Tạo client với token giả mạo
    bad_client = MasterAuthorityIPCClient(
        base_url=f"http://127.0.0.1:{TEST_IPC_PORT}",
        ipc_token="invalid_rogue_token"
    )

    now = time.time()
    ok, envelope, resp = bad_client.request_envelope(
        lease_id="lease_unauth",
        nonce="any_nonce",
        hwnd=111,
        target_pid=222,
        proc_name="notepad.exe",
        action="type_text",
        text_payload="test",
        session_id="sess_unauth",
        lease_expires_at=now + 60.0
    )
    assert ok is False
    assert resp.get("status_code") == 401
    assert "UNAUTHORIZED_IPC_CLIENT" in resp.get("detail", {}).get("error", "")


def test_authenticated_ipc_nonce_challenge_end_to_end(independent_signer_subprocess):
    """Mục 1 & 2: Quy trình thẩm thực IPC end-to-end có Server-side Challenge Nonce và tiêu thụ 1 lần."""
    client, signer_pid = independent_signer_subprocess
    verifier = MasterAuthorityVerifier()

    session_id = "session_ipc_test_e2e"
    # 1. Lấy Challenge Nonce từ Server (có session binding)
    challenge_nonce = client.request_challenge(session_id=session_id, purpose="envelope")
    assert len(challenge_nonce) == 32

    # 2. Gửi yêu cầu ký phong bì kèm Nonce
    now = time.time()
    lease_expires = now + 120.0
    ok, envelope_b64, resp = client.request_envelope(
        lease_id="lease_ipc_001",
        nonce=challenge_nonce,
        hwnd=123456,
        target_pid=7788,
        proc_name="notepad.exe",
        action="type_text",
        text_payload="JKAI Authenticated IPC Test",
        session_id=session_id,
        lease_expires_at=lease_expires,
        ttl_seconds=60.0
    )
    assert ok is True
    assert envelope_b64 != ""
    assert resp["signer_pid"] == signer_pid

    # 3. Verifier thẩm định với Pinned Public Key & Nonce Challenge
    v_ok, v_reason, audit = verifier.verify_approval_token(
        approval_envelope_b64=envelope_b64,
        expected_action="type_text",
        expected_hwnd=123456,
        expected_target_pid=7788,
        expected_proc_name="notepad.exe",
        expected_text="JKAI Authenticated IPC Test",
        expected_session_id=session_id,
        expected_lease_id="lease_ipc_001",
        expected_nonce=challenge_nonce
    )
    assert v_ok is True
    assert v_reason == "MASTER_AUTHORITY_VERIFIED_PASS"
    assert audit["master_key_id"] == "master_primary_v1"


def test_server_rejects_unissued_or_forged_nonce(independent_signer_subprocess):
    """Mục 2 & 6: Signer Server từ chối ký request mang Nonce giả mạo (chưa từng được Server cấp) (HTTP 403)."""
    client, _ = independent_signer_subprocess
    forged_nonce = "deadbeef" * 4

    now = time.time()
    ok, envelope_b64, resp = client.request_envelope(
        lease_id="lease_forged",
        nonce=forged_nonce,
        hwnd=1111,
        target_pid=2222,
        proc_name="notepad.exe",
        action="type_text",
        text_payload="Test Forgery",
        session_id="sess_forged",
        lease_expires_at=now + 120.0
    )
    assert ok is False
    assert resp.get("status_code") == 403
    assert resp.get("detail", {}).get("error") == "CHALLENGE_NOT_FOUND_OR_FORGED"


def test_server_rejects_replayed_nonce_one_shot(independent_signer_subprocess):
    """Mục 2 & 6: Signer Server từ chối ký request tái sử dụng Nonce đã tiêu thụ (One-shot Consume) (HTTP 403)."""
    client, _ = independent_signer_subprocess
    session_id = "sess_replay_test"

    nonce = client.request_challenge(session_id=session_id, purpose="envelope")

    now = time.time()
    # Lần 1: Ký thành công và tiêu thụ nonce
    ok1, env1, resp1 = client.request_envelope(
        lease_id="lease_replay_1",
        nonce=nonce,
        hwnd=1111,
        target_pid=2222,
        proc_name="notepad.exe",
        action="type_text",
        text_payload="First Usage",
        session_id=session_id,
        lease_expires_at=now + 120.0
    )
    assert ok1 is True
    assert env1 != ""

    # Lần 2: Tái sử dụng cùng nonce -> Server reject ngay lập tức trước khi ký!
    ok2, env2, resp2 = client.request_envelope(
        lease_id="lease_replay_2",
        nonce=nonce,
        hwnd=1111,
        target_pid=2222,
        proc_name="notepad.exe",
        action="type_text",
        text_payload="Second Replay Usage",
        session_id=session_id,
        lease_expires_at=now + 120.0
    )
    assert ok2 is False
    assert resp2.get("status_code") == 403
    assert resp2.get("detail", {}).get("error") == "CHALLENGE_ALREADY_CONSUMED_REPLAY_DETECTED"


def test_server_rejects_wire_coercion(independent_signer_subprocess):
    """Mục 5: Signer Server từ chối hoàn toàn bool hoặc numeric string tại ranh giới IPC (HTTP 400)."""
    client, _ = independent_signer_subprocess
    session_id = "sess_type_test"
    nonce = client.request_challenge(session_id=session_id, purpose="envelope")

    # Gửi raw payload vi phạm typing: hwnd là string "1234" thay vì int
    bad_payload = {
        "lease_id": "lease_type",
        "nonce": nonce,
        "hwnd": "12345",  # VI PHẠM: numeric string thay vì int
        "target_pid": 2222,
        "proc_name": "notepad.exe",
        "action": "type_text",
        "text_payload": "test",
        "session_id": session_id,
        "lease_expires_at": time.time() + 60.0
    }
    req = urllib.request.Request(
        f"{client.base_url}/authority/sign_envelope",
        data=json.dumps(bad_payload).encode("utf-8"),
        headers=client._auth_headers()
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Phải fail với HTTP 400 vì hwnd là string"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        data = json.loads(e.read().decode("utf-8"))
        assert "TYPE_VALIDATION_ERROR" in data.get("error", "")

    # Gửi raw payload vi phạm typing: target_pid là boolean True
    nonce2 = client.request_challenge(session_id=session_id, purpose="envelope")
    bad_payload2 = {
        "lease_id": "lease_type",
        "nonce": nonce2,
        "hwnd": 12345,
        "target_pid": True,  # VI PHẠM: bool thay vì int
        "proc_name": "notepad.exe",
        "action": "type_text",
        "text_payload": "test",
        "session_id": session_id,
        "lease_expires_at": time.time() + 60.0
    }
    req2 = urllib.request.Request(
        f"{client.base_url}/authority/sign_envelope",
        data=json.dumps(bad_payload2).encode("utf-8"),
        headers=client._auth_headers()
    )
    try:
        urllib.request.urlopen(req2)
        assert False, "Phải fail với HTTP 400 vì target_pid là bool"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        data = json.loads(e.read().decode("utf-8"))
        assert "TYPE_VALIDATION_ERROR" in data.get("error", "")


def test_server_rejects_unauthorized_receipt_signing(independent_signer_subprocess):
    """Mục 3 & 6: Server từ chối ký receipt nếu verifier identity lạ hoặc nonce receipt không hợp lệ."""
    client, _ = independent_signer_subprocess
    session_id = "sess_receipt_unauth"

    receipt = {"action": "type_text", "status": "CONFIRMED"}

    # 1. Thử ký với Verifier Identity không nằm trong Allowlist (HTTP 403)
    ok, _, resp = client.request_receipt_signature(
        receipt=receipt,
        receipt_nonce="any_nonce",
        session_id=session_id,
        verifier_identity="ROGUE_UNTRUSTED_VERIFIER_V99"
    )
    assert ok is False
    assert resp.get("status_code") == 403
    assert resp.get("detail", {}).get("error") == "UNTRUSTED_VERIFIER_IDENTITY"

    # 2. Thử ký với Nonce giả mạo (HTTP 403)
    ok2, _, resp2 = client.request_receipt_signature(
        receipt=receipt,
        receipt_nonce="forged_receipt_nonce",
        session_id=session_id,
        verifier_identity="JKAI_MASTER_AUTHORITY_VERIFIER_V1"
    )
    assert ok2 is False
    assert resp2.get("status_code") == 403
    assert resp2.get("detail", {}).get("error") == "CHALLENGE_NOT_FOUND_OR_FORGED"


def test_authenticated_verifier_receipt_channel(independent_signer_subprocess):
    """Mục 3: Kênh Authenticated Verifier Receipt hoàn chỉnh với Receipt Challenge và Verifier Allowlist."""
    client, _ = independent_signer_subprocess
    verifier = MasterAuthorityVerifier()
    session_id = "sess_receipt_valid"

    # 1. Lấy Challenge riêng cho receipt signing
    receipt_nonce = client.request_challenge(session_id=session_id, purpose="receipt")

    receipt = {
        "action": "type_text",
        "hwnd": 123456,
        "proc_name": "notepad.exe",
        "text_typed": "Receipt Verification Test",
        "dispatched_at": time.time(),
        "status": "DISPATCH_CONFIRMED"
    }

    # 2. Ký xác thực receipt qua Authenticated IPC
    ok, sig_b64, resp = client.request_receipt_signature(
        receipt=receipt,
        receipt_nonce=receipt_nonce,
        session_id=session_id,
        verifier_identity="JKAI_MASTER_AUTHORITY_VERIFIER_V1"
    )
    assert ok is True
    assert sig_b64 != ""
    assert resp["key_id"] == "master_primary_v1"

    # 3. Thẩm định chữ ký của Receipt bằng Pinned Public Key của Verifier
    pinned_meta = verifier._trusted_keys["master_primary_v1"]
    ed_pub = pinned_meta["ed25519_obj"]

    from services.ai_desktop.master_authority_signer import canonical_serialize
    authenticated_record = resp["authenticated_record"]
    canonical_bytes = canonical_serialize(authenticated_record)
    raw_sig = base64.b64decode(sig_b64)
    # Xác thực chữ ký số Ed25519 thành công
    ed_pub.verify(raw_sig, canonical_bytes)


def test_verifier_process_has_no_private_key():
    """Mục 6: Chứng minh Verifier Process không thể ký phong bì vì không chứa Private Key."""
    verifier = MasterAuthorityVerifier()
    assert not hasattr(verifier, "_private_key")
    assert not hasattr(verifier, "private_key_b64")
    for k, v in verifier._trusted_keys.items():
        assert isinstance(v["ed25519_obj"], ed25519.Ed25519PublicKey)


def test_expired_challenges_cleaned_up_bounded_state():
    """Lượt 327 Finding 1: Thẩm định cơ chế dọn dẹp TTL và bảo đảm bounded state."""
    from services.ai_desktop.master_authority_ipc import _MasterAuthorityHTTPHandler, MAX_ACTIVE_CHALLENGES

    # Giả lập nạp challenge hết hạn và challenge còn hạn
    now = time.time()
    test_challenges = {
        "expired_nonce_1": {"issued_at": now - 120.0, "expires_at": now - 60.0, "consumed": False},
        "expired_nonce_2": {"issued_at": now - 100.0, "expires_at": now - 40.0, "consumed": False},
        "consumed_old_nonce": {"issued_at": now - 80.0, "expires_at": now + 10.0, "consumed": True, "consumed_at": now - 20.0},
        "valid_nonce_active": {"issued_at": now, "expires_at": now + 60.0, "consumed": False}
    }

    _MasterAuthorityHTTPHandler.active_challenges = test_challenges.copy()
    cleaned = _MasterAuthorityHTTPHandler._cleanup_expired_challenges(now)

    assert cleaned >= 3
    assert "expired_nonce_1" not in _MasterAuthorityHTTPHandler.active_challenges
    assert "expired_nonce_2" not in _MasterAuthorityHTTPHandler.active_challenges
    assert "consumed_old_nonce" not in _MasterAuthorityHTTPHandler.active_challenges
    assert "valid_nonce_active" in _MasterAuthorityHTTPHandler.active_challenges
    assert len(_MasterAuthorityHTTPHandler.active_challenges) <= MAX_ACTIVE_CHALLENGES


def test_production_mode_rejects_default_ipc_token(monkeypatch):
    """Lượt 327 Finding 2: Chế độ Production (JKAI_MUTATION_TEST_MODE != 1) fail-closed nếu dùng DEFAULT_IPC_TOKEN."""
    from services.ai_desktop.master_authority_ipc import MasterAuthorityIPCServer, DEFAULT_IPC_TOKEN

    monkeypatch.setenv("JKAI_MUTATION_TEST_MODE", "0")
    with pytest.raises(RuntimeError, match="FAIL_CLOSED: Production Master Authority requires non-default"):
        MasterAuthorityIPCServer(port=19991, ipc_token=DEFAULT_IPC_TOKEN)


def test_receipt_challenge_cross_lease_mismatch_rejected(independent_signer_subprocess):
    """Lượt 327 Finding 3: Server từ chối ký receipt nếu lease_id hoặc action không khớp với challenge đã cấp."""
    client, _ = independent_signer_subprocess
    session_id = "sess_cross_lease_test"

    # Cấp challenge gắn chặt với lease_id "lease_TARGET_001"
    receipt_nonce = client.request_challenge(
        session_id=session_id,
        purpose="receipt",
        lease_id="lease_TARGET_001",
        action="type_text"
    )

    receipt = {
        "action": "type_text",
        "hwnd": 123456,
        "proc_name": "notepad.exe",
        "text_typed": "Cross Lease Test",
        "status": "DISPATCH_CONFIRMED"
    }

    # Thử gửi với lease_id khác ("lease_ROGUE_999") -> Server phải reject với HTTP 403
    ok, _, resp = client.request_receipt_signature(
        receipt=receipt,
        receipt_nonce=receipt_nonce,
        session_id=session_id,
        lease_id="lease_ROGUE_999",  # MISMATCH
        verifier_identity="JKAI_MASTER_AUTHORITY_VERIFIER_V1"
    )
    assert ok is False
    assert resp.get("status_code") == 403
    assert resp.get("detail", {}).get("error") == "CHALLENGE_RECEIPT_BINDING_MISMATCH"

