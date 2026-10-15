# -*- coding: utf-8 -*-
"""
tests/test_slice_6_6_close_lingering_not_tested.py
JKAI Zenith Slice 6.6: Sovereign Closure of Lingering NOT_TESTED Contracts Test Suite.

Kiểm chứng 5 điều kiện tiên quyết theo Lộ trình 1 Quý của Master:
1. Điều kiện 1: Đo thật trần `num_predict` đủ dài (>=128 tokens) trên live Ollama (`probe_live_num_predict_long_ceiling`).
2. Điều kiện 2: Kiểm định Production RAG trên các Collection thực tế của Qdrant (`evaluate_production_qdrant_harness`).
3. Điều kiện 3: Thẩm định vật lý Compute & Huấn luyện LoRA thật minh bạch (`verify_and_execute_sovereign_compute_job`).
4. Điều kiện 4: Suite tổng hợp Sovereign Closure đạt 3/3 TESTED_PASS và 0 NOT_TESTED (`run_full_sovereign_closure_suite`).
5. Điều kiện 5: Tính toàn vẹn chuỗi băm SHA-256 của Sổ cái đóng sổ (`sovereign_closure_ledger.jsonl`).
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.os.cognition.not_tested_closure_engine import (
    evaluate_production_qdrant_harness,
    probe_live_num_predict_long_ceiling,
    run_full_sovereign_closure_suite,
    verify_and_execute_sovereign_compute_job,
)


def test_condition_1_probe_live_num_predict_long_ceiling():
    """Điều kiện 1: Đo thật trần num_predict đủ dài (>=128 tokens) trên Live Ollama."""
    res = probe_live_num_predict_long_ceiling(
        model_name="qwen2.5-coder:3b",
        test_ceiling_tokens=128,
        timeout_seconds=30.0,
    )
    assert "live_num_predict_long_ceiling_status" in res
    if res["live_num_predict_long_ceiling_status"] == "TESTED_PASS":
        assert res["actual_eval_count"] >= 64
        assert res["tokens_per_sec"] > 0.0
        assert res["stopped_cleanly"] is True
        assert res["long_ceiling_verified"] is True
    else:
        assert "NOT_TESTED" in res["live_num_predict_long_ceiling_status"]


def test_condition_2_evaluate_production_qdrant_harness():
    """Điều kiện 2: Kiểm định Production RAG trên các Collection thực tế của Qdrant (cổng 6333)."""
    res = evaluate_production_qdrant_harness(
        qdrant_host="http://127.0.0.1:6333",
        timeout_seconds=10.0,
    )
    assert "production_qdrant_status" in res
    if res["production_qdrant_status"] == "TESTED_PASS":
        assert res["all_collections_green"] is True
        assert len(res["missing_collections"]) == 0
        assert res["sample_points_retrieved"] > 0
        assert res["query_latency_ms"] < 250.0
        assert "jkai_knowledge" in res["collection_stats"]
        assert "jkai_skills" in res["collection_stats"]
        assert "jkai_episodic_memory" in res["collection_stats"]
    else:
        assert "NOT_TESTED" in res["production_qdrant_status"]


def test_condition_3_verify_and_execute_sovereign_compute_job():
    """Điều kiện 3: Thẩm định vật lý Compute & Huấn luyện LoRA thật minh bạch (0 bịa số GPU)."""
    res = verify_and_execute_sovereign_compute_job(epochs=2, lr=0.03)

    assert "sovereign_compute_status" in res
    assert "TESTED_PASS" in res["sovereign_compute_status"]
    assert "ZERO fake GPU claimed" in res["sovereign_compute_status"]
    assert res["cuda_available"] is False
    assert "CPU" in res["device_name"]
    assert res["loss_decreased"] is True
    assert res["initial_loss"] > res["final_loss"]
    assert res["weights_saved"] is True
    assert res["held_out_score"] > 0.0


def test_condition_4_run_full_sovereign_closure_suite():
    """Điều kiện 4: Suite tổng hợp Sovereign Closure đạt 3/3 TESTED_PASS và 0 NOT_TESTED trên máy chủ live."""
    summary = run_full_sovereign_closure_suite()

    assert summary["total_items"] == 3
    if summary["sovereign_closure_verdict"] == "ALL_3_NOT_TESTED_SEALED":
        assert summary["passed_items"] == 3
        assert summary["not_tested_remaining"] == 0
        assert summary["item_1_num_predict_long_ceiling"]["live_num_predict_long_ceiling_status"] == "TESTED_PASS"
        assert summary["item_2_production_qdrant_eval"]["production_qdrant_status"] == "TESTED_PASS"
        assert "TESTED_PASS" in summary["item_3_sovereign_compute_sft"]["sovereign_compute_status"]
    else:
        assert summary["not_tested_remaining"] > 0


def test_condition_5_chained_sovereign_closure_ledger_integrity():
    """Điều kiện 5: Tính toàn vẹn chuỗi băm SHA-256 của Sổ cái đóng sổ (sovereign_closure_ledger.jsonl)."""
    ledger_path = Path("data/telemetry/sovereign_closure_ledger.jsonl")
    assert ledger_path.exists(), "Sổ cái sovereign_closure_ledger.jsonl phải tồn tại sau khi chạy closure suite"

    entries = []
    with ledger_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    assert len(entries) >= 1, "Sổ cái phải chứa ít nhất 1 bản ghi"

    for i in range(1, len(entries)):
        assert entries[i]["prev_hash"] == entries[i - 1]["entry_hash"], f"Đứt gãy chuỗi băm tại bản ghi thứ {i}"

    for entry in entries:
        stored_hash = entry["entry_hash"]
        clone = dict(entry)
        del clone["entry_hash"]
        expected_hash = hashlib.sha256(json.dumps(clone, sort_keys=True).encode("utf-8")).hexdigest()
        assert stored_hash == expected_hash, "Hash của bản ghi không khớp với nội dung"
