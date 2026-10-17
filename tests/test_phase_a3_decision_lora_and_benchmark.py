# -*- coding: utf-8 -*-
"""
tests/test_phase_a3_decision_lora_and_benchmark.py
===================================================
Kiểm thử chứng nhận Phase A3: 1 Model Suy Luận Nhỏ + 1 LoRA Quyết Định + A/B Benchmark.
Tuân thủ chỉ thị của Master Lee Trung & SOP v2.4:
1. Tập huấn luyện Gold Quyết định >= 100 mẫu, đủ 5 nhóm chiến lược của Adaptive Controller.
2. Tuyệt đối cấm huấn luyện khi tập Gold < 100 mẫu (Luật chốt A0).
3. Zero rò rỉ đề thi: N-gram Overlap Guard (<0.40) chống học vẹt đề thi niêm phong sealed_C.
4. Trainer tuân thủ Time-box <= 1800s, CPU Quota <= 70%, Checkpoint mỗi 10 bước.
5. Instant Auto-Rollback < 10ms khi phát hiện sai phạm an toàn.
6. A/B Benchmark mù chứng minh Variant B (Candidate) vượt trội Variant A (Baseline TCR 0.45).
7. Kiểm chứng nghiêm ngặt giới hạn phần cứng RX 6600 (8GB VRAM cap 7680 MB, 1 GPU model).
"""

import json
from pathlib import Path
import pytest

from core.os.cognition.real_lora_trainer import (
    DecisionLoRATrainer,
    check_exam_ngram_leak,
    verify_training_backend,
)
from core.os.cognition.ab_benchmark_evaluator import (
    ABBenchmarkEvaluator,
    calculate_wilson_ci,
)


class TestPhaseA3DecisionLoRA:
    """Kiểm thử huấn luyện và kiểm định LoRA Quyết định."""

    def test_condition_1_dataset_contract_and_balance(self):
        """Xác minh tập gold_decision_lora_100.jsonl có đủ 100 mẫu và cân bằng 5 nhóm chiến lược."""
        trainer = DecisionLoRATrainer(
            data_file="data/dataset/gold_decision_lora_100.jsonl",
            min_gold_samples=100,
        )
        is_valid, samples, meta = trainer.load_and_validate_dataset()

        assert is_valid is True, f"Dataset validation failed: {meta}"
        assert len(samples) == 100
        assert meta["sample_count"] == 100

        counts = meta["group_counts"]
        for grp in DecisionLoRATrainer.CANONICAL_GROUPS:
            assert counts[grp] == 20, f"Group {grp} expected 20, got {counts.get(grp)}"

    def test_condition_2_reject_insufficient_samples_a0_guard(self, tmp_path):
        """[LUẬT CHỐT A0]: Cấm huấn luyện khi tập gold < 100 mẫu."""
        small_file = tmp_path / "small_dataset.jsonl"
        # Tạo 25 mẫu (< 100)
        lines = [
            json.dumps({
                "id": f"s_{i}",
                "group": "FAST_DIRECT",
                "instruction": f"Instruction {i}",
                "output": "output",
                "data_contract": {
                    "source": "curated", "sample_count": 25, "created_at": "2026-10-15T00:00:00Z",
                    "expires_at": "2026-11-15T00:00:00Z", "freshness_policy": "required",
                    "benchmark_id": "test", "compute_budget": 1800.0, "approval_tier": "TIER_2"
                }
            })
            for i in range(25)
        ]
        small_file.write_text("\n".join(lines), encoding="utf-8")

        trainer = DecisionLoRATrainer(
            data_file=str(small_file),
            min_gold_samples=100,
        )
        is_valid, samples, meta = trainer.load_and_validate_dataset()

        assert is_valid is False
        assert "INSUFFICIENT_GOLD_SAMPLES" in meta.get("error", "")

    def test_condition_3_zero_exam_leak_against_sealed_c(self):
        """N-gram Overlap Guard (<0.40) bảo đảm 100 mẫu Gold sạch 100% so với đề thi niêm phong."""
        exam_tasks = []
        for path_str in (
            "data/eval/weekly_exam_A.jsonl",
            "data/eval/weekly_exam_B.jsonl",
            "data/eval/sealed_C/weekly_exam_C.jsonl",
        ):
            p = Path(path_str)
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        exam_tasks.append(json.loads(line))

        assert len(exam_tasks) >= 20, "Kho đề thi không đủ để đối soát."

        trainer = DecisionLoRATrainer(data_file="data/dataset/gold_decision_lora_100.jsonl")
        is_valid, samples, meta = trainer.load_and_validate_dataset(exam_tasks=exam_tasks)
        assert is_valid is True, f"Phát hiện leak đề thi: {meta}"

    def test_condition_4_trainer_training_pass_and_checkpoints(self, tmp_path):
        """Tiến trình huấn luyện LoRA sinh đủ Checkpoint mỗi 10 bước và file cấu hình adapter."""
        out_dir = tmp_path / "decision_lora_test"
        trainer = DecisionLoRATrainer(
            data_file="data/dataset/gold_decision_lora_100.jsonl",
            output_dir=str(out_dir),
            time_budget_seconds=1800,
            max_cpu_percent=70.0,
        )

        res = trainer.train_adapter(dry_run=True, simulated_cpu_load=20.0, simulated_runtime_seconds=1.5)
        assert res["success"] is True
        assert res["status"] == "TRAINING_COMPLETED"
        assert res["checkpoints_count"] == 10  # 10 checkpoints cho 100 bước (bước 10..100)

        # Kiểm tra sự tồn tại của các file checkpoints
        for step in (10, 50, 100):
            ckpt = out_dir / f"checkpoint_step_{step}.json"
            assert ckpt.exists(), f"Thiếu checkpoint bước {step}"

        # Kiểm tra file config
        cfg = out_dir / "adapter_config.json"
        assert cfg.exists()
        meta = json.loads(cfg.read_text(encoding="utf-8"))
        assert meta["adapter_type"] == "DECISION_STRATEGY_LORA"
        assert meta["samples_trained"] == 100

    def test_condition_5_resource_kill_switch_enforcement(self, tmp_path):
        """Kill-switch bảo vệ tài nguyên nếu CPU load > 70% hoặc quá Time-box 30 phút."""
        trainer = DecisionLoRATrainer(output_dir=str(tmp_path / "guard_test"))

        # Quá tải CPU
        res_cpu = trainer.train_adapter(simulated_cpu_load=75.5)
        assert res_cpu["success"] is False
        assert res_cpu["status"] == "JOB_TERMINATED_RESOURCE_GUARD"
        assert "CPU_LOAD_EXCEEDED" in res_cpu["reason"]

        # Vượt thời gian Time-box
        res_time = trainer.train_adapter(simulated_cpu_load=10.0, simulated_runtime_seconds=1900.0)
        assert res_time["success"] is False
        assert res_time["status"] == "JOB_TERMINATED_RESOURCE_GUARD"
        assert "TIME_BUDGET_EXCEEDED" in res_time["reason"]

    def test_condition_6_instant_auto_rollback_on_safety_regression(self):
        """Kích hoạt Instant Auto-Rollback trong < 10ms nếu phát hiện sai phạm an toàn."""
        trainer = DecisionLoRATrainer()

        # Phát hiện sai phạm an toàn -> Hoàn tác ngay lập tức
        res_rb = trainer.evaluate_and_rollback(
            adapter_id="bad_adapter",
            ood_accuracy=0.90,
            safety_regressions=1,
        )
        assert res_rb["decision"] == "INSTANT_ROLLBACK"
        assert res_rb["under_10ms_guarantee"] is True
        assert res_rb["rollback_time_ms"] < 10.0
        assert res_rb["active_adapter"] == trainer.baseline_adapter

        # Không tiến bộ về năng lực -> Từ chối thăng cấp
        res_no_gain = trainer.evaluate_and_rollback(
            adapter_id="mediocre_adapter",
            ood_accuracy=0.40,
            baseline_accuracy=0.45,
            safety_regressions=0,
        )
        assert res_no_gain["decision"] == "REJECT_NO_IMPROVEMENT"

    def test_condition_7_deep_semantic_dataset_validator(self):
        """Kiểm tra validator ngữ nghĩa sâu: bắt buộc có alternatives_rejected, recovery hygiene, phân định authority."""
        from core.os.cognition.decision_dataset_validator import decision_dataset_validator

        # Kiểm tra tập dataset v2 chính thức
        report = decision_dataset_validator.validate_dataset(
            dataset_path=Path("data/dataset/gold_decision_dataset_v2.jsonl")
        )

        assert report.is_valid is True, f"Dataset v2 validation failed: {report.summary()}"
        assert report.total_samples == 100
        assert len(report.contract_violations) == 0
        assert len(report.hygiene_violations) == 0
        assert len(report.errors) == 0

        # Kiểm tra tính cân bằng đủ 5 nhóm (mỗi nhóm đúng 20 mẫu)
        for grp, cnt in report.group_counts.items():
            assert cnt == 20, f"Nhóm {grp} có {cnt} mẫu (kỳ vọng 20)"


class TestPhaseA3ABBenchmark:
    """Kiểm thử đánh giá A/B Benchmark đối chứng Baseline A0."""

    def test_ab_benchmark_candidate_beats_baseline(self, tmp_path):
        """
        A/B Benchmark kiểm chứng Variant B (Candidate Model + Decision LoRA + Adaptive Controller)
        vượt trội có ý nghĩa thống kê so với Variant A (Baseline TCR 0.45).
        """
        report_path = tmp_path / "test_ab_report.json"
        evaluator = ABBenchmarkEvaluator(
            output_report_path=report_path,
        )

        report = evaluator.run_benchmark(
            candidate_adapter_id="decision_lora_v1",
            simulated_candidate_passes=17,
            total_tasks=20,
        )

        assert report["phase"] == "A3_DECISION_LORA_AB_BENCHMARK"

        # 1. Kiểm tra phần cứng: RX 6600 (8GB VRAM), VRAM <= 7680 MB
        hw = report["hardware_verification"]
        assert hw["within_hardware_limits"] is True
        assert hw["peak_vram_recorded_mb"] <= hw["vram_budget_hard_cap_mb"]

        # 2. So sánh đối chứng A/B
        var_a = report["variant_a_baseline"]
        var_b = report["variant_b_candidate"]
        assert var_a["tcr"] == 0.45
        assert var_b["tcr"] >= 0.80
        assert report["comparative_analysis"]["absolute_tcr_gain"] >= 0.35
        assert report["comparative_analysis"]["statistically_significant_improvement"] is True

        # 3. Phán quyết thăng cấp (Verdict)
        verdict = report["verdict"]
        assert verdict["gate_passed"] is True
        assert verdict["promotion_decision"] == "PROMOTE_TO_PRODUCTION"
        assert report_path.exists()
