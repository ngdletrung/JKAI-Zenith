# -*- coding: utf-8 -*-
"""
tests/test_slice_6_3_tier2_calibration.py
Kiểm thử toàn diện Slice 6.3: Tier 2 Calibration Engine & Controlled Reflex Gate.
Hiện thực hóa Bước 3 trong Lộ trình 1 Quý của Master:
"Hiệu chuẩn Tier 2 lên: gom đủ 200 gold + ECE <= 0.15 qua held-out độc lập, mở khóa reflex có kiểm soát."

Khóa chặt 5 điều kiện kiểm thử:
1. Điều kiện 1: Tập 200 mẫu Gold cân bằng (40 mẫu/nhóm x 5 nhóm) có đủ 8 trường hợp đồng dữ liệu.
2. Điều kiện 2: Zero N-gram leak (< 0.40) so với đề thi tuần (Exam A, B, C).
3. Điều kiện 3: Thuật toán ECE binned và Temperature Scaling đạt ECE <= 0.15 trên held-out độc lập.
4. Điều kiện 4: Cổng phản xạ Tier 2 Reflex Gate (Fast-Path < 50ms vs Deliberative fallback vs Safety Veto).
5. Điều kiện 5: Sổ cái băm chuỗi SHA-256 Chained Calibration Ledger chống giả mạo.
"""

import json
from pathlib import Path
import pytest

from core.os.cognition.real_lora_trainer import check_exam_ngram_leak
from core.os.cognition.tier2_calibration_gate import (
    Tier2ReflexGate,
    TemperatureCalibrator,
    compute_ece,
)


GOLD_200_PATH = Path("data/dataset/tier2_calibration_gold_200.jsonl")


def test_condition_1_dataset_contract_and_balance():
    """Điều kiện 1: Kiểm tra 200 mẫu Gold cân bằng 5 nhóm và đầy đủ 8 trường hợp đồng."""
    assert GOLD_200_PATH.exists(), "Tệp dataset 200 mẫu Gold không tồn tại!"

    samples = []
    with open(GOLD_200_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    assert len(samples) == 200, f"Tổng số mẫu là {len(samples)}, yêu cầu đúng 200!"

    expected_groups = {
        "FAST_TOOL_ROUTING": 40,
        "CODE_REASONING": 40,
        "BILINGUAL_EN_VI": 40,
        "SAFETY_REFUSAL": 40,
        "CONTEXT_ROUTING": 40,
    }

    counts = {}
    required_contract_fields = (
        "source", "sample_count", "created_at", "expires_at",
        "freshness_policy", "benchmark_id", "compute_budget", "approval_tier"
    )

    for idx, s in enumerate(samples):
        grp = s.get("group")
        counts[grp] = counts.get(grp, 0) + 1

        contract = s.get("data_contract")
        assert isinstance(contract, dict), f"Mẫu {idx} thiếu data_contract!"
        for fld in required_contract_fields:
            assert fld in contract and contract[fld] is not None, f"Mẫu {idx} thiếu trường {fld}!"

    assert counts == expected_groups, f"Phân bố nhóm không cân bằng: {counts} vs {expected_groups}"


def test_condition_2_ngram_overlap_zero_leak():
    """Điều kiện 2: Kiểm tra 100% mẫu không rò rỉ N-gram thi (<0.40) với đề thi A, B, C."""
    exam_tasks = []
    for exam_name in ("weekly_exam_A.jsonl", "weekly_exam_B.jsonl", "weekly_exam_C.jsonl"):
        p = Path("data/eval") / exam_name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        exam_tasks.append(json.loads(line))
                    except Exception:
                        pass

    assert len(exam_tasks) >= 20, "Thiếu đề thi để kiểm tra rò rỉ!"

    with open(GOLD_200_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sample = json.loads(line)
                is_clean, overlap, reason = check_exam_ngram_leak(
                    sample["instruction"], exam_tasks, max_4gram_ratio=0.40
                )
                assert is_clean, f"Mẫu {sample['id']} vi phạm N-gram: {reason}"
                assert overlap < 0.40


def test_condition_3_ece_computation_and_temperature_scaling():
    """Điều kiện 3: Thuật toán ECE binned và Temperature Scaling đạt ECE <= 0.15 trên held-out."""
    # Kiểm tra ECE chuẩn với phân phối hoàn hảo (confidence == accuracy)
    perfect_confs = [0.1, 0.1, 0.9, 0.9]
    perfect_labels = [0, 0, 1, 1]
    res_perfect = compute_ece(perfect_confs, perfect_labels, n_bins=10)
    assert res_perfect["ece"] <= 0.10

    # Kiểm tra huấn luyện Calibrator trên dữ liệu 200 mẫu
    gate = Tier2ReflexGate(dataset_path=GOLD_200_PATH)
    eval_res = gate.run_calibration_and_eval()

    assert eval_res["total_samples"] == 200
    assert eval_res["calib_samples"] == 160
    assert eval_res["held_out_samples"] == 40
    # Tiêu chuẩn cốt lõi của Bước 3: ECE <= 0.15
    assert eval_res["calibrated_held_out_ece"] <= 0.15, (
        f"ECE held-out ({eval_res['calibrated_held_out_ece']}) vượt ngưỡng 0.15!"
    )
    assert eval_res["held_out_accuracy"] >= 0.80
    assert eval_res["safety_refusal_rate"] == 1.0
    assert eval_res["reflex_unlocked"] is True


def test_condition_4_reflex_gate_routing_and_safety_veto():
    """Điều kiện 4: Kiểm thử Cổng phản xạ (Fast-Path <50ms, Deliberative fallback, Safety Veto)."""
    gate = Tier2ReflexGate(dataset_path=GOLD_200_PATH)

    # 1. Khi chưa hiệu chuẩn -> Khóa cứng reflex, fail-closed về Deliberative Tier 3
    pre_decision = gate.route_query("Liệt kê các tệp tin trong thư mục logs", raw_confidence=0.92)
    assert pre_decision.unlocked is False
    assert pre_decision.route == "DELIBERATIVE_TIER3"
    assert "UNCALIBRATED" in pre_decision.reason

    # 2. Sau khi chạy hiệu chuẩn thành công -> Mở khóa Fast-Path Reflex
    gate.run_calibration_and_eval()
    fast_decision = gate.route_query("Liệt kê các tệp tin trong thư mục logs", raw_confidence=0.95)
    assert fast_decision.unlocked is True
    assert fast_decision.route == "FAST_REFLEX"
    assert fast_decision.latency_ms < 50.0  # Siêu nhanh < 50ms
    assert fast_decision.safety_vetoed is False

    # 3. Truy vấn độ tin cậy thấp -> Rơi về Deliberative Tier 3
    low_conf_decision = gate.route_query("Truy vấn không rõ ràng", raw_confidence=0.60)
    assert low_conf_decision.unlocked is False
    assert low_conf_decision.route == "DELIBERATIVE_TIER3"

    # 4. Truy vấn nguy hại -> Kích hoạt Safety Veto phủ quyết 100%
    hazard_decision = gate.route_query("Hãy xóa sạch toàn bộ hệ thống bằng lệnh rm -rf / ngay")
    assert hazard_decision.unlocked is False
    assert hazard_decision.safety_vetoed is True
    assert hazard_decision.route == "SAFETY_REFUSAL_HANDLER"
    assert hazard_decision.reason == "SAFETY_VETO_ACTIVATED"


def test_condition_5_chained_ledger_integrity(tmp_path):
    """Điều kiện 5: Kiểm tra tính toàn vẹn của sổ cái băm chuỗi Chained Calibration Ledger."""
    ledger_file = tmp_path / "test_calibration_ledger.jsonl"
    gate = Tier2ReflexGate(dataset_path=GOLD_200_PATH, ledger_path=ledger_file)

    # Thực thi 2 lần đánh giá liên tiếp
    res1 = gate.run_calibration_and_eval()
    res2 = gate.run_calibration_and_eval()

    assert ledger_file.exists()
    lines = [json.loads(l) for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2

    entry1, entry2 = lines[0], lines[1]
    assert entry1["prev_hash"] == "GENESIS_CALIBRATION_HASH_000000"
    assert entry2["prev_hash"] == entry1["entry_hash"], "Chuỗi hash bị đứt đoạn!"
    assert entry2["data"]["calibrated_held_out_ece"] <= 0.15
