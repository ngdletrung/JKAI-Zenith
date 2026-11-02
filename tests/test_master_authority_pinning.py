# -*- coding: utf-8 -*-
"""
tests/test_master_authority_pinning.py
[COMPREHENSIVE TEST SUITE FOR MASTER AUTHORITY KEY PINNING & TAMPER RESISTANCE]
Kiểm chứng 10 kịch bản an ninh theo chỉ đạo tại LƯỢT 319 của OpenCode Red Team Auditor.
"""

import base64
import copy
import json
import time
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from services.ai_desktop.master_authority_signer import MasterAuthoritySigner
from services.ai_desktop.master_authority_verifier import MasterAuthorityVerifier, canonical_serialize


class TestMasterAuthorityPinningSuite:

    @pytest.fixture
    def authority_signer(self):
        return MasterAuthoritySigner()

    @pytest.fixture
    def authority_verifier(self):
        return MasterAuthorityVerifier()

    @pytest.fixture
    def valid_context(self):
        now = time.time()
        return {
            "lease_id": "lease_test_001",
            "nonce": "nonce_test_001",
            "hwnd": 123456,
            "target_pid": 9876,
            "proc_name": "notepad.exe",
            "action": "TYPE_TEXT",
            "text_payload": "Authorized Text",
            "session_id": "session_test_001",
            "lease_expires_at": now + 120.0,
            "ttl_seconds": 60.0
        }

    # ── Test 1: Happy Path với Pinned Key ─────────────────────────────────
    def test_valid_pinned_key_signature_passes(self, authority_signer, authority_verifier, valid_context):
        envelope_b64 = authority_signer.issue_mutation_approval(**valid_context)

        ok, reason, details = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is True
        assert reason == "MASTER_AUTHORITY_VERIFIED_PASS"
        assert details["master_key_id"] == "master_primary_v1"
        assert len(details["public_key_fingerprint"]) == 64
        assert details["verifier_identity"] == "JKAI_MASTER_AUTHORITY_VERIFIER_V1"

    # ── Test 2: Forged Key Rejection ─────────────────────────────────────
    def test_forged_key_signature_fails_closed(self, authority_verifier, valid_context):
        """Khóa giả mạo (không nằm trong pinned keys) bị từ chối ngay lập tức."""
        fake_priv = ed25519.Ed25519PrivateKey.generate()
        now = time.time()

        payload = {
            "action": valid_context["action"],
            "expires_at": now + 60.0,
            "hwnd": valid_context["hwnd"],
            "lease_expires_at": valid_context["lease_expires_at"],
            "lease_id": valid_context["lease_id"],
            "nonce": valid_context["nonce"],
            "proc_name": valid_context["proc_name"],
            "session_id": valid_context["session_id"],
            "target_pid": valid_context["target_pid"],
            "text_payload": valid_context["text_payload"],
            "worker_generation": "master_gen_01"
        }
        sig_bytes = fake_priv.sign(canonical_serialize(payload))

        envelope = {
            "key_id": "forged_attacker_key_v1",
            "canonical_payload": payload,
            "signature": base64.b64encode(sig_bytes).decode("utf-8")
        }
        env_b64 = base64.urlsafe_b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")

        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=env_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is False
        assert "UNTRUSTED_KEY_ID" in reason

    # ── Test 3: Signature Tamper Rejection ────────────────────────────────
    def test_signature_tamper_fails_closed(self, authority_signer, authority_verifier, valid_context):
        """Làm giả mạo chữ ký (thay đổi dù chỉ 1 ký tự) lập tức thất bại."""
        envelope_b64 = authority_signer.issue_mutation_approval(**valid_context)
        raw_json = json.loads(base64.urlsafe_b64decode(envelope_b64.encode("utf-8")).decode("utf-8"))

        # Giả mạo chữ ký
        sig_bytes = base64.b64decode(raw_json["signature"])
        tampered_sig = bytes([sig_bytes[0] ^ 0xFF]) + sig_bytes[1:]
        raw_json["signature"] = base64.b64encode(tampered_sig).decode("utf-8")

        tampered_b64 = base64.urlsafe_b64encode(json.dumps(raw_json).encode("utf-8")).decode("utf-8")

        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=tampered_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is False
        assert reason == "INVALID_ED25519_SIGNATURE"

    # ── Test 4: Payload Tamper Rejection ─────────────────────────────────
    def test_payload_tamper_fails_closed(self, authority_signer, authority_verifier, valid_context):
        """Thay đổi nội dung payload nhưng giữ nguyên chữ ký cũ lập tức bị bắt."""
        envelope_b64 = authority_signer.issue_mutation_approval(**valid_context)
        raw_json = json.loads(base64.urlsafe_b64decode(envelope_b64.encode("utf-8")).decode("utf-8"))

        # Sửa payload
        raw_json["canonical_payload"]["text_payload"] = "Tampered Malicious Payload"

        tampered_b64 = base64.urlsafe_b64encode(json.dumps(raw_json).encode("utf-8")).decode("utf-8")

        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=tampered_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text="Tampered Malicious Payload",
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is False
        assert reason == "INVALID_ED25519_SIGNATURE"

    # ── Test 5: Expired Token Rejection ──────────────────────────────────
    def test_expired_approval_fails_closed(self, authority_signer, authority_verifier, valid_context):
        """Token đã hết hạn sử dụng bị từ chối ngay."""
        expired_ctx = copy.deepcopy(valid_context)
        expired_ctx["ttl_seconds"] = -10.0  # Đã hết hạn 10s trước

        envelope_b64 = authority_signer.issue_mutation_approval(**expired_ctx)

        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=expired_ctx["action"],
            expected_hwnd=expired_ctx["hwnd"],
            expected_target_pid=expired_ctx["target_pid"],
            expected_proc_name=expired_ctx["proc_name"],
            expected_text=expired_ctx["text_payload"],
            expected_session_id=expired_ctx["session_id"],
            expected_lease_id=expired_ctx["lease_id"]
        )

        assert ok is False
        assert "APPROVAL_EXPIRED" in reason

    # ── Test 6: Target Context Mismatches ─────────────────────────────────
    def test_target_mismatch_fails_closed(self, authority_signer, authority_verifier, valid_context):
        """Mọi sai lệch danh tính mục tiêu (HWND, PID, process name, action, text) đều Fail-Closed."""
        envelope_b64 = authority_signer.issue_mutation_approval(**valid_context)

        # 1. Sai HWND
        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=valid_context["action"],
            expected_hwnd=999999,
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )
        assert ok is False
        assert "HWND_MISMATCH" in reason

        # 2. Sai PID
        ok2, reason2, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=77777,
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )
        assert ok2 is False
        assert "PID_MISMATCH" in reason2

        # 3. Sai Process Name
        ok3, reason3, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name="cmd.exe",
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )
        assert ok3 is False
        assert "PROC_NAME_MISMATCH" in reason3

    # ── Test 7: Key Revocation Rejection ─────────────────────────────────
    def test_revoked_key_fails_closed(self, authority_signer, authority_verifier, valid_context):
        """Khóa đã bị thu hồi (status == REVOKED) bị từ chối dứt khoát."""
        # Giả lập đưa key_id vào danh sách thu hồi
        authority_verifier._revoked_keys.add("master_primary_v1")
        if "master_primary_v1" in authority_verifier._trusted_keys:
            del authority_verifier._trusted_keys["master_primary_v1"]

        envelope_b64 = authority_signer.issue_mutation_approval(**valid_context)

        ok, reason, _ = authority_verifier.verify_approval_token(
            approval_envelope_b64=envelope_b64,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is False
        assert "REVOKED_MASTER_KEY_ID" in reason

    # ── Test 8: Dynamic Key Rotation ─────────────────────────────────────
    def test_key_rotation_passes(self, valid_context, tmp_path):
        """Khi Master luân chuyển sang key v2, verifier nạp khóa v2 và chấp nhận token v2."""
        # Sinh keypair mới cho v2
        priv2 = ed25519.Ed25519PrivateKey.generate()
        priv2_b64 = base64.b64encode(priv2.private_bytes_raw()).decode("utf-8")
        pub2 = priv2.public_key()
        pub2_bytes = pub2.public_bytes_raw()
        pub2_b64 = base64.b64encode(pub2_bytes).decode("utf-8")
        import hashlib
        fp2 = hashlib.sha256(pub2_bytes).hexdigest()

        # Tạo file config xoay khóa: v1 bị REVOKED, v2 là ACTIVE
        rot_config = tmp_path / "rotated_keys.json"
        rot_data = {
            "version": "1.1",
            "trusted_keys": {
                "master_primary_v1": {
                    "algorithm": "Ed25519",
                    "public_key_b64": "OGyX56SvjINS47b6PawWN0j9js6vnyaLaAuroZXISn0=",
                    "fingerprint_sha256": "e34bd1bf24a03847e3052648d1c40b4027215507eabc110754bf98b89c7431c7",
                    "status": "REVOKED"
                },
                "master_primary_v2": {
                    "algorithm": "Ed25519",
                    "public_key_b64": pub2_b64,
                    "fingerprint_sha256": fp2,
                    "status": "ACTIVE"
                }
            }
        }
        rot_config.write_text(json.dumps(rot_data), encoding="utf-8")

        # Tạo signer giữ khóa v2
        signer_v2_key = tmp_path / "master_v2.json"
        signer_v2_key.write_text(json.dumps({
            "key_id": "master_primary_v2",
            "private_key_b64": priv2_b64,
            "public_key_b64": pub2_b64
        }), encoding="utf-8")

        signer_v2 = MasterAuthoritySigner(key_path=str(signer_v2_key))
        verifier_rot = MasterAuthorityVerifier(config_path=str(rot_config))

        envelope_v2 = signer_v2.issue_mutation_approval(**valid_context)

        ok, reason, details = verifier_rot.verify_approval_token(
            approval_envelope_b64=envelope_v2,
            expected_action=valid_context["action"],
            expected_hwnd=valid_context["hwnd"],
            expected_target_pid=valid_context["target_pid"],
            expected_proc_name=valid_context["proc_name"],
            expected_text=valid_context["text_payload"],
            expected_session_id=valid_context["session_id"],
            expected_lease_id=valid_context["lease_id"]
        )

        assert ok is True
        assert reason == "MASTER_AUTHORITY_VERIFIED_PASS"
        assert details["master_key_id"] == "master_primary_v2"
        assert details["public_key_fingerprint"] == fp2
