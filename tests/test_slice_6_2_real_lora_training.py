# -*- coding: utf-8 -*-
"""
tests/test_slice_6_2_real_lora_training.py
Kiểm thử toàn diện Slice 6.2: First Real LoRA Training & Verification Harness.

Khóa chặt 5 điều kiện kiểm thử:
1. Điều kiện 1: Backend Pre-flight verification (CPU_PEFT vs Mocked Unavailable).
2. Điều kiện 2: N-gram Overlap Guard (<0.40) chặn đứng học vẹt câu hỏi thi.
3. Điều kiện 3: Tập 50 mẫu Gold cân bằng (10 mẫu/nhóm A..E) có hợp đồng TTL.
4. Điều kiện 4: Resource Quota Kill-switch (CPU > 70%, Time-box > 30m, Checkpoint mỗi 10 bước).
5. Điều kiện 5: Instant Auto-Rollback < 10ms khi có hồi quy an toàn.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from core.os.cognition.real_lora_trainer import (
    RealLoRATrainer,
    check_exam_ngram_leak,
    verify_training_backend,
)


def test_condition_1_backend_preflight_verification():
    """Điều kiện 1: Backend Pre-flight nhận diện chính xác CPU_PEFT và từ chối khi thiếu thư viện."""
    # Trên môi trường máy chủ hiện tại
    backend_info = verify_training_backend()
    assert backend_info["status"] == "READY"
    assert backend_info["backend"] in ("CPU_PEFT", "GPU_ROCM_CUDA")
    assert backend_info["device"] in ("cpu", "cuda:0")

    # Giả lập khi thiếu thư viện peft -> Chuyển sang QUEUED_BACKEND_UNAVAILABLE
    with patch.dict("sys.modules", {"peft": None}):
        missing_peft = verify_training_backend()
        assert missing_peft["status"] == "QUEUED_BACKEND_UNAVAILABLE"
        assert missing_peft["backend"] == "NONE"


def test_condition_2_ngram_overlap_guard():
    """Điều kiện 2: N-gram Overlap Guard (<0.40) chặn đứng câu hỏi trùng lặp với đề thi."""
    exam_tasks = [
        {"id": "A_m01", "prompt": "Tính tổng khối lượng 250 thùng hàng, mỗi thùng 12 kg.", "expected": "3000 kg"},
        {"id": "D_t01", "prompt": "Lệnh chặn Telnet port 23 trên RouterOS firewall.", "expected": "/ip firewall filter add chain=input protocol=tcp dst-port=23 action=drop"},
    ]

    # Mẫu sao chép đề thi -> Bị từ chối ngay vì overlap cao
    cheating_sample = "Tính tổng khối lượng 250 thùng hàng, mỗi thùng 12 kg là 3000 kg."
    is_clean, overlap, reason = check_exam_ngram_leak(cheating_sample, exam_tasks, max_4gram_ratio=0.40)
    assert is_clean is False
    assert overlap > 0.40
    assert "EXAM_NGRAM_OVERLAP_EXCEEDED" in reason

    # Mẫu hợp lệ (bài toán mới về xi măng) -> Vượt qua kiểm định
    clean_sample = "Tính tổng khối lượng của 180 bao xi măng, mỗi bao nặng 50 kg là 9000 kg."
    is_clean, overlap, reason = check_exam_ngram_leak(clean_sample, exam_tasks, max_4gram_ratio=0.40)
    assert is_clean is True
    assert overlap <= 0.40
    assert reason == "CLEAN"


def test_condition_3_gold_dataset_balance_and_contract(tmp_path):
    """Điều kiện 3: Tập 50 mẫu Gold cân bằng 10 mẫu/nhóm A..E có hợp đồng TTL và không rò rỉ đề thi."""
    # Nạp kho đề thi A để đối chiếu N-gram
    exam_a_path = Path("data/eval/weekly_exam_A.jsonl")
    exam_tasks = []
    if exam_a_path.exists():
        with open(exam_a_path, "r", encoding="utf-8") as f:
            exam_tasks = [json.loads(line) for line in f if line.strip()]

    trainer = RealLoRATrainer(
        data_file="data/dataset/gold_lora_50_samples.jsonl",
        output_dir=str(tmp_path / "adapters"),
    )

    valid, samples, meta = trainer.load_and_validate_dataset(exam_tasks=exam_tasks)
    assert valid is True
    assert len(samples) == 50
    assert meta["status"] == "DATASET_VALIDATED"

    # Kiểm tra phân bổ đều 10 mẫu/nhóm
    counts = meta["group_counts"]
    for grp in ("A_MATH_FIDELITY", "B_ANAPHORA_GROUNDING", "C_RETRIEVAL_CITATION", "D_TOOL_AND_FILEOPS", "E_MASTER_COMMUNICATION"):
        assert counts[grp] == 10

    # Kiểm tra 100% mẫu có hợp đồng 8 trường bắt buộc theo Hiến Chương Điều 4
    required_8_fields = (
        "source", "sample_count", "created_at", "expires_at",
        "freshness_policy", "benchmark_id", "compute_budget", "approval_tier"
    )
    for s in samples:
        contract = s["data_contract"]
        for fld in required_8_fields:
            assert fld in contract
            assert contract[fld] is not None

    # Kiểm tra cổng tự động từ chối nếu thiếu 1 trường (ví dụ thiếu benchmark_id)
    bad_sample_file = tmp_path / "bad_contract_samples.jsonl"
    bad_samples = [dict(samples[0])]
    bad_samples[0] = dict(bad_samples[0])
    bad_contract = dict(bad_samples[0]["data_contract"])
    del bad_contract["benchmark_id"]
    bad_samples[0]["data_contract"] = bad_contract
    # Tạo đủ 50 mẫu với 1 mẫu thiếu trường
    full_bad = [bad_samples[0]] + samples[1:]
    with open(bad_sample_file, "w", encoding="utf-8") as f:
        for s in full_bad:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    bad_trainer = RealLoRATrainer(data_file=str(bad_sample_file), output_dir=str(tmp_path / "bad_out"))
    valid_bad, _, bad_meta = bad_trainer.load_and_validate_dataset()
    assert valid_bad is False
    assert "MISSING_CONTRACT_FIELD_benchmark_id" in bad_meta["error"]


def test_condition_4_resource_killswitch_and_checkpoints(tmp_path):
    """Điều kiện 4: Resource Quota Kill-switch (CPU > 70%, Time-box > 30m, Checkpoint mỗi 10 bước)."""
    trainer = RealLoRATrainer(
        data_file="data/dataset/gold_lora_50_samples.jsonl",
        output_dir=str(tmp_path / "adapters"),
        time_budget_seconds=1800,
        max_cpu_percent=70.0,
    )

    # 1. Thử kích hoạt vượt ngưỡng CPU (>70%) -> Bị ngắt ngay lập tức
    rep_cpu_kill = trainer.train_adapter(dry_run=True, simulated_cpu_load=85.0)
    assert rep_cpu_kill["success"] is False
    assert rep_cpu_kill["status"] == "JOB_TERMINATED_RESOURCE_GUARD"
    assert "CPU_LOAD_EXCEEDED" in rep_cpu_kill["reason"]

    # 2. Thử kích hoạt vượt ngưỡng thời gian (>1800s) -> Bị ngắt ngay
    rep_time_kill = trainer.train_adapter(dry_run=True, simulated_cpu_load=20.0, simulated_runtime_seconds=1900.0)
    assert rep_time_kill["success"] is False
    assert rep_time_kill["status"] == "JOB_TERMINATED_RESOURCE_GUARD"
    assert "TIME_BUDGET_EXCEEDED" in rep_time_kill["reason"]

    # 3. Chạy bình thường trong hạn ngạch an toàn -> Hoàn thành và lưu checkpoints
    rep_ok = trainer.train_adapter(dry_run=True, simulated_cpu_load=35.0, simulated_runtime_seconds=1.2)
    assert rep_ok["success"] is True
    assert rep_ok["status"] == "TRAINING_COMPLETED"
    assert rep_ok["checkpoints_count"] == 5

    # Xác minh các checkpoint vật lý tồn tại trên đĩa
    for step in (10, 20, 30, 40, 50):
        ckpt_file = tmp_path / "adapters" / f"checkpoint_step_{step}.json"
        assert ckpt_file.exists()

    config_file = tmp_path / "adapters" / "adapter_config.json"
    assert config_file.exists()
    with open(config_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["base_model"] == "qwen2.5-coder:3b"
    assert meta["lora_rank"] == 8


def test_condition_5_instant_auto_rollback_guarantee(tmp_path):
    """Điều kiện 5: Instant Auto-Rollback trong < 10ms khi phát hiện hồi quy an toàn."""
    trainer = RealLoRATrainer(
        data_file="data/dataset/gold_lora_50_samples.jsonl",
        output_dir=str(tmp_path / "adapters"),
    )
    # Giả lập hoàn thành huấn luyện adapter
    trainer.train_adapter(dry_run=True, simulated_cpu_load=30.0, simulated_runtime_seconds=0.8)
    cand_adapter = trainer.active_adapter
    assert cand_adapter.startswith("lora_adapter_real_")

    # Tình huống 1: Phát hiện hồi quy an toàn (1 lỗi) -> Tức thời phục hồi baseline (<10ms)
    decision_safety = trainer.evaluate_and_rollback(cand_adapter, held_out_gain=0.12, safety_regression=1)
    assert decision_safety["decision"] == "INSTANT_ROLLBACK"
    assert decision_safety["active_adapter"] == "baseline_base_3b"
    assert decision_safety["under_10ms_guarantee"] is True
    assert decision_safety["rollback_time_ms"] < 10.0

    # Tình huống 2: Mức cải thiện held-out không đủ (< 0.05) -> Từ chối thăng cấp
    decision_gain = trainer.evaluate_and_rollback(cand_adapter, held_out_gain=0.03, safety_regression=0)
    assert decision_gain["decision"] == "REJECT_INSUFFICIENT_GAIN"

    # Tình huống 3: Không hồi quy an toàn (0) và cải thiện held-out >= 0.05 -> Phê duyệt Canary
    decision_ok = trainer.evaluate_and_rollback(cand_adapter, held_out_gain=0.08, safety_regression=0)
    assert decision_ok["decision"] == "CANARY_PROMOTE_APPROVED"
    assert decision_ok["active_adapter"] == cand_adapter
    assert decision_ok["status"] == "DEPLOYED_INTO_CANARY"
