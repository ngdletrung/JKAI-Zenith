"""
Unit Tests for Phase R2: Benchmark Manifest & Ablation Matrix
File: tests/test_benchmark_manifest_and_ablation.py
"""

import pytest
from core.benchmarks.benchmark_manifest import (
    ExecutionMode,
    BenchmarkTask,
    BenchmarkManifest,
    BenchmarkReport
)
from core.benchmarks.ablation_matrix import (
    AblationTier,
    AblationConfig,
    ABLATION_CONFIGS,
    get_ablation_config,
    AblationComparisonEngine
)


def test_benchmark_task_integrity_and_hash():
    """Bảo đảm chữ ký SHA-256 bao trùm cả đề bài và rubric đánh giá."""
    task = BenchmarkTask(
        task_id="TASK-T1",
        domain="browser",
        prompt="Truy cập vietnamnet.vn và chụp ảnh màn hình",
        eval_rubric={"expected_files": ["eye_1.png"], "min_bytes": 100000}
    )
    assert len(task.task_hash) == 64
    assert task.verify_integrity() is True

    # Giả mạo rubric để làm lỏng tiêu chí
    tampered_task = BenchmarkTask(
        task_id="TASK-T1",
        domain="browser",
        prompt="Truy cập vietnamnet.vn và chụp ảnh màn hình",
        eval_rubric={"expected_files": []},  # Bị sửa tiêu chí
        task_hash=task.task_hash  # Giữ nguyên hash cũ
    )
    assert tampered_task.verify_integrity() is False


def test_manifest_sealing_and_tamper_detection():
    """Bảo đảm Manifest phát hiện bất kỳ thay đổi nào trong tập bài thi."""
    manifest = BenchmarkManifest(
        manifest_id="BM-2026-Q4",
        version="1.0.0",
        description="Standard evaluation suite for JKAI"
    )

    t1 = BenchmarkTask(
        task_id="T01",
        domain="file_ops",
        prompt="Ghi file cấu hình",
        eval_rubric={"syntax_ast": "valid"}
    )
    t2 = BenchmarkTask(
        task_id="T02",
        domain="terminal",
        prompt="Chạy kiểm thử pytest",
        eval_rubric={"exit_code": 0}
    )

    manifest.add_task(t1)
    manifest.add_task(t2)
    seal_hash = manifest.seal_manifest()

    assert len(seal_hash) == 64
    assert manifest.verify_manifest() is True

    # Cố tình sửa đổi đề bài sau khi đã niêm phong
    manifest.tasks["T01"].prompt = "Đã bị hacker sửa đổi"
    assert manifest.verify_manifest() is False


def test_execution_mode_separation():
    """Bảo đảm báo cáo phân tách minh bạch giữa LIVE_MODEL và SIMULATED."""
    rep_live = BenchmarkReport(
        report_id="REP-LIVE-01",
        manifest_id="BM-2026-Q4",
        manifest_hash="abc123hash",
        execution_mode=ExecutionMode.LIVE_MODEL,
        model_name="qwen2.5-coder:3b",
        ablation_tier="A4_JKAI_CANONICAL",
        results=[
            {"task_id": "T01", "verdict": "COMPLETE", "action_count": 3, "latency_ms": 1200.0},
            {"task_id": "T02", "verdict": "COMPLETE", "action_count": 2, "latency_ms": 950.0}
        ]
    )
    metrics = rep_live.calculate_summary_metrics()
    assert metrics["completion_rate_pct"] == 100.0
    assert metrics["actions_per_task"] == 2.5
    assert rep_live.execution_mode == ExecutionMode.LIVE_MODEL
    assert rep_live.to_dict()["execution_mode"] == "LIVE_MODEL"

    rep_sim = BenchmarkReport(
        report_id="REP-SIM-01",
        manifest_id="BM-2026-Q4",
        manifest_hash="abc123hash",
        execution_mode=ExecutionMode.SIMULATED,
        model_name="mock_reasoner",
        ablation_tier="A0_MODEL_ONLY"
    )
    assert rep_sim.execution_mode == ExecutionMode.SIMULATED


def test_ablation_matrix_configs():
    """Kiểm tra cấu hình 6 tầng cắt bỏ A0–A5."""
    assert len(ABLATION_CONFIGS) == 6
    a0 = get_ablation_config(AblationTier.A0_MODEL_ONLY)
    assert not a0.has_tools and not a0.has_memory and not a0.has_governor

    a1 = get_ablation_config(AblationTier.A1_MODEL_DIRECT_TOOLS)
    assert a1.has_tools and not a1.has_governor and not a1.has_verification

    a4 = get_ablation_config(AblationTier.A4_JKAI_CANONICAL)
    assert a4.has_tools and a4.has_memory and a4.has_governor and a4.has_verification and not a4.has_lora

    a5 = get_ablation_config(AblationTier.A5_JKAI_LORA)
    assert a5.has_lora and a5.has_verification


def test_ablation_governance_impact_calculation():
    """Tính toán chính xác mức cải thiện nhờ Runtime kiểm soát và phát hiện rủi ro unverified tool."""
    tier_reports = {
        AblationTier.A0_MODEL_ONLY: {"completion_rate_pct": 35.0},
        AblationTier.A1_MODEL_DIRECT_TOOLS: {"completion_rate_pct": 55.0, "false_positive_rate_pct": 28.0},
        AblationTier.A4_JKAI_CANONICAL: {"completion_rate_pct": 88.0}
    }
    engine = AblationComparisonEngine(tier_reports)
    impact = engine.evaluate_governance_impact()

    assert impact["governance_net_gain_pct"] == 53.0  # 88 - 35
    assert impact["tool_governor_gain_pct"] == 33.0   # 88 - 55
    assert impact["unverified_tool_false_positive_pct"] == 28.0


def test_ablation_lora_rejection_on_insufficient_gain():
    """Bác bỏ LoRA nếu không đem lại tăng trưởng thực chất so với A4."""
    tier_reports = {
        AblationTier.A4_JKAI_CANONICAL: {"completion_rate_pct": 88.0},
        AblationTier.A5_JKAI_LORA: {"completion_rate_pct": 87.5, "regressed_tasks_count": 0}
    }
    engine = AblationComparisonEngine(tier_reports)
    decision = engine.evaluate_lora_justification()

    assert decision["marginal_gain_pct"] == -0.5
    assert decision["lora_promoted"] is False
    assert decision["verdict"] == "REJECTED_INSUFFICIENT_MARGINAL_GAIN_OR_REGRESSION"


def test_ablation_lora_rejection_on_regression():
    """Bác bỏ LoRA nếu gây suy thoái (catastrophic forgetting) trên các tác vụ cơ sở."""
    tier_reports = {
        AblationTier.A4_JKAI_CANONICAL: {"completion_rate_pct": 85.0},
        AblationTier.A5_JKAI_LORA: {"completion_rate_pct": 90.0, "regressed_tasks_count": 2}
    }
    engine = AblationComparisonEngine(tier_reports)
    decision = engine.evaluate_lora_justification()

    assert decision["marginal_gain_pct"] == 5.0
    assert decision["regressed_tasks_count"] == 2
    assert decision["lora_promoted"] is False
    assert decision["verdict"] == "REJECTED_INSUFFICIENT_MARGINAL_GAIN_OR_REGRESSION"


def test_ablation_lora_promotion_on_clean_gain():
    """Chỉ thăng hạng LoRA khi có tăng trưởng thực chất VÀ không hồi quy."""
    tier_reports = {
        AblationTier.A4_JKAI_CANONICAL: {"completion_rate_pct": 85.0},
        AblationTier.A5_JKAI_LORA: {"completion_rate_pct": 92.5, "regressed_tasks_count": 0}
    }
    engine = AblationComparisonEngine(tier_reports)
    decision = engine.evaluate_lora_justification()

    assert decision["marginal_gain_pct"] == 7.5
    assert decision["regressed_tasks_count"] == 0
    assert decision["lora_promoted"] is True
    assert decision["verdict"] == "PROMOTED"
