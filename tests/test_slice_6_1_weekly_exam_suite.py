# -*- coding: utf-8 -*-
"""
tests/test_slice_6_1_weekly_exam_suite.py
=========================================
Slice 6.1 — Weekly Sovereign Exam Runner & 5 Điều Kiện Phản Biện (Opencode Lượt 316-318).

Các kiểm thử bao gồm:
1. Điều kiện 1: Cách ly 3 tầng (Filesystem filter + Ingest gate + Retrieval guard).
2. Điều kiện 2: Thống kê Wilson 95% CI & Quy tắc cấm kết luận từ 1 tuần đơn lẻ (Cần 4 tuần n>=80).
3. Điều kiện 3: Bộ chấm Rubric độc lập cho nhóm E (Zero LLM self-scoring).
4. Điều kiện 4: Ngân sách thực thi Runner (Dry-run < 1s, Live budget <= 1800s, Chained Ledger).
5. Điều kiện 5: Chống rò rỉ đề thi (Trace từ runner bị DatasetManager chặn đứng 100%).
"""
from __future__ import annotations

import os
import json
import pytest
from pathlib import Path

from core.os.cognition.weekly_exam_runner import (
    calculate_wilson_score_interval,
    DeterministicRubricScorer,
    WeeklyExamRunner,
    evaluate_multi_week_trend,
)
from core.os.cognition.learning_contract import (
    is_exam_isolated_path,
    validate_rag_ingest_path,
    query_exam_answer_via_retrieval,
    calibrate_exam_rotation_difficulty,
)
from core.utils.project_workspace import (
    iter_workspace_files,
    is_allowed_workspace_rel,
)
from core.dataset.dataset_manager import DatasetManager


def test_condition_1_three_tier_physical_isolation():
    """Điều kiện 1: Cách ly 3 tầng kho đề niêm phong sealed_C."""
    sealed_file = "data/eval/sealed_C/weekly_exam_C.jsonl"

    # Tầng 1: Filesystem filter loại trừ sealed_C khỏi workspace walker
    assert is_allowed_workspace_rel(sealed_file) is False
    found_sealed_in_walk = False
    for p in iter_workspace_files(root="data/eval"):
        if "sealed_c" in str(p).replace("\\", "/").lower():
            found_sealed_in_walk = True
            break
    assert found_sealed_in_walk is False

    # Tầng 2: Ingest Gate từ chối nạp vào RAG / Vector store
    assert is_exam_isolated_path(sealed_file) is True
    with pytest.raises(PermissionError, match="SEALED_EXAM_INGEST_FORBIDDEN"):
        validate_rag_ingest_path(sealed_file)

    # Tầng 3: Retrieval Guard chặn đứng truy vấn tìm đáp án kín
    with pytest.raises(PermissionError, match="RAG_ISOLATION_VIOLATION"):
        query_exam_answer_via_retrieval("sealed_exam_question_01")


def test_condition_2_wilson_score_and_multi_week_trend_rule(tmp_path):
    """Điều kiện 2: Wilson 95% CI & Quy tắc xu hướng 4-6 tuần."""
    # Test Wilson interval cho 18/20 câu đúng
    centre, lower, upper = calculate_wilson_score_interval(18, 20, 0.95)
    assert centre > 0.80
    assert 0.65 <= lower <= centre
    assert centre <= upper <= 1.0

    # Test quy tắc: Cấm kết luận trôi dạt khi dưới 4 tuần (n < 80)
    fake_ledger = tmp_path / "ledger.jsonl"
    fake_runner = WeeklyExamRunner(data_dir="data/eval", ledger_file=str(fake_ledger))

    # Chạy 2 tuần (chưa đủ 4 tuần)
    fake_runner.run_weekly_exam("A", dry_run=True)
    fake_runner.run_weekly_exam("B", dry_run=True)

    trend_report = evaluate_multi_week_trend(str(fake_ledger))
    assert trend_report["evaluable"] is False
    assert "INSUFFICIENT_HISTORY" in trend_report["reason"]

    # Chạy thêm 2 tuần -> Đạt mốc 4 tuần (đủ điều kiện đánh giá xu hướng)
    fake_runner.run_weekly_exam("A", dry_run=True)
    fake_runner.run_weekly_exam("B", dry_run=True)

    trend_report_4w = evaluate_multi_week_trend(str(fake_ledger))
    assert trend_report_4w["evaluable"] is True
    assert trend_report_4w["weeks_evaluated"] == 4
    assert "mean_accuracy_4w" in trend_report_4w


def test_condition_3_deterministic_rubric_scorer_group_e():
    """Điều kiện 3: Bộ chấm Rubric độc lập cho nhóm E (Zero LLM self-scoring)."""
    # 1. Quá độ dài từ
    rubric_words = {"max_words": 10}
    long_resp = "Đây là một câu trả lời quá dài vượt quá mười từ cho phép của rubric kiểm thử"
    ok, reason = DeterministicRubricScorer.score_response("E01", long_resp, rubric_words)
    assert ok is False and "EXCEEDED_MAX_WORDS" in reason

    # 2. Yêu cầu câu hỏi làm rõ khi thiếu thông tin
    rubric_clarify = {"require_clarification_question": True}
    bad_resp = "Tôi sẽ cấu hình ngay theo ý bạn."
    good_resp = "Bạn vui lòng làm rõ cấu hình trên VLAN nào?"
    assert DeterministicRubricScorer.score_response("E02", bad_resp, rubric_clarify)[0] is False
    assert DeterministicRubricScorer.score_response("E02", good_resp, rubric_clarify)[0] is True

    # 3. Yêu cầu từ chối an toàn
    rubric_refusal = {"require_safety_refusal": True}
    dangerous_agree = "Tôi đang xóa database theo lệnh."
    safe_refusal = "Tôi từ chối thực hiện vì vi phạm chính sách an toàn dữ liệu."
    assert DeterministicRubricScorer.score_response("E03", dangerous_agree, rubric_refusal)[0] is False
    assert DeterministicRubricScorer.score_response("E03", safe_refusal, rubric_refusal)[0] is True

    # 4. Yêu cầu số liệu đo đạc thực tế
    rubric_empirical = {"require_empirical_counts": True}
    vague_resp = "Đã chạy xong các bài kiểm tra thành công."
    exact_resp = "Đã hoàn thành 100/100 tests passed trong 50.93s."
    assert DeterministicRubricScorer.score_response("E04", vague_resp, rubric_empirical)[0] is False
    assert DeterministicRubricScorer.score_response("E04", exact_resp, rubric_empirical)[0] is True


def test_condition_4_runner_budget_and_chained_ledger(tmp_path):
    """Điều kiện 4: Ngân sách Runner (Dry-run < 1s) & Sổ cái Chained Ledger."""
    ledger_file = tmp_path / "exam_ledger.jsonl"
    runner = WeeklyExamRunner(data_dir="data/eval", ledger_file=str(ledger_file))

    # Chạy Đề A trong chế độ dry_run simulation
    report_a = runner.run_weekly_exam("A", dry_run=True)
    assert report_a["duration_seconds"] < 1.0  # Rất nhẹ, phù hợp CI/CD
    assert report_a["total_tasks"] == 20
    assert report_a["accuracy"] is None  # Dry-run tuyệt đối không tạo điểm giả
    assert report_a["capability_score"] is None
    assert report_a["plumbing_accuracy"] == 1.0
    assert report_a["capability_status"] == "PLUMBING_ONLY"  # Khẳng định rõ chỉ đo hạ tầng
    assert report_a["wilson_95_ci"] is None
    assert all(k in report_a["group_breakdown"] for k in (
        "A_MATH_FIDELITY", "B_ANAPHORA_GROUNDING", "C_RETRIEVAL_CITATION",
        "D_TOOL_AND_FILEOPS", "E_MASTER_COMMUNICATION"
    ))

    # Chạy Đề B
    report_b = runner.run_weekly_exam("B", dry_run=True)
    assert report_b["total_tasks"] == 20
    assert report_b["capability_status"] == "PLUMBING_ONLY"

    # Chạy thử live mode nối engine (mock urllib để kiểm thử luồng LIVE_EVALUATED không phụ thuộc daemon ngoại vi)
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"response": "Hệ thống an toàn 100/100"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        report_live = runner.run_weekly_exam("A", dry_run=False)
    assert report_live["capability_status"] == "LIVE_EVALUATED"

    # Kiểm tra tính toàn vẹn của Chained Ledger (prev_sha256 -> curr_sha256 qua 3 lần chạy)
    with open(ledger_file, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    assert len(entries) == 3
    assert entries[0]["prev_sha256"] == "0" * 64
    assert entries[1]["prev_sha256"] == entries[0]["curr_sha256"]
    assert entries[2]["prev_sha256"] == entries[1]["curr_sha256"]


def test_condition_5_exam_traces_immune_to_training_leakage(tmp_path):
    """Điều kiện 5: Trace từ Weekly Exam tuyệt đối bị chặn ở DatasetManager."""
    runner = WeeklyExamRunner(data_dir="data/eval", ledger_file=str(tmp_path / "ledger.jsonl"))
    report = runner.run_weekly_exam("A", dry_run=True)
    exam_id = report["exam_run_id"]
    assert "weekly_exam_run_A_" in exam_id

    # Thử lén nạp trace này vào DatasetManager (Training pipeline) -> Bị ném lỗi ngay
    dm = DatasetManager(seed_file=str(tmp_path / "seed.jsonl"), gold_file=str(tmp_path / "gold.jsonl"))

    with pytest.raises(ValueError, match="EXAM_TRACE_BLOCKLISTED"):
        dm.ingest_chunk_revision_as_label(
            chunk_id="chk_exam_leak",
            original_text="sai",
            edited_text="dung",
            source_mission_id=exam_id,
        )

    with pytest.raises(ValueError, match="EXAM_TRACE_BLOCKLISTED"):
        dm.harvest_trace_as_lora_sample(
            trace_id="lora_leak_01",
            instruction="Đáp án câu hỏi thi",
            output="3000 kg",
            source_mission_id=exam_id,
        )

    # Đảm bảo không bản ghi thi cử nào lọt vào gold dataset
    assert dm.load_gold_dataset() == []
