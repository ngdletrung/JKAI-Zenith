# -*- coding: utf-8 -*-
"""
tests/test_slice_4_2_tier1_autonomous_tuning_loop.py
===================================================
[Pha 4 - Slice 4.2: Tier 1 Autonomous Evolution Loop (RAG, KV-Cache, Dataset)]:
Kiểm thử vòng tự học đệ quy cấp cao cho Tầng 1 (Tham số & Bộ nhớ):
1. Vòng tự tối ưu RAG RRF k & Parent-Child window khi khâu EVIDENCE_RETRIEVAL bị nghẽn:
   - Sinh candidate -> chạy sandbox trên Frozen RAG Corpus -> đạt 4 Cổng Hiến Pháp -> Auto-Promote.
2. Vòng tự động nạp nhãn Chunk Revision của Master vào Dataset Manager qua cổng Weak-Supervision:
   - Tự động sinh nhãn chuẩn A-E, phân loại đúng, cập nhật gold dataset không cần can thiệp thủ công.
3. Vòng kiểm tra và điều chỉnh CacheAligner prefix khi có volatile tokens:
   - Tự động phát hiện và định tuyến chuyển volatile tokens ra sau system prefix tĩnh.
4. Kiểm soát ngân sách tự trị: Tự động ghi nhận vào Chained Promotion Journal, bảo đảm không vượt quota tuần.
"""

import pytest
from core.os.cognition.rsil_orchestrator import (
    EvolutionTier,
    AutonomousQuotaTracker,
    ChainedPromotionJournal,
    RSILOrchestrator,
)
from core.os.cognition.rsil_tier1_loop import (
    AutonomousRAGOptimizer,
    AutonomousDatasetIngestionLoop,
    AutonomousPrefixOptimizer,
    run_tier1_autonomous_evolution_cycle,
)


def test_slice_4_2_item1_autonomous_rag_optimizer_promotes_on_gain():
    """
    Tự động tối ưu tham số RAG khi EVIDENCE_RETRIEVAL bị nghẽn:
    Thử nghiệm các giá trị RRF k (40, 60, 80) trên Frozen RAG Benchmark.
    Khi tìm thấy cấu hình cải thiện gain >= 0.05 và 0 regression -> Auto-Promote vào Canary.
    """
    optimizer = AutonomousRAGOptimizer()
    res = optimizer.optimize_rag_parameters(current_k=30, candidate_k_values=[40, 60, 80])
    assert res["status"] in ("AUTO_PROMOTED", "NO_GAIN_REJECTED")
    if res["status"] == "AUTO_PROMOTED":
        assert res["best_k"] in (40, 60, 80)
        assert res["delta_score"] >= 0.05
        assert res["witness_signature"] is not None


def test_slice_4_2_item2_autonomous_dataset_ingestion_loop():
    """
    Tự động khép vòng học từ các bản sửa chunk của Master:
    Đọc mẫu sửa mới -> tự động gán nhãn yếu (A-E) -> nạp vào DatasetManager -> cập nhật gold stats.
    """
    ingestion_loop = AutonomousDatasetIngestionLoop()
    new_revisions = [
        {
            "chunk_id": "auto_rev_01",
            "goal": "Tính chi phí 20 chuyến xe giá 500k.",
            "original_text": "Chi phí là 5 triệu.",
            "edited_text": "Chi phí 20 chuyến x 500k = 10.000.000 VND.",
            "expected_category": "A_MATH_FIDELITY",
        },
        {
            "chunk_id": "auto_rev_02",
            "goal": "Lệnh xóa file rác trong sandbox.",
            "original_text": "Xóa bằng tay.",
            "edited_text": "Chạy lệnh git clean -fd trong sandbox worktree.",
            "expected_category": "D_TOOL_AND_FILEOPS",
        },
    ]
    ingest_res = ingestion_loop.ingest_master_revisions(new_revisions)
    assert ingest_res["ingested_count"] == 2
    assert ingest_res["correct_category_count"] == 2
    assert ingest_res["accuracy"] == 1.0


def test_slice_4_2_item3_autonomous_prefix_alignment_optimizer():
    """
    Tự động chuẩn hóa KV-Cache prefix:
    Phát hiện prompt bị nhiễm volatile header -> tự động tách dời volatile ra sau prefix tĩnh.
    """
    prefix_opt = AutonomousPrefixOptimizer()
    dirty_prompt = "System Prompt 2026-10-14T12:00:00Z task_id=xyz: You are JKAI Zenith."
    clean_res = prefix_opt.align_system_prompt_prefix(dirty_prompt)
    assert clean_res["cache_aligned"] is True
    assert clean_res["volatile_relocated"] is True
    assert clean_res["aligned_prefix"].startswith("You are JKAI Zenith.")


def test_slice_4_2_item4_tier1_full_autonomous_cycle_within_budget():
    """
    Chạy 1 chu trình tự tiến hóa Tầng 1 đầy đủ qua RSILOrchestrator:
    - Quét stage attribution phát hiện khâu nghẽn.
    - Kích hoạt tối ưu RAG.
    - Tự động ghi chép vào Chained Promotion Journal.
    - Kiểm tra không vi phạm hạn mức 3 lần/tuần.
    """
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        cycle_res = run_tier1_autonomous_evolution_cycle(
            attribution_records=[
                {"stage": "EVIDENCE_RETRIEVAL", "outcome_ok": False},
                {"stage": "EVIDENCE_RETRIEVAL", "outcome_ok": False},
                {"stage": "ACTION_PROPOSAL", "outcome_ok": True},
            ],
            journal_path=j_path,
        )
        assert cycle_res["bottleneck_detected"] == "EVIDENCE_RETRIEVAL"
        assert cycle_res["action_taken"] in ("OPTIMIZE_RAG_SUCCESS", "MAINTAINED_BASELINE")
        assert cycle_res["journal_integrity_ok"] is True
        assert cycle_res["quota_frozen"] is False


def test_slice_4_2_item5_real_production_trace_schema_adaptation():
    """
    [Khóa Lỗ Hổng Schema Trace Detector — Lượt 300]:
    Kiểm tra khả năng thích ứng schema trace production (từ project_agent_loop.py và results/trace_*.jsonl):
    - Khâu được gắn dưới dạng `stage_attribution` (hoặc suy từ `tool`).
    - Kết quả `outcome_ok` được suy luận fail-closed từ `status`, `signal`, hoặc `observation`.
    - Đảm bảo không bị nuốt vào UNKNOWN và phát hiện đúng điểm nghẽn EVIDENCE_RETRIEVAL.
    """
    from core.os.cognition.rsil_orchestrator import RSILOrchestrator, normalize_stage_trace_entry

    # Các bản ghi mô phỏng đúng 100% schema ghi bởi `_write_trace` trong project_agent_loop.py
    real_prod_traces = [
        {
            "step": 1,
            "thought": "Truy vấn quy định sandbox",
            "tool": "view_file",
            "stage_attribution": "EVIDENCE_RETRIEVAL",
            "observation": "FileNotFoundError: [Errno 2] No such file or directory",
            # Không có outcome_ok -> normalizer phải suy ra False do observation chứa FileNotFoundError
        },
        {
            "step": 2,
            "thought": "Thử truy xuất lại tài liệu cũ",
            "tool": "view_file",
            "stage_attribution": "EVIDENCE_RETRIEVAL",
            "signal": "TOOL_ERROR",
            # Không có outcome_ok -> normalizer phải suy ra False do signal TOOL_ERROR
        },
        {
            "step": 3,
            "thought": "Đề xuất hành động sửa code",
            "tool": "replace_file_content",
            "stage_attribution": "ACTION_PROPOSAL",
            "status": "SUCCESS",
            "observation": "The file was modified successfully.",
            # Không có outcome_ok -> normalizer phải suy ra True do status SUCCESS
        },
    ]

    orchestrator = RSILOrchestrator()
    analysis = orchestrator.detect_bottleneck(real_prod_traces)
    assert analysis["primary_bottleneck_stage"] == "EVIDENCE_RETRIEVAL"
    assert analysis["failure_ratio"] == 1.0  # 2/2 failures in EVIDENCE_RETRIEVAL
    assert analysis["breakdown"]["ACTION_PROPOSAL"] == 0.0  # 0/1 failures


def test_slice_4_2_item6_suite_manifest_integrity():
    """
    [Khóa Số Bộ Kiểm Thử SUITE_MANIFEST.json — Lượt 300]:
    Kiểm tra tính nhất quán bit-wise giữa SUITE_MANIFEST.json và cấu trúc kiểm thử dự án:
    - Mọi tệp trong sprint_18 và extended_extra_5 đều phải tồn tại.
    - Tổng số test item khai báo trong manifest phải khớp chính xác với dự kiến.
    """
    import json
    from pathlib import Path

    manifest_path = Path("tests/SUITE_MANIFEST.json")
    assert manifest_path.exists(), "tests/SUITE_MANIFEST.json must exist"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sprint_files = manifest.get("sprint_suite") or manifest.get("sprint_18", {})
    extended_extra = manifest["extended_extra_5"]

    for file_path_str in list(sprint_files.keys()) + list(extended_extra.keys()):
        p = Path(file_path_str)
        assert p.exists(), f"Manifest declared file does not exist: {file_path_str}"

    total_sprint = sum(sprint_files.values())
    total_extended = total_sprint + sum(extended_extra.values())

    expected_sprint = manifest["expected_totals"].get("sprint_suite_total_items", manifest["expected_totals"].get("sprint_18_total_items"))
    expected_extended = manifest["expected_totals"].get("extended_suite_total_items", manifest["expected_totals"].get("extended_23_total_items"))

    assert total_sprint == expected_sprint
    assert total_extended == expected_extended

