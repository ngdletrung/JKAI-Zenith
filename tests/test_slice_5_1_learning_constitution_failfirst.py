# -*- coding: utf-8 -*-
"""
tests/test_slice_5_1_learning_constitution_failfirst.py
=======================================================
Slice 5.1 — 7 fail-first tests cho Hien chuong Tu Hoc (chi thi Master).
Moi test co ca vi pham + ca hop le. Khong sua test de lay xanh.
"""
from __future__ import annotations

import pytest


def test_T1_proposal_missing_or_expired_data_ttl_must_be_rejected():
    """T1: Proposal thieu data_ttl/expires_at hoac du lieu het han -> tu choi + journal."""
    from core.os.cognition.learning_contract import validate_learning_proposal

    bad_missing = {
        "source": "operational_trace", "sample_count": 120,
        "benchmark_id": "heldout_v1", "compute_budget": "cpu_2h",
        "approval_tier": "L2",
    }
    r1 = validate_learning_proposal(bad_missing)
    assert r1["accepted"] is False and r1["reason_code"] == "MISSING_EXPIRY"

    bad_expired = dict(bad_missing, created_at="2026-01-01T00:00:00Z",
                       expires_at="2026-02-01T00:00:00Z")
    r2 = validate_learning_proposal(bad_expired)
    assert r2["accepted"] is False and r2["reason_code"] == "DATA_EXPIRED"

    good = dict(bad_missing, created_at="2026-10-14T00:00:00Z",
                expires_at="2027-01-01T00:00:00Z")
    r3 = validate_learning_proposal(good)
    assert r3["accepted"] is True


def test_T2_metric_gaming_fewer_proposals_is_not_improvement():
    """T2: Giam so proposal de lam dep phut Master khong duoc tinh la cai thien."""
    from core.os.cognition.learning_contract import evaluate_loop_health

    quiet_week = {"proposals": 1, "promoted": 1, "master_minutes": 2,
                  "held_out_delta": 0.0, "rollbacks": 0, "freezes": 0}
    r = evaluate_loop_health(quiet_week)
    assert r["counts_as_improvement"] is False

    good_week = {"proposals": 8, "promoted": 3, "master_minutes": 20,
                 "held_out_delta": 0.08, "rollbacks": 0, "freezes": 0}
    r2 = evaluate_loop_health(good_week)
    assert r2["counts_as_improvement"] is True


def test_T3_exam_trace_must_be_blocked_at_ingest(tmp_path):
    """T3: Trace co exam_run_id vao pipeline train -> bi chan o ca 2 cua (ingest + harvest LoRA)."""
    from core.dataset.dataset_manager import DatasetManager

    dm = DatasetManager(seed_file=str(tmp_path / "seed.jsonl"),
                        gold_file=str(tmp_path / "gold.jsonl"))

    # Cửa 1: ingest_chunk_revision_as_label với exam_run_id -> Bị chặn
    with pytest.raises(ValueError, match="EXAM_TRACE_BLOCKLISTED"):
        dm.ingest_chunk_revision_as_label(
            chunk_id="exam_q01", original_text="sai", edited_text="dung",
            source_mission_id="exam_run_2026W41",
        )
    assert dm.load_gold_dataset() == []

    # Cửa 2: harvest_trace_as_lora_sample với exam trace -> Bị chặn
    with pytest.raises(ValueError, match="EXAM_TRACE_BLOCKLISTED"):
        dm.harvest_trace_as_lora_sample(
            trace_id="trace_exam_999",
            instruction="Hỏi đáp đề thi bí mật",
            output="Đáp án đề thi",
            source_mission_id="weekly_exam_2026_w42",
        )
    assert dm.load_gold_dataset() == []

    # Ca hợp lệ (không chứa exam identifier) -> Được nạp thành công
    valid_rec = dm.harvest_trace_as_lora_sample(
        trace_id="trace_prod_001",
        instruction="Cấu hình VLAN 100 trên router",
        output="/interface vlan add name=vlan100 vlan-id=100",
        source_mission_id="prod_ticket_1234",
    )
    assert valid_rec.id == "LORA_HARVEST_trace_prod_001"
    assert len(dm.load_gold_dataset()) == 1



def test_T4_sealed_exam_content_unreachable_via_retrieval(tmp_path):
    """T4: De/dap an niem phong khong ingest duoc, khong truy van duoc."""
    from core.os.cognition.learning_contract import (
        EXAM_ISOLATE_DIR_NAME, is_exam_isolated_path,
        query_exam_answer_via_retrieval,
    )

    assert EXAM_ISOLATE_DIR_NAME
    assert is_exam_isolated_path("data/eval/sealed_C/q01.md") is True
    assert is_exam_isolated_path("rag/corpus/doc.md") is False
    with pytest.raises(PermissionError):
        query_exam_answer_via_retrieval("sealed_C_q01")


def test_T5_exam_rotation_requires_difficulty_calibration():
    """T5: Cau moi chua kiem dinh do kho thi khong duoc so sanh diem."""
    from core.os.cognition.learning_contract import calibrate_exam_rotation_difficulty

    uncalibrated = {"new_questions": ["q1", "q2", "q3", "q4"],
                    "difficulty_report": None}
    r = calibrate_exam_rotation_difficulty(uncalibrated)
    assert r["comparable"] is False

    calibrated = {"new_questions": ["q1"],
                  "difficulty_report": {"mean_delta_vs_old": 0.02, "n_trials": 5}}
    r2 = calibrate_exam_rotation_difficulty(calibrated)
    assert r2["comparable"] is True


def test_T6_safety_gate_blocks_promotion_despite_gain():
    """T6: Safety regression > 0 -> chan promote du diem tang (da co san)."""
    from core.dataset.dataset_manager import run_end_to_end_lora_eval_loop

    res = run_end_to_end_lora_eval_loop(simulate_degraded_candidate=True)
    assert res["decision"] == "KILL_SWITCH_ROLLBACK"


def test_T7_two_negative_cycles_trigger_freeze():
    """T7: 2 chu ky am lien tiep -> freeze; canary suy giam -> rollback (da co san)."""
    from core.os.cognition.rsil_orchestrator import AutonomousQuotaTracker

    q = AutonomousQuotaTracker()
    q.record_rollback("r1", drift_pct=20.0)
    q.record_rollback("r2", drift_pct=25.0)
    assert q.is_frozen() is True
