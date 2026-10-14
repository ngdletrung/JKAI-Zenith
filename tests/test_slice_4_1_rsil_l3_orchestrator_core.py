# -*- coding: utf-8 -*-
"""
tests/test_slice_4_1_rsil_l3_orchestrator_core.py
=================================================
[Pha 4 - Slice 4.1: RSIL-L3 Autonomous Promotion Core Contracts]:
Kiểm thử 7 cơ chế thép đã ký duyệt tại Lượt 296:
1. Taxonomy phân loại theo bản chất (security/governance/sanitizer -> bắt buộc Tier 3, cấm auto-promote).
2. Autonomous Quota Tracker & Auto-Freeze (Fail-Closed khi hết 3 lần/tuần hoặc 2 lần rollback liên tiếp).
3. Chữ ký 2 khóa (Operational Witness Key vs Master Authority Key).
4. 4 Cổng Hiến Pháp trực giao (Held-out gain delta >= 0.05, Zero safety regression, System AST invariant, Resource ceiling <= 30%).
5. Sổ cái bất biến Chained Promotion Journal (băm xích SHA-256 prev_sha256 -> curr_sha256).
6. Bottleneck Detector (phân tích bảng StageAttribution 6 khâu tìm khâu nghẽn nhất).
7. Quy trình Auto-Promote & Canary Instant Rollback (< 10ms khi drift > 15%).
"""

import pytest
from core.os.cognition.rsil_orchestrator import (
    EvolutionTier,
    classify_diff_evolution_tier,
    AutonomousQuotaTracker,
    ChainedPromotionJournal,
    DualKeySigner,
    FourConstitutionalGates,
    RSILOrchestrator,
)


def test_slice_4_1_item1_taxonomy_security_enforces_tier3():
    """
    Cơ chế 4 Lượt 296: Bất kỳ diff nào chạm vào security, sanitizer, governor, allowlist,
    authority đều bị cưỡng chế thuộc TIER3_IRREVERSIBLE_AND_SECURITY (Master duyệt bắt buộc).
    """
    # Diff chạm RAG -> Tier 1
    t1 = classify_diff_evolution_tier(["rag/app.py", "core/utils/rag_eval_harness.py"])
    assert t1 == EvolutionTier.TIER1_PARAMETERS_AND_MEMORY

    # Diff chạm LoRA adapter -> Tier 2
    t2 = classify_diff_evolution_tier(["models/lora_adapters/candidate_v1.bin"])
    assert t2 == EvolutionTier.TIER2_MODELS_AND_ROUTERS

    # Diff chạm security/sanitizer dù nhỏ -> Tier 3 bắt buộc
    t3_sec = classify_diff_evolution_tier(["core/sanitizer/state_sanitizer.py"])
    assert t3_sec == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    t3_gov = classify_diff_evolution_tier(["core/kernel/mcp_pilot_allowlist.py"])
    assert t3_gov == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    # [Khắc phục lỗ hổng tải trọng Lượt 298]:
    # 1. tools/web_search.py chứa SSRF guard -> Tier 3 bắt buộc
    t3_ws = classify_diff_evolution_tier(["tools/web_search.py"])
    assert t3_ws == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    # 2. Diff content chứa symbol nhạy cảm (validate_egress_url_ssrf_safe) trên file thường -> Tier 3 bắt buộc
    t3_sym = classify_diff_evolution_tier(
        ["utils/helper.py"],
        diff_content="def wrapper(): return validate_egress_url_ssrf_safe(url)",
    )
    assert t3_sym == EvolutionTier.TIER3_IRREVERSIBLE_AND_SECURITY

    # 3. Thu hẹp pattern auth: author_notes.md KHÔNG bị phạt Tier 3 oan
    t1_author = classify_diff_evolution_tier(["docs/author_notes.md"])
    assert t1_author == EvolutionTier.TIER1_PARAMETERS_AND_MEMORY


def test_slice_4_1_item2_quota_tracker_and_auto_freeze():
    """
    Cơ chế 6 Lượt 296: Ngân sách tự trị 3 lần/tuần và Auto-Freeze khi hết quota hoặc 2 lần rollback liên tiếp.
    """
    tracker = AutonomousQuotaTracker(max_weekly_promotes=3, max_consecutive_rollbacks=2)
    assert tracker.is_frozen() is False

    # Promote 3 lần -> thành công
    tracker.record_promotion("prop_01")
    tracker.record_promotion("prop_02")
    tracker.record_promotion("prop_03")
    assert tracker.is_frozen() is False

    # Lần thứ 4 vượt quota -> tự động đóng băng (Fail-Closed)
    can_promote, reason = tracker.can_promote()
    assert can_promote is False
    assert "FROZEN_QUOTA_EXCEEDED" in reason

    # Reset và test 2 rollback liên tiếp -> Auto-freeze
    tracker.reset_state_for_testing()
    tracker.record_rollback("prop_a", drift_pct=18.0)
    assert tracker.is_frozen() is False
    tracker.record_rollback("prop_b", drift_pct=22.0)
    assert tracker.is_frozen() is True
    assert tracker.state == "FROZEN_CONSECUTIVE_ROLLBACKS"


def test_slice_4_1_item3_chained_promotion_journal_sha256():
    """
    Cơ chế 7 Lượt 296: Sổ cái băm chuỗi append-only (prev_sha256 -> curr_sha256), chống sửa lén.
    """
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        journal = ChainedPromotionJournal(journal_path=j_path)

        journal.append_entry(action="PROPOSE", proposal_id="p1", details={"tier": "TIER1"})
        journal.append_entry(action="PROMOTE", proposal_id="p1", details={"tier": "TIER1", "status": "PASSED"})
        journal.append_entry(action="CANARY_OK", proposal_id="p1", details={"drift": 2.5})

        entries = journal.read_all_entries()
        assert len(entries) == 3
        assert entries[0]["prev_sha256"] == "GENESIS"
        assert entries[1]["prev_sha256"] == entries[0]["curr_sha256"]
        assert entries[2]["prev_sha256"] == entries[1]["curr_sha256"]
        assert journal.verify_journal_integrity() is True


def test_slice_4_1_item4_dual_key_and_four_orthogonal_gates():
    """
    Cơ chế 1 & Cơ chế 5 Lượt 296:
    4 Cổng độc lập: Gain (H1/H2) >= +0.05 và drift <= 10%, Zero Safety Regression, AST Invariant, Resource <= 30%.
    Chữ ký Operational Witness ký CHECKS_PASSED.
    """
    gates = FourConstitutionalGates()
    # Case PASS
    res_pass = gates.evaluate_all(
        baseline_score=0.80,
        candidate_scores=[0.90, 0.88],  # Gain >= +0.08, drift < 5%
        safety_regressions=0,
        ast_invariant_ok=True,
        blast_radius_ok=True,
        resource_overhead_pct=15.0,
    )
    assert res_pass["all_gates_passed"] is True
    assert res_pass["gate_1_heldout_gain"] is True
    assert res_pass["gate_2_zero_safety"] is True

    signer = DualKeySigner()
    sig = signer.sign_operational_witness(proposal_id="p100", gates_result=res_pass)
    assert sig.startswith("WITNESS_HMAC_")
    assert signer.verify_witness_signature("p100", res_pass, sig) is True

    # Case FAIL: có safety regression dù điểm tăng
    res_fail = gates.evaluate_all(
        baseline_score=0.80,
        candidate_scores=[0.95, 0.95],
        safety_regressions=1,
        ast_invariant_ok=True,
        blast_radius_ok=True,
        resource_overhead_pct=10.0,
    )
    assert res_fail["all_gates_passed"] is False
    assert res_fail["gate_2_zero_safety"] is False


def test_slice_4_1_item5_rsil_orchestrator_end_to_end_auto_promote_and_rollback():
    """
    Cơ chế 3 & Lượt 296: Bộ điều phối RSILOrchestrator:
    1. Đọc attribution records phát hiện bottleneck EVIDENCE_RETRIEVAL.
    2. Đánh giá proposal Tier 1 đạt 4 cổng -> tự động Auto-Promote có chữ ký witness.
    3. Giám sát Canary: khi drift > 15% -> giật lùi (rollback) tức thì < 10ms.
    """
    orchestrator = RSILOrchestrator()

    # 1. Bottleneck detection
    dummy_attributions = [
        {"stage": "EVIDENCE_RETRIEVAL", "outcome_ok": False},
        {"stage": "EVIDENCE_RETRIEVAL", "outcome_ok": False},
        {"stage": "ACTION_PROPOSAL", "outcome_ok": True},
        {"stage": "COMPLETION_VERIFICATION", "outcome_ok": True},
    ]
    bn = orchestrator.detect_bottleneck(dummy_attributions)
    assert bn["primary_bottleneck_stage"] == "EVIDENCE_RETRIEVAL"
    assert bn["failure_ratio"] >= 0.5

    # 2. Auto-promote valid Tier 1 candidate
    cand = {
        "proposal_id": "prop_rrf_k_tuning",
        "affected_files": ["rag/app.py"],
        "baseline_score": 0.85,
        "candidate_scores": [0.92, 0.91],
        "safety_regressions": 0,
        "ast_invariant_ok": True,
        "blast_radius_ok": True,
        "resource_overhead_pct": 5.0,
    }
    decision = orchestrator.evaluate_and_autonomous_promote(cand)
    assert decision["decision"] == "AUTO_PROMOTED_INTO_CANARY"
    assert decision["evolution_tier"] == "TIER1_PARAMETERS_AND_MEMORY"
    assert decision["witness_signature"] is not None

    # 3. Canary monitoring & instant rollback
    canary_missions_with_drift = [
        {"mission_id": f"m_{i}", "outcome_ok": True if i < 7 else False}
        for i in range(10)
    ]  # 3 failures in 10 -> 30% drift > 15%
    rb_res = orchestrator.canary_evaluate_and_rollback_if_needed(
        proposal_id="prop_rrf_k_tuning",
        recent_canary_missions=canary_missions_with_drift,
    )
    assert rb_res["rollback_triggered"] is True
    assert rb_res["rollback_elapsed_ms"] < 10.0
    assert rb_res["reason"] == "CANARY_DRIFT_EXCEEDED"
