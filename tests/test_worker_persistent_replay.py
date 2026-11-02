# -*- coding: utf-8 -*-
import os
import time
import pytest
from scripts.host_mutation_worker import HostMutationWorker
from scripts.master_approval_signer import MasterApprovalSigner

def test_worker_rejects_replay_after_worker_restart(tmp_path, monkeypatch):
    """
    Chứng minh khả năng bảo vệ chống Replay Attack xuyên suốt các lần Worker khởi động lại (Crash/Restart).
    """
    priv_b64, pub_b64 = MasterApprovalSigner.generate_keypair()
    os.environ["JKAI_MASTER_PUBLIC_KEY"] = pub_b64
    os.environ["JKAI_MUTATION_ENABLED"] = "0"
    os.environ["JKAI_MUTATION_SECRET"] = "persistent_test_secret_32_characters"

    signer = MasterApprovalSigner(private_key_b64=priv_b64)

    # Worker Thế hệ 1 (Worker Generation A)
    worker_a = HostMutationWorker()
    worker_a.nonce_store.clear_all_for_test()

    mock_state = {
        "hwnd": 77777,
        "valid": True,
        "target_pid": 1111,
        "proc_name": "notepad.exe",
        "class_name": "Notepad",
        "window_title": "Untitled - Notepad",
        "bounds": [100, 100, 600, 500],
        "is_minimized": False,
        "is_foreground": True
    }
    monkeypatch.setattr(worker_a.target_validator, "get_window_identity", lambda hwnd: mock_state)
    monkeypatch.setattr(worker_a, "_verify_target_allowed", lambda hwnd, action, text, element_ref="", *a, **k: (1111, "notepad.exe"))

    auth_token = signer.create_master_auth_token(session_id="session_persist_01", ttl_seconds=30.0)

    # 1. Cấp vé trên Worker A
    lease = worker_a.request_one_time_lease(
        hwnd=77777,
        action="type",
        expected_session_id="session_persist_01",
        text_payload="Safe Text",
        master_auth_token=auth_token
    )

    approval_sig = signer.sign_mutation_approval(
        lease_id=lease["lease_id"],
        nonce=lease["nonce"],
        hwnd=77777,
        target_pid=1111,
        proc_name="notepad.exe",
        action="type",
        text_payload="Safe Text",
        worker_generation=worker_a.worker_generation,
        lease_expires_at=lease["expires_at"],
        session_id="session_persist_01"
    )

    # 2. Worker A thực thi thành công (Dry-run)
    res_a = worker_a.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig
    )
    assert res_a["status"] in ("BLOCKED_BY_DEFAULT", "MUTATION_DISABLED_DRY_RUN")

    # 3. Giả lập Worker A bị Crash và Worker B được khởi động lại (Worker Generation B)
    worker_b = HostMutationWorker()
    monkeypatch.setattr(worker_b.target_validator, "get_window_identity", lambda hwnd: mock_state)
    monkeypatch.setattr(worker_b, "_verify_target_allowed", lambda hwnd, action, text, element_ref="", *a, **k: (1111, "notepad.exe"))

    # Giả lập kẻ tấn công inject lại lease_id và approval_sig vào Worker B
    # Gán lease vào bộ nhớ Worker B để kiểm tra chốt chặn Persistent Anti-Replay
    worker_b._active_leases[lease["lease_id"]] = {
        "lease_id": lease["lease_id"],
        "nonce": lease["nonce"],
        "hwnd": 77777,
        "pid": 1111,
        "proc_name": "notepad.exe",
        "action": "type",
        "text_payload": "Safe Text",
        "expires_at": time.time() + 30.0,
        "signature": lease["signature"],
        "consumed": False, # Giả mạo unconsumed
        "worker_generation": worker_b.worker_generation, # Giả mạo generation
        "session_id": "session_persist_01",
        "target_identity": mock_state
    }

    res_b = worker_b.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig
    )

    # Phải bị chặn đứng bởi Persistent Anti-Replay!
    assert res_b["status"] == "BLOCKED"
    assert res_b["receipt"] == "REPLAY_ATTACK_DETECTED"

def test_worker_rejects_target_identity_drift(monkeypatch):
    """
    Chứng minh Worker chặn đứng hành vi tráo đổi cửa sổ hoặc thu nhỏ ngầm (Target Identity Drift).
    """
    priv_b64, pub_b64 = MasterApprovalSigner.generate_keypair()
    os.environ["JKAI_MASTER_PUBLIC_KEY"] = pub_b64
    os.environ["JKAI_MUTATION_ENABLED"] = "0"
    os.environ["JKAI_MUTATION_SECRET"] = "persistent_test_secret_32_characters"

    signer = MasterApprovalSigner(private_key_b64=priv_b64)
    worker = HostMutationWorker()
    worker.nonce_store.clear_all_for_test()

    mock_state = {
        "hwnd": 88888,
        "valid": True,
        "target_pid": 2222,
        "proc_name": "notepad.exe",
        "class_name": "Notepad",
        "window_title": "Original Notepad",
        "bounds": [100, 100, 600, 500],
        "is_minimized": False,
        "is_foreground": True
    }
    monkeypatch.setattr(worker.target_validator, "get_window_identity", lambda hwnd: mock_state)
    monkeypatch.setattr(worker, "_verify_target_allowed", lambda hwnd, action, text, element_ref="", *a, **k: (2222, "notepad.exe"))

    auth_token = signer.create_master_auth_token(session_id="sess_drift", ttl_seconds=30.0)

    lease = worker.request_one_time_lease(
        hwnd=88888,
        action="type",
        expected_session_id="sess_drift",
        text_payload="Drift Test",
        master_auth_token=auth_token
    )

    approval_sig = signer.sign_mutation_approval(
        lease_id=lease["lease_id"],
        nonce=lease["nonce"],
        hwnd=88888,
        target_pid=2222,
        proc_name="notepad.exe",
        action="type",
        text_payload="Drift Test",
        worker_generation=worker.worker_generation,
        lease_expires_at=lease["expires_at"],
        session_id="sess_drift"
    )

    # Giả lập cửa sổ bị trôi dạt: bị thu nhỏ (is_minimized = True) trước khi bấm phím
    mock_state_drifted = dict(mock_state)
    mock_state_drifted["is_minimized"] = True
    monkeypatch.setattr(worker.target_validator, "get_window_identity", lambda hwnd: mock_state_drifted)

    res = worker.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig
    )

    assert res["status"] == "BLOCKED"
    assert res["receipt"] == "TARGET_IDENTITY_DRIFT"
    assert "TARGET_IS_MINIMIZED" in res["reason"]

def test_preflight_does_not_consume_nonce_and_allows_execution(monkeypatch):
    """
    Chứng minh Preflight Authorization tách rời hoàn toàn: có thể gọi nhiều lần mà không làm tiêu thụ nonce,
    và lượt execute sau đó vẫn tiêu thụ nonce an toàn và chính xác.
    """
    priv_b64, pub_b64 = MasterApprovalSigner.generate_keypair()
    os.environ["JKAI_MASTER_PUBLIC_KEY"] = pub_b64
    os.environ["JKAI_MUTATION_ENABLED"] = "0"
    os.environ["JKAI_MUTATION_SECRET"] = "persistent_test_secret_32_characters"

    signer = MasterApprovalSigner(private_key_b64=priv_b64)
    worker = HostMutationWorker()
    worker.nonce_store.clear_all_for_test()

    mock_state = {
        "hwnd": 99991,
        "valid": True,
        "target_pid": 5555,
        "proc_name": "notepad.exe",
        "class_name": "Notepad",
        "window_title": "Preflight Test",
        "bounds": [100, 100, 500, 400],
        "is_minimized": False,
        "is_foreground": True
    }
    monkeypatch.setattr(worker.target_validator, "get_window_identity", lambda hwnd: mock_state)
    monkeypatch.setattr(worker, "_verify_target_allowed", lambda hwnd, action, text, element_ref="", *a, **k: (5555, "notepad.exe"))

    auth_token = signer.create_master_auth_token(session_id="sess_preflight", ttl_seconds=30.0)

    lease = worker.request_one_time_lease(
        hwnd=99991,
        action="type",
        expected_session_id="sess_preflight",
        text_payload="Preflight Payload",
        master_auth_token=auth_token
    )

    approval_sig = signer.sign_mutation_approval(
        lease_id=lease["lease_id"],
        nonce=lease["nonce"],
        hwnd=99991,
        target_pid=5555,
        proc_name="notepad.exe",
        action="type",
        text_payload="Preflight Payload",
        worker_generation=worker.worker_generation,
        lease_expires_at=lease["expires_at"],
        session_id="sess_preflight"
    )

    # 1. Preflight Lần 1: Thành công
    ok1, reason1, lease_data1 = worker.preflight_verify_authorization(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig
    )
    assert ok1 is True
    assert reason1 == "PREFLIGHT_AUTH_PASSED"

    # 2. Preflight Lần 2: Bị chặn (lease đã có chủ preflight) nhưng KHÔNG tiêu thụ nonce
    ok2, reason2, lease_data2 = worker.preflight_verify_authorization(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig
    )
    assert ok2 is False
    assert reason2 == "LEASE_ALREADY_PREFLIGHT_LOCKED"
    assert worker.nonce_store.is_nonce_used(f"worker_exec_{lease['nonce']}") is False

    owner = lease_data1["preflight_owner_token"]

    # 2.1. Execute sai owner token -> chặn, vé vẫn còn nguyên
    res_wrong_owner = worker.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig,
        owner_token="not_the_owner"
    )
    assert res_wrong_owner["receipt"] == "PREFLIGHT_OWNER_MISMATCH"

    # 2.2. Gắn before-snapshot: chỉ owner được gắn, chỉ một lần
    assert worker.attach_before_snapshot(lease["lease_id"], "not_the_owner", "h1")[1] == "PREFLIGHT_OWNER_MISMATCH"
    assert worker.attach_before_snapshot(lease["lease_id"], owner, "h1") == (True, "BEFORE_SNAPSHOT_ATTACHED")
    assert worker.attach_before_snapshot(lease["lease_id"], owner, "h2")[1] == "BEFORE_SNAPSHOT_ALREADY_ATTACHED"

    # 2.3. Execute đúng owner nhưng sai snapshot hash -> chặn
    res_wrong_snap = worker.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig,
        owner_token=owner,
        before_snapshot_hash="h2"
    )
    assert res_wrong_snap["receipt"] == "BEFORE_SNAPSHOT_MISMATCH"

    # 3. Execute đúng owner + đúng snapshot: Tiêu thụ nonce và hoàn tất hành động
    res_exec = worker.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig,
        owner_token=owner,
        before_snapshot_hash="h1"
    )
    assert res_exec["status"] in ("BLOCKED_BY_DEFAULT", "MUTATION_DISABLED_DRY_RUN")

    # 4. Execute Lần 2: BỊ TỪ CHỐI REPLAY ATTACK
    res_replay = worker.execute_with_lease(
        lease_id=lease["lease_id"],
        signature=lease["signature"],
        master_approval_signature=approval_sig,
        owner_token=owner,
        before_snapshot_hash="h1"
    )
    assert res_replay["status"] == "BLOCKED"
    assert res_replay["receipt"] == "REPLAY_ATTACK_DETECTED"

def test_master_auth_token_persistent_replay_across_restarts():
    """
    Chứng minh Master Auth Token (Tầng 1) với scope master_auth được bảo vệ chống Replay Attack
    ngay cả khi Verifier được khởi tạo lại (mô phỏng process restart).
    """
    from scripts.master_approval_verifier import MasterApprovalVerifier

    priv_b64, pub_b64 = MasterApprovalSigner.generate_keypair()
    os.environ["JKAI_MASTER_PUBLIC_KEY"] = pub_b64
    signer = MasterApprovalSigner(private_key_b64=priv_b64)

    # Verifier Thế hệ 1
    verifier1 = MasterApprovalVerifier(public_key_b64=pub_b64)
    verifier1._nonce_store.clear_all_for_test()

    token = signer.create_master_auth_token(session_id="sess_auth_persist", ttl_seconds=30.0)

    # Lần 1: Hợp lệ
    ok1, reason1, payload1 = verifier1.verify_master_auth_token(token, expected_session_id="sess_auth_persist")
    assert ok1 is True
    assert reason1 == "TOKEN_VALID"

    # Verifier Thế hệ 2 (Restart instance mới kết nối cùng Persistent Nonce DB)
    verifier2 = MasterApprovalVerifier(public_key_b64=pub_b64)

    # Lần 2 trên instance mới: Phải bị chặn đứng REPLAY_AUTH_TOKEN_DETECTED
    ok2, reason2, payload2 = verifier2.verify_master_auth_token(token, expected_session_id="sess_auth_persist")
    assert ok2 is False
    assert reason2 == "REPLAY_AUTH_TOKEN_DETECTED"
