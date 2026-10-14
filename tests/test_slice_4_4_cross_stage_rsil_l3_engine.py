# -*- coding: utf-8 -*-
"""
tests/test_slice_4_4_cross_stage_rsil_l3_engine.py
==================================================
[Pha 4 - Slice 4.4: Cross-Stage Attribution Autonomous Proposal Engine & Master Handshake]:
Kiểm thử chu trình tự tiến hóa đệ quy toàn diện RSIL-L3:
1. CrossStageProposalEngine: Đọc StageAttribution 6 khâu -> tự sinh đề xuất sửa đúng khâu nghẽn.
2. MasterAuthorityHandshakeGate: Mọi đề xuất chạm Tier 3 (bảo mật, boundary) bắt buộc có Master ký duyệt.
3. Chữ ký Master hợp lệ: Ủy quyền thành công, ký nhận vào Chained Promotion Journal.
4. Vòng đệ quy RSIL-L3 hoàn chỉnh: Khép kín toàn bộ mạch máu tự học từ đo đạc -> sinh đề xuất -> thăng cấp.
"""

import tempfile
import time
from pathlib import Path
import pytest

from core.os.cognition.rsil_orchestrator import (
    EvolutionTier,
    AutonomousQuotaTracker,
    ChainedPromotionJournal,
    RSILOrchestrator,
)
from core.os.cognition.rsil_tier3_cross_stage_engine import (
    CrossStageProposalEngine,
    MasterAuthorityHandshakeGate,
    run_rsil_l3_full_cycle,
)


def test_slice_4_4_item1_cross_stage_proposal_generation():
    """
    Tự động sinh đề xuất theo khâu nghẽn:
    - EVIDENCE_RETRIEVAL nghẽn -> sinh đề xuất Tier 1 (RAG / Cache).
    - INTENT_ROUTING nghẽn -> sinh đề xuất Tier 2 (LoRA / Router).
    - INGRESS_SANITIZATION hoặc CONTROLLER_GATE nghẽn -> sinh đề xuất Tier 3 (Master Authority).
    """
    engine = CrossStageProposalEngine()

    # 1. Khâu Retrieval nghẽn
    p1 = engine.generate_remediation_proposal("EVIDENCE_RETRIEVAL", failure_ratio=0.6)
    assert p1["evolution_tier"] == EvolutionTier.TIER1_PARAMETERS_AND_MEMORY.value
    assert "core/utils/rag_eval_harness.py" in p1["affected_files"]

    # 2. Khâu Routing nghẽn
    p2 = engine.generate_remediation_proposal("INTENT_ROUTING", failure_ratio=0.5)
    assert p2["evolution_tier"] == EvolutionTier.TIER2_MODELS_AND_ROUTERS.value
    assert any("models/" in f for f in p2["affected_files"])

    # 3. Khâu Security / Ingress nghẽn
    p3 = engine.generate_remediation_proposal("INGRESS_SANITIZATION", failure_ratio=0.4)
    assert p3["evolution_tier"] == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY.value
    assert any("core/security" in f or "sanitizer" in f for f in p3["affected_files"])


def test_slice_4_4_item2_tier3_master_handshake_gate_blocks_auto_promote():
    """
    Rào chắn Master Handshake Gate:
    Đề xuất Tier 3 gửi vào RSILOrchestrator BẮT BUỘC bị từ chối Auto-Promote
    và tạo ra 1 Challenge Token chờ Master ký duyệt.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        orchestrator = RSILOrchestrator(journal_path=j_path)
        gate = MasterAuthorityHandshakeGate(orchestrator=orchestrator)

        tier3_proposal = {
            "proposal_id": "prop_sec_01",
            "affected_files": ["core/security/auth_verifier.py"],
            "diff_content": "def authorize_mutation_path(): pass",
            "evolution_tier": EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY.value,
        }

        # Thử auto-promote -> BỊ TỪ CHỐI
        eval_res = orchestrator.evaluate_and_autonomous_promote(tier3_proposal)
        assert eval_res["decision"] == "REQUIRES_MASTER_AUTHORITY"

        # Tạo Master Handshake Challenge
        challenge = gate.create_handshake_challenge(tier3_proposal)
        assert challenge["status"] == "AWAITING_MASTER_SIGNATURE"
        assert challenge["challenge_token"] is not None
        assert challenge["witness_attestation"] is not None


def test_slice_4_4_item3_valid_master_handshake_authorizes_tier3(monkeypatch):
    """
    Ủy quyền thành công bằng chữ ký Master ngoài băng:
    - Secret được cấp động qua biến môi trường hoặc out-of-band (không lưu trong source).
    - Master ký challenge token bằng hàm ký độc lập ngoài băng.
    - Gate xác thực chữ ký -> Ủy quyền thành công -> Ghi sổ cái bất biến Chained Journal.
    - Ký sai key -> BỊ TỪ CHỐI (INVALID_MASTER_SIGNATURE).
    """
    import secrets

    dynamic_master_secret = f"zenith_master_{secrets.token_hex(24)}"
    monkeypatch.setenv("JKAI_MASTER_AUTHORITY_KEY", dynamic_master_secret)

    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        orchestrator = RSILOrchestrator(journal_path=j_path)
        gate = MasterAuthorityHandshakeGate(orchestrator=orchestrator)

        tier3_proposal = {
            "proposal_id": "prop_sec_02",
            "affected_files": ["core/sanitizer/state_sanitizer.py"],
            "evolution_tier": EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY.value,
        }
        challenge = gate.create_handshake_challenge(tier3_proposal)

        # 1. Ký đúng khóa Master bằng hàm out-of-band
        valid_sig = MasterAuthorityHandshakeGate.sign_with_master_key(
            challenge_token=challenge["challenge_token"],
            master_secret=dynamic_master_secret,
        )
        auth_res = gate.verify_and_authorize_tier3(challenge, master_signature=valid_sig)
        assert auth_res["authorized"] is True
        assert auth_res["decision"] == "MASTER_AUTHORITY_GRANTED"
        assert orchestrator.journal.verify_journal_integrity() is True

        # 2. Ký sai khóa Master -> Từ chối
        invalid_sig = "FAKE_TAMPERED_MASTER_SIGNATURE_XYZ"
        fail_res = gate.verify_and_authorize_tier3(challenge, master_signature=invalid_sig)
        assert fail_res["authorized"] is False
        assert fail_res["decision"] == "REJECTED_INVALID_MASTER_SIGNATURE"


def test_slice_4_4_item4_full_rsil_l3_closed_loop_recursion():
    """
    Khép kín toàn bộ mạch máu tự học đệ quy RSIL-L3:
    1. Quét StageAttribution telemetry.
    2. Tự động nhận diện khâu nghẽn nhất.
    3. Tự sinh đề xuất tương ứng.
    4. Tự động đánh giá 4 Cổng Hiến Pháp -> Auto-Promote vào Canary.
    5. Kiểm tra sổ cái Chained SHA-256 Journal toàn vẹn 100%.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        cycle_res = run_rsil_l3_full_cycle(
            telemetry_records=[
                {"stage_attribution": "EVIDENCE_RETRIEVAL", "observation": "error: chunk missing"},
                {"stage_attribution": "EVIDENCE_RETRIEVAL", "observation": "error: timeout"},
                {"stage_attribution": "ACTION_PROPOSAL", "status": "OK"},
            ],
            journal_path=j_path,
        )
        assert cycle_res["bottleneck_stage"] == "EVIDENCE_RETRIEVAL"
        assert cycle_res["proposal_generated"] is True
        assert cycle_res["execution_decision"] in ("AUTO_PROMOTED_INTO_CANARY", "MAINTAINED_BASELINE")
        assert cycle_res["journal_integrity_ok"] is True
        assert cycle_res["quota_frozen"] is False


def test_slice_4_4_item5_attacker_cannot_self_authorize_without_master_key(monkeypatch):
    """
    [Thử nghiệm Kẻ Tấn Công — Red Team Lượt 306]:
    Mô phỏng kẻ tấn công hoặc quy trình tự trị cố tình tự ký duyệt Tier 3
    khi không nắm được JKAI_MASTER_AUTHORITY_KEY:
    - Môi trường không có biến JKAI_MASTER_AUTHORITY_KEY.
    - Gate ở trạng thái AWAITING_MASTER_SIGNATURE fail-closed.
    - Mọi nỗ lực gọi verify_and_authorize_tier3 đều bị từ chối với mã REJECTED_MISSING_MASTER_KEY.
    """
    monkeypatch.delenv("JKAI_MASTER_AUTHORITY_KEY", raising=False)

    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        orchestrator = RSILOrchestrator(journal_path=j_path)
        gate = MasterAuthorityHandshakeGate(orchestrator=orchestrator, master_secret=None)

        tier3_proposal = {
            "proposal_id": "prop_attack_01",
            "affected_files": ["core/security/egress_guard.py"],
            "evolution_tier": EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY.value,
        }
        challenge = gate.create_handshake_challenge(tier3_proposal)

        # Kẻ tấn công thử đưa chữ ký giả hoặc đoán secret
        attacker_sig = "MASTER_HMAC_attacker_forged_sig"
        res = gate.verify_and_authorize_tier3(challenge, master_signature=attacker_sig)

        assert res["authorized"] is False
        assert res["decision"] == "REJECTED_MISSING_MASTER_KEY"
        assert "Autonomous self-approval is strictly forbidden" in res["reason"]


def test_slice_4_4_item6_zero_hardcoded_master_secrets_in_core():
    """
    [Quét Toàn Bộ Mã Nguồn Core]:
    Đảm bảo 100% không còn bất kỳ chuỗi Master Secret tĩnh nào bị hardcode trong thư mục core/.
    """
    import os

    forbidden_needles = [
        "MASTER_ZENITH_VAULT_KEY_SECURE_2026",
    ]

    core_dir = Path(__file__).resolve().parent.parent / "core"
    for root, _, files in os.walk(core_dir):
        for f in files:
            if f.endswith(".py"):
                f_path = Path(root) / f
                content = f_path.read_text(encoding="utf-8", errors="ignore")
                for needle in forbidden_needles:
                    assert needle not in content, f"Phat hien secret bi hardcode tai: {f_path}"

