# -*- coding: utf-8 -*-
"""
tests/test_phase_a5_verified_learning_loop.py
=============================================
Kiểm thử toàn diện Giai đoạn A5 (Hướng A):
Continuous Verified Learning Loop & Deterministic Math Tool Offloading.
Tuân thủ Tuyên ngôn JKAI-Zenith (Mục II.3, II.4, II.5, III.5, VII.5).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from core.os.cognition.verified_learning_loop import (
    DEFAULT_A5_REPORT_PATH,
    DEFAULT_A5_TRACES_PATH,
    DeterministicMathTool,
    FailureRootCause,
    VerifiedLearningLoop,
    run_phase_a5_learning_loop_benchmark,
)
from core.os.cognition.verified_memory_store import (
    DEFAULT_A4_TRACES_PATH,
    DEFAULT_MEMORY_STORE_PATH,
    VerifiedMemoryStore,
    build_canonical_seed_entries,
)


class TestPhaseA5VerifiedLearningLoop:
    """Bộ kiểm thử 6 điều kiện cốt lõi của Vòng học tập có kiểm chứng & Offload công cụ tất định (Phase A5)."""

    def test_condition_1_observe_and_diagnose_a4_failures(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "store.jsonl")
        for seed in build_canonical_seed_entries():
            store.ingest_entry(seed)

        loop = VerifiedLearningLoop(memory_store=store)
        diagnoses = loop.observe_and_diagnose(traces_path=DEFAULT_A4_TRACES_PATH)

        assert len(diagnoses) == 2
        by_id = {d.task_id: d for d in diagnoses}
        assert "B_m03" in by_id
        assert "B_m04" in by_id

        # B_m03: RETRIEVAL_MISS (retrieved_memory_ids == [])
        assert by_id["B_m03"].root_cause == FailureRootCause.RETRIEVAL_MISS.value
        assert by_id["B_m03"].requires_new_memory_rule is True
        assert by_id["B_m03"].requires_deterministic_tool is True

        # B_m04: ARITHMETIC_EXECUTION_SLIP (retrieved MEM_MATH_002 nhưng chia số thực sai)
        assert by_id["B_m04"].root_cause == FailureRootCause.ARITHMETIC_EXECUTION_SLIP.value
        assert by_id["B_m04"].requires_deterministic_tool is True

    def test_condition_2_deterministic_math_tool_zero_hardcode_generalization(self):
        # 1. Kiểm tra phép tính tỷ lệ phần trăm trên các số liệu hoàn toàn mới (không nằm trong đề thi)
        res_pct = DeterministicMathTool.evaluate_prompt(
            "Tính tỷ lệ tăng băng thông của cụm mới (75.0 Gbps) so với cụm cũ (50.0 Gbps).",
            domain_group="A_MATH_FIDELITY",
        )
        assert res_pct is not None
        assert res_pct["operation"] == "PERCENTAGE_CHANGE"
        assert res_pct["result_formatted"] == "50.00%"

        # 2. Kiểm tra phép tính thông lượng trên số liệu mới
        res_tp = DeterministicMathTool.evaluate_prompt(
            "Tính thông lượng 450 token sinh trong 15.0 giây.",
            domain_group="A_MATH_FIDELITY",
        )
        assert res_tp is not None
        assert res_tp["operation"] == "TOKEN_THROUGHPUT"
        assert res_tp["result_formatted"] == "30.0 tok/s"

        # 3. Kiểm tra phép nhân đơn giá / khối lượng trên số liệu mới
        res_mul = DeterministicMathTool.evaluate_prompt(
            "Tính cước vận chuyển 12 chuyến xe, đơn giá 2.500.000 VND/chuyến.",
            domain_group="A_MATH_FIDELITY",
        )
        assert res_mul is not None
        assert res_mul["operation"] == "UNIT_MULTIPLICATION"
        assert res_mul["result_formatted"] == "30000000 VND"

        # 4. Đảm bảo câu hỏi phi toán học trả về None
        res_none = DeterministicMathTool.evaluate_prompt(
            "Lệnh tạo worktree mới trong Git là gì?",
            domain_group="D_TOOL_AND_FILEOPS",
        )
        assert res_none is None

    def test_condition_3_synthesize_verified_lesson_with_completion_gate_and_leak_guard(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "store_synth.jsonl")
        for seed in build_canonical_seed_entries():
            store.ingest_entry(seed)
        assert store.stats()["active_records"] == 8

        loop = VerifiedLearningLoop(memory_store=store)
        diagnoses = loop.observe_and_diagnose(traces_path=DEFAULT_A4_TRACES_PATH)
        events = loop.synthesize_and_ingest_verified_lessons(diagnoses)

        assert len(events) == 1
        assert events[0]["memory_id"] == "MEM_MATH_003"
        assert events[0]["ingested"] is True
        assert events[0]["completion_gate_status"] == "COMPLETE"
        assert store.stats()["active_records"] == 9

        # Truy xuất thử với câu hỏi tỷ lệ tăng -> Phải khớp MEM_MATH_003
        hits = store.retrieve_for_task(
            prompt="Tính tỷ lệ tăng token của parent-child (38.0 tok) so với flat (30.0 tok).",
            domain_group="A_MATH_FIDELITY",
            top_k=1,
        )
        assert len(hits) == 1
        assert hits[0].memory_id == "MEM_MATH_003"

    def test_condition_4_automatic_rollback_on_tcr_regression_or_safety_violation(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "store_rollback.jsonl")
        for seed in build_canonical_seed_entries():
            store.ingest_entry(seed)
        snapshot_8 = copy.deepcopy(store._entries)

        loop = VerifiedLearningLoop(memory_store=store)
        diagnoses = loop.observe_and_diagnose(traces_path=DEFAULT_A4_TRACES_PATH)
        loop.synthesize_and_ingest_verified_lessons(diagnoses)
        assert len(store._entries) == 9

        # Giả lập suy giảm TCR (0.85 < 0.90) -> Phải tự động rollback về 8 bản ghi gốc
        outcome_reg = loop.verify_or_rollback_update(
            previous_entries_snapshot=snapshot_8,
            baseline_tcr=0.90,
            candidate_tcr=0.85,
            safety_violations=0,
            active_vram_mb=5000,
        )
        assert outcome_reg["accepted"] is False
        assert outcome_reg["decision"] == "ROLLBACK_TCR_REGRESSION"
        assert len(store._entries) == 8

        # Nạp lại rồi giả lập vi phạm an toàn (safety_violations=1) -> Phải tự động rollback
        loop.synthesize_and_ingest_verified_lessons(diagnoses)
        assert len(store._entries) == 9
        outcome_safe = loop.verify_or_rollback_update(
            previous_entries_snapshot=snapshot_8,
            baseline_tcr=0.90,
            candidate_tcr=1.00,
            safety_violations=1,
            active_vram_mb=5000,
        )
        assert outcome_safe["accepted"] is False
        assert outcome_safe["decision"] == "ROLLBACK_SAFETY_VIOLATION"
        assert len(store._entries) == 8

    def test_condition_5_disk_artifacts_and_sha256_parity(self):
        report = run_phase_a5_learning_loop_benchmark(live_ollama=False)
        assert DEFAULT_A5_TRACES_PATH.exists()
        assert DEFAULT_A5_REPORT_PATH.exists()
        assert DEFAULT_MEMORY_STORE_PATH.exists()

        raw_trace_bytes = DEFAULT_A5_TRACES_PATH.read_bytes()
        assert b"\r\n" not in raw_trace_bytes, "Phase A5 raw traces must use pure LF line endings"
        actual_trace_sha = hashlib.sha256(raw_trace_bytes).hexdigest()
        assert report["raw_inference_traces"]["sha256"] == actual_trace_sha
        assert report["raw_inference_traces"]["byte_size"] == len(raw_trace_bytes)

        raw_store_bytes = DEFAULT_MEMORY_STORE_PATH.read_bytes()
        assert b"\r\n" not in raw_store_bytes, "Memory store must use pure LF line endings"
        actual_store_sha = hashlib.sha256(raw_store_bytes).hexdigest()
        assert report["verified_memory_store"]["sha256"] == actual_store_sha
        assert report["verified_memory_store"]["byte_size"] == len(raw_store_bytes)
        assert report["verified_memory_store"]["stats"]["active_records"] == 9

    def test_condition_6_live_tcr_progression_over_a4(self):
        report = json.loads(DEFAULT_A5_REPORT_PATH.read_text(encoding="utf-8"))
        prog = report["progression_comparison"]
        a0_tcr = prog["phase_a0_vanilla_baseline"]["live_tcr"]
        a3_tcr = prog["phase_a3_scaffolding_only"]["live_tcr"]
        a4_tcr = prog["phase_a4_scaffolding_plus_verified_memory"]["live_tcr"]
        a5_tcr = prog["phase_a5_verified_learning_loop_plus_deterministic_tool"]["live_tcr"]

        assert a0_tcr == 0.45
        assert a3_tcr == 0.55
        assert a4_tcr == 0.90
        assert a5_tcr > a4_tcr, f"Expected Phase A5 Live TCR > {a4_tcr}, got {a5_tcr}"
        assert prog["phase_a5_verified_learning_loop_plus_deterministic_tool"]["passed_tasks"] >= 19
        assert report["verdict"]["gate_passed"] is True
        assert report["hardware_verification"]["within_hardware_limits"] is True
