# -*- coding: utf-8 -*-
"""
tests/test_desktop_control_hardening.py
[R1..R4 / R6 / R7 hardening suite]

Bổ sung các lớp bằng chứng mà bộ test cũ không có:
  1. Policy SSoT: JSON là nguồn duy nhất, file hỏng/thiếu -> fail-closed.
  2. IR boundary: bỏ coordinate_policy / FocusParams.dummy, cấm field lạ trong wire payload.
  3. Ed25519 thật: signer (private) và verifier (pinned public key) round-trip,
     envelope bị sửa nội dung -> từ chối.
  4. End-to-end dispatch thật: approval envelope + nonce SQLite + after-state độc lập
     -> DELIVERED_VERIFIED; chạy lại -> REPLAY_NONCE_DETECTED.
  5. Nonce store bền vững qua "restart" (instance mới trên cùng DB).
  6. Independent after-state verifier: match_mode append/exact và read_success gate.
"""

import base64
import hashlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from services.ai_desktop.app_policy import (
    DEFAULT_POLICY_PATH,
    DesktopActionPolicy,
    DesktopPolicyError,
    get_policy,
)
from services.ai_desktop.host_after_state_verifier import HostAfterStateVerifier
from services.ai_desktop.master_authority_signer import MasterAuthoritySigner, canonical_serialize
from services.ai_desktop.master_authority_verifier import MasterAuthorityVerifier
from services.ai_desktop.nonce_store import PersistentNonceStore
from services.ai_desktop.semantic_action_dispatcher import SemanticActionDispatcher
from services.ai_desktop.semantic_action_ir import (
    ActionType,
    ClickParams,
    FocusParams,
    SemanticActionIR,
    TypeTextParams,
    compute_canonical_snapshot_hash,
)
from services.ai_desktop.uia_tree_inspector import UIAElementNode, UIATreeSnapshot

KEY_ID = "test_master_v1"


# ── Fixtures ─────────────────────────────────────────────────────────────


def _notepad_snapshot(text: str = "", captured_at=None, ttl=30.0):
    hwnd, pid, proc = 5555, 8888, "notepad.exe"
    nodes = [
        UIAElementNode(
            name="Text Editor",
            control_type="Edit",
            automation_id="Edit",
            class_name="Edit",
            rect=(0, 0, 400, 300),
            center=(200, 150),
            hwnd=hwnd,
            supported_patterns=["ValuePattern"],
            ref="e1",
            value=text,
        )
    ]
    snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc, elements=nodes)
    base = time.time() if captured_at is None else captured_at
    return UIATreeSnapshot(
        hwnd=hwnd,
        window_title="Untitled - Notepad",
        process_name=proc,
        pid=pid,
        element_count=len(nodes),
        snapshot_hash=snap_hash,
        elements=nodes,
        ref_map={n.ref: n for n in nodes},
        captured_at=base,
        expires_at=base + ttl,
    )


class FakeAfterState:
    def __init__(self, before_text="seed", match=True):
        self.before_text = before_text
        self.match = match

    def capture_snapshot(self, hwnd, proc_name="notepad.exe"):
        return {
            "timestamp": time.time(),
            "hwnd": hwnd,
            "proc_name": proc_name,
            "read_success": True,
            "text": self.before_text,
            "hash": hashlib.sha256(self.before_text.encode("utf-8")).hexdigest(),
            "error": None,
        }

    def verify_action_result(self, before_snapshot, hwnd, expected_mutation_text, proc_name="notepad.exe",
                             timeout_seconds=2.0, match_mode="append"):
        after_text = expected_mutation_text if self.match else "unexpected"
        return {
            "status": "VERIFIED_MATCH" if self.match else "STATE_MISMATCH",
            "before_hash": before_snapshot.get("hash", ""),
            "after_hash": hashlib.sha256(after_text.encode("utf-8")).hexdigest(),
            "expected_text_sha256": hashlib.sha256(expected_mutation_text.encode("utf-8")).hexdigest(),
            "read_success": True,
            "match": self.match,
            "match_mode": match_mode,
            "receipt_digest": "d" * 64,
        }


@pytest.fixture
def ephemeral_master(tmp_path):
    """Sinh cặp khóa Ed25519 tạm thời + pinned public keys để không đụng khóa thật."""
    private = ed25519.Ed25519PrivateKey.generate()
    raw_priv = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_pub = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fingerprint = hashlib.sha256(raw_pub).hexdigest()

    key_dir = tmp_path / "secrets"
    key_dir.mkdir()
    key_path = key_dir / "master_authority_key.json"
    key_path.write_text(
        json.dumps(
            {
                "key_id": KEY_ID,
                "private_key_b64": base64.b64encode(raw_priv).decode("utf-8"),
                "public_key_b64": base64.b64encode(raw_pub).decode("utf-8"),
                "fingerprint_sha256": fingerprint,
            }
        ),
        encoding="utf-8",
    )

    pub_path = tmp_path / "master_public_keys.json"
    pub_path.write_text(
        json.dumps(
            {
                "trusted_keys": {
                    KEY_ID: {
                        "status": "ACTIVE",
                        "public_key_b64": base64.b64encode(raw_pub).decode("utf-8"),
                        "fingerprint_sha256": fingerprint,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    return {
        "signer": MasterAuthoritySigner(key_path=str(key_path)),
        "verifier": MasterAuthorityVerifier(config_path=str(pub_path)),
        "fingerprint": fingerprint,
    }


def _type_text_action(snapshot, text="Hardened payload", nonce="nonce_hardened_0001", digest=None):
    now = time.time()
    el = snapshot.ref_map["e1"]
    return SemanticActionIR(
        session_id="pilot_session_001",
        lease_id="lease_hardened_001",
        nonce=nonce,
        issued_at=now,
        expires_at=now + 60.0,
        approval_digest=digest or ("sha256_" + "0" * 64),
        action_type=ActionType.TYPE_TEXT,
        target_ref="e1",
        target_hwnd=snapshot.hwnd,
        target_pid=snapshot.pid,
        target_process_name=snapshot.process_name,
        element_hash=el.element_hash,
        snapshot_hash=snapshot.snapshot_hash,
        parameters=TypeTextParams(text=text, max_length=1000, clear_before_type=True),
        description="Hardening e2e action",
    )


def _approve(signer: MasterAuthoritySigner, action: SemanticActionIR):
    """Master ký envelope cho action; trả về (envelope_b64, approval_digest)."""
    payload = signer.build_mutation_approval_payload(
        lease_id=action.lease_id,
        nonce=action.nonce,
        hwnd=action.target_hwnd,
        target_pid=action.target_pid,
        proc_name=action.target_process_name,
        action=action.action_type.value,
        text_payload=action.parameters.text,
        session_id=action.session_id,
        lease_expires_at=action.expires_at,
    )
    digest = "sha256_" + hashlib.sha256(canonical_serialize(payload)).hexdigest()
    return signer.sign_payload(payload), digest


# ── 1. Policy SSoT ───────────────────────────────────────────────────────


class TestPolicySSOT:

    def _write_policy(self, tmp_path, **overrides):
        policy = {
            "version": "test-1.0",
            "policy_name": "TEST_DESKTOP_POLICY",
            "destructive_keywords": ["delete"],
            "global_invariants": {"pure_read_only_sampler_port": 9997},
            "allowed_applications": {
                "notepad.exe": {
                    "app_name": "Notepad",
                    "allowed_actions": ["type_text"],
                    "element_allowlist": ["Edit"],
                    "max_text_length": 50,
                }
            },
        }
        policy.update(overrides)
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        return path

    def test_policy_loaded_from_json_is_authoritative(self, tmp_path):
        path = self._write_policy(tmp_path)
        policy = DesktopActionPolicy.load(str(path))

        assert policy.version == "test-1.0"
        assert policy.allowed_processes == frozenset({"notepad.exe"})
        rule = policy.app_rule("Notepad.EXE ")
        assert rule is not None
        assert rule.allows_action("type_text") is True
        assert rule.allows_action("click") is False
        assert rule.max_text_length == 50
        assert rule.allows_element("Text Editor", "Edit", "Edit", "Edit") == (True, "ELEMENT_ALLOWLISTED")
        assert rule.allows_element("Password", "passEdit", "Edit", "Edit")[0] is False

    def test_empty_element_allowlist_denies_everything(self, tmp_path):
        path = self._write_policy(
            tmp_path,
            allowed_applications={
                "notepad.exe": {"app_name": "Notepad", "allowed_actions": ["type_text"], "element_allowlist": []}
            },
        )
        rule = DesktopActionPolicy.load(str(path)).app_rule("notepad.exe")
        assert rule.allows_element("Text Editor", "Edit", "Edit", "Edit") == (False, "ELEMENT_ALLOWLIST_EMPTY")

    def test_unknown_action_in_policy_fails_closed(self, tmp_path):
        path = self._write_policy(
            tmp_path,
            allowed_applications={
                "notepad.exe": {"app_name": "Notepad", "allowed_actions": ["execute_shell"], "element_allowlist": ["Edit"]}
            },
        )
        with pytest.raises(DesktopPolicyError) as excinfo:
            DesktopActionPolicy.load(str(path))
        assert "POLICY_UNKNOWN_ACTIONS" in str(excinfo.value)

    def test_missing_policy_file_fails_closed(self, tmp_path):
        with pytest.raises(DesktopPolicyError) as excinfo:
            DesktopActionPolicy.load(str(tmp_path / "does_not_exist.json"))
        assert "POLICY_FILE_MISSING" in str(excinfo.value)

    def test_default_policy_is_present_and_includes_notepad(self):
        policy = get_policy(DEFAULT_POLICY_PATH)
        assert "notepad.exe" in policy.allowed_processes
        assert get_policy(DEFAULT_POLICY_PATH) is policy  # cached theo path+mtime+size


# ── 2. IR boundary ───────────────────────────────────────────────────────


class TestIRHardening:

    def _wire_action(self, parameters):
        now = time.time()
        return {
            "session_id": "pilot_session_001",
            "lease_id": "lease_hardened_001",
            "nonce": "nonce_hardened_0001",
            "issued_at": now,
            "expires_at": now + 60.0,
            "approval_digest": "sha256_" + "a" * 64,
            "action_type": "click",
            "target_ref": "e1",
            "target_hwnd": 5555,
            "target_pid": 8888,
            "target_process_name": "notepad.exe",
            "element_hash": "f" * 64,
            "snapshot_hash": "sha256_" + "e" * 64,
            "parameters": parameters,
        }

    def test_coordinate_policy_is_gone(self):
        """R7: coordinate_policy bị xóa hẳn khỏi ClickParams và wire schema."""
        with pytest.raises(TypeError):
            ClickParams(button="left", coordinate_policy="none")

        wire = self._wire_action({"button": "left", "coordinate_policy": "none"})
        with pytest.raises(ValueError) as excinfo:
            SemanticActionIR.from_wire_dict(wire)
        assert "UNKNOWN_PARAM_FIELDS" in str(excinfo.value)

    def test_focus_params_has_no_fields(self):
        assert FocusParams() == FocusParams()
        assert FocusParams.__dataclass_fields__ == {}

    def test_click_partial_coordinates_rejected(self):
        ok, reason = ClickParams(button="left", target_x=10).validate()
        assert ok is False
        assert "CLICK_TARGET_COORDS_INCOMPLETE" in reason

    def test_wire_unknown_root_field_rejected(self):
        wire = self._wire_action({"button": "left"})
        wire["shell_command"] = "whoami"
        with pytest.raises(ValueError) as excinfo:
            SemanticActionIR.from_wire_dict(wire)
        assert "UNKNOWN_ROOT_FIELDS" in str(excinfo.value)


# ── 3. Ed25519 round-trip ────────────────────────────────────────────────


class TestEd25519Approval:

    def test_signed_envelope_verifies(self, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot)
        envelope, digest = _approve(ephemeral_master["signer"], action)

        ok, reason, details = ephemeral_master["verifier"].verify_approval_token(
            approval_envelope_b64=envelope,
            expected_action=action.action_type.value,
            expected_hwnd=action.target_hwnd,
            expected_target_pid=action.target_pid,
            expected_proc_name=action.target_process_name,
            expected_text=action.parameters.text,
            expected_session_id=action.session_id,
            expected_lease_id=action.lease_id,
            expected_nonce=action.nonce,
        )
        assert ok is True
        assert reason == "MASTER_AUTHORITY_VERIFIED_PASS"
        assert details["master_key_id"] == KEY_ID
        assert details["public_key_fingerprint"] == ephemeral_master["fingerprint"]
        assert "sha256_" + details["canonical_payload_sha256"] == digest

    def test_tampered_payload_is_rejected(self, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot, text="signed text")
        envelope, _ = _approve(ephemeral_master["signer"], action)

        ok, reason, _ = ephemeral_master["verifier"].verify_approval_token(
            approval_envelope_b64=envelope,
            expected_action=action.action_type.value,
            expected_hwnd=action.target_hwnd,
            expected_target_pid=action.target_pid,
            expected_proc_name=action.target_process_name,
            expected_text="different text",
            expected_session_id=action.session_id,
            expected_lease_id=action.lease_id,
            expected_nonce=action.nonce,
        )
        assert ok is False
        assert "TEXT_PAYLOAD_MISMATCH" in reason

    def test_corrupted_signature_is_rejected(self, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot)
        envelope, _ = _approve(ephemeral_master["signer"], action)

        raw = json.loads(base64.urlsafe_b64decode(envelope.encode("utf-8")))
        sig = bytearray(base64.b64decode(raw["signature"]))
        sig[0] ^= 0xFF
        raw["signature"] = base64.b64encode(bytes(sig)).decode("utf-8")
        tampered = base64.urlsafe_b64encode(json.dumps(raw).encode("utf-8")).decode("utf-8")

        ok, reason, _ = ephemeral_master["verifier"].verify_approval_token(
            approval_envelope_b64=tampered,
            expected_action=action.action_type.value,
            expected_hwnd=action.target_hwnd,
            expected_target_pid=action.target_pid,
            expected_proc_name=action.target_process_name,
            expected_text=action.parameters.text,
            expected_session_id=action.session_id,
            expected_lease_id=action.lease_id,
            expected_nonce=action.nonce,
        )
        assert ok is False
        assert "INVALID_ED25519_SIGNATURE" in reason


# ── 4. End-to-end dispatch ───────────────────────────────────────────────


class TestEndToEndDispatch:

    @pytest.fixture(autouse=True)
    def _test_mode_env(self, monkeypatch):
        monkeypatch.delenv("JKAI_MUTATION_ENABLED", raising=False)
        monkeypatch.setenv("JKAI_MUTATION_TEST_MODE", "1")

    def _dispatcher(self, tmp_path, ephemeral_master, after_state=None):
        return SemanticActionDispatcher(
            inspector=MagicMock(),
            dry_run=False,
            verifier=ephemeral_master["verifier"],
            nonce_store=PersistentNonceStore(tmp_path / "nonces.db"),
            after_state_verifier=after_state or FakeAfterState(),
        )

    def test_approved_dispatch_is_delivered_verified_once(self, tmp_path, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot)
        envelope, digest = _approve(ephemeral_master["signer"], action)
        action.approval_digest = digest
        dispatcher = self._dispatcher(tmp_path, ephemeral_master)

        with patch("win32gui.SendMessage", return_value=1) as send_message:
            res = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64=envelope
            )

        assert res.success is True
        assert res.status == "DELIVERED_VERIFIED"
        receipt = res.execution_receipt
        assert receipt["verified_after_state"] is True
        assert receipt["approval"]["master_key_id"] == KEY_ID
        assert receipt["approval"]["canonical_payload_sha256"] == digest.replace("sha256_", "")
        assert receipt["nonce"] == action.nonce
        assert send_message.call_count == 1

        # Replay cùng nonce / lease -> chặn đứng
        replay = dispatcher.dispatch_action(
            action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64=envelope
        )
        assert replay.success is False
        assert replay.status == "REPLAY_NONCE_DETECTED"

    def test_digest_must_match_signed_payload(self, tmp_path, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot)
        envelope, digest = _approve(ephemeral_master["signer"], action)
        action.approval_digest = "sha256_" + "9" * 64  # sai lệch so với envelope
        dispatcher = self._dispatcher(tmp_path, ephemeral_master)

        with patch("win32gui.SendMessage") as send_message:
            res = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64=envelope
            )

        assert res.success is False
        assert res.status == "REJECTED_BY_APPROVAL"
        assert "APPROVAL_DIGEST_MISMATCH" in res.reason
        send_message.assert_not_called()

    def test_after_state_mismatch_is_never_verified(self, tmp_path, ephemeral_master):
        snapshot = _notepad_snapshot()
        action = _type_text_action(snapshot)
        envelope, digest = _approve(ephemeral_master["signer"], action)
        action.approval_digest = digest
        dispatcher = self._dispatcher(tmp_path, ephemeral_master, after_state=FakeAfterState(match=False))

        with patch("win32gui.SendMessage", return_value=1):
            res = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64=envelope
            )

        assert res.success is False
        assert res.status == "AFTER_STATE_VERIFICATION_FAILED"
        assert res.execution_receipt["verified_after_state"] is False


# ── 5. Persistent nonce store ────────────────────────────────────────────


class TestNonceStorePersistence:

    def test_nonce_survives_new_instance(self, tmp_path):
        db = tmp_path / "nonces.db"
        first = PersistentNonceStore(db)
        assert first.check_and_use_nonce("desktop_dispatch_nonce_x1", "desktop_dispatch", 60.0) is True

        second = PersistentNonceStore(db)
        assert second.check_and_use_nonce("desktop_dispatch_nonce_x1", "desktop_dispatch", 60.0) is False
        assert second.is_nonce_used("desktop_dispatch_nonce_x1") is True

    def test_expired_nonce_can_be_reused_after_prune(self, tmp_path):
        store = PersistentNonceStore(tmp_path / "nonces.db")
        assert store.check_and_use_nonce("desktop_dispatch_nonce_x2", "desktop_dispatch", 0.05) is True
        time.sleep(0.1)
        store.prune_expired()
        assert store.check_and_use_nonce("desktop_dispatch_nonce_x2", "desktop_dispatch", 60.0) is True


# ── 6. Independent after-state verifier logic ────────────────────────────


class ScriptedVerifier(HostAfterStateVerifier):
    """Ghi đè capture_snapshot để kiểm chứng thuần logic so khớp."""

    def __init__(self, readings):
        super().__init__()
        self.readings = list(readings)

    def capture_snapshot(self, hwnd, proc_name="notepad.exe"):
        reading = self.readings.pop(0) if self.readings else (False, "")
        success, text = reading
        return {
            "timestamp": time.time(),
            "hwnd": hwnd,
            "proc_name": proc_name,
            "read_success": success,
            "text": text,
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "error": None if success else "SCRIPTED_READ_FAILURE",
        }


class TestAfterStateVerifier:

    def test_exact_match_requires_exact_text(self):
        verifier = ScriptedVerifier([(True, "expected text")])
        result = verifier.verify_action_result(
            before_snapshot={"text": "old", "hash": "h"},
            hwnd=1,
            expected_mutation_text="expected text",
            match_mode="exact",
        )
        assert result["match"] is True
        assert result["status"] == "VERIFIED_MATCH"

    def test_append_match_requires_before_plus_text(self):
        verifier = ScriptedVerifier([(True, "old" + "new")])
        result = verifier.verify_action_result(
            before_snapshot={"text": "old", "hash": "h"},
            hwnd=1,
            expected_mutation_text="new",
            match_mode="append",
        )
        assert result["match"] is True

    def test_read_failure_never_matches(self):
        verifier = ScriptedVerifier([(False, "expected text"), (False, "expected text")])
        result = verifier.verify_action_result(
            before_snapshot={"text": "", "hash": "h"},
            hwnd=1,
            expected_mutation_text="expected text",
            match_mode="exact",
            timeout_seconds=0.01,
        )
        assert result["match"] is False
        assert result["read_success"] is False

    def test_invalid_match_mode_raises(self):
        verifier = ScriptedVerifier([])
        with pytest.raises(ValueError):
            verifier.verify_action_result({}, 1, "x", match_mode="fuzzy")
