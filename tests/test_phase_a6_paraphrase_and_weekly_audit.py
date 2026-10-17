# -*- coding: utf-8 -*-
"""
tests/test_phase_a6_paraphrase_and_weekly_audit.py
==================================================
Kiểm thử toàn diện Giai đoạn A6 (Hướng 1):
Paraphrase & Bilingual Semantic Generalization + 6-Gate Weekly Autonomous Audit Runner.
Giải quyết trực tiếp lưu ý kiểm toán Lượt 380 của OpenCode và chỉ đạo Hướng 1 của Master Lee Trung.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.os.cognition.verified_learning_loop import DeterministicMathTool
from core.os.cognition.verified_memory_store import (
    DEFAULT_MEMORY_STORE_PATH,
    ensure_canonical_memory_store,
)
from core.os.cognition.weekly_autonomous_audit import (
    DEFAULT_A6_REPORT_PATH,
    DEFAULT_A6_TRACES_PATH,
    DEFAULT_PARAPHRASE_CHALLENGE_PATH,
    WeeklyAutonomousAuditRunner,
)


class TestPhaseA6ParaphraseAndWeeklyAudit:
    """Bộ kiểm thử 6 điều kiện của Tổng quát hóa Diễn đạt Song ngữ & Kiểm toán Tự động Định kỳ (Phase A6)."""

    def test_condition_1_bilingual_and_directional_math_tool_generalization(self):
        # 1. Diễn đạt theo hướng "từ X lên Y" (X là gốc 40.0, Y là mới 50.0 -> +25.00%)
        r1 = DeterministicMathTool.evaluate_prompt(
            "Khi băng thông nâng cấp từ 40.0 Gbps lên 50.0 Gbps thì mức tăng tương đối là bao nhiêu phần trăm?",
            domain_group="A_MATH_FIDELITY",
        )
        assert r1 is not None
        assert r1["operation"] == "PERCENTAGE_CHANGE"
        assert r1["operands"] == [50.0, 40.0]
        assert r1["result_formatted"] == "25.00%"

        # 2. Diễn đạt tiếng Anh "percentage increase of Y compared to X"
        r2 = DeterministicMathTool.evaluate_prompt(
            "What is the percentage increase of cluster B (90.0 tok) compared to cluster A (72.0 tok)?",
            domain_group="A_MATH_FIDELITY",
        )
        assert r2 is not None
        assert r2["operation"] == "PERCENTAGE_CHANGE"
        assert r2["operands"] == [90.0, 72.0]
        assert r2["result_formatted"] == "25.00%"

        # 3. Diễn đạt tiếng Anh "from X to Y"
        r3 = DeterministicMathTool.evaluate_prompt(
            "By what percentage did throughput grow from 80.0 tok to 100.0 tok?",
            domain_group="A_MATH_FIDELITY",
        )
        assert r3 is not None
        assert r3["operands"] == [100.0, 80.0]
        assert r3["result_formatted"] == "25.00%"

        # 4. Diễn đạt tốc độ sinh / generation speed (không dùng từ "thông lượng")
        r4 = DeterministicMathTool.evaluate_prompt(
            "Calculate the generation speed in tok/s when 280 tokens are produced in 14.0 seconds.",
            domain_group="A_MATH_FIDELITY",
        )
        assert r4 is not None
        assert r4["operation"] == "TOKEN_THROUGHPUT"
        assert r4["result_formatted"] == "20.0 tok/s"

        # 5. Diễn đạt chi phí tiếng Anh có dấu phẩy phân cách hàng nghìn (2,000,000 VND)
        r5 = DeterministicMathTool.evaluate_prompt(
            "What is the total shipping cost for 15 trips if the unit price per trip is 2,000,000 VND?",
            domain_group="A_MATH_FIDELITY",
        )
        assert r5 is not None
        assert r5["operation"] == "UNIT_MULTIPLICATION"
        assert r5["result_formatted"] == "30000000 VND"

    def test_condition_2_bilingual_semantic_concept_memory_retrieval(self):
        store = ensure_canonical_memory_store(DEFAULT_MEMORY_STORE_PATH, force_rebuild=False)

        # Truy xuất bằng câu hỏi tiếng Anh hoàn toàn (không có từ khóa tiếng Việt gốc)
        hits_pct = store.retrieve_for_task(
            prompt="What is the percentage increase of cluster B (90.0 tok) compared to cluster A (72.0 tok)?",
            domain_group="A_MATH_FIDELITY",
            top_k=1,
        )
        assert len(hits_pct) == 1
        assert hits_pct[0].memory_id == "MEM_MATH_003"

        hits_tp = store.retrieve_for_task(
            prompt="Calculate the generation speed in tok/s when 280 tokens are produced in 14.0 seconds.",
            domain_group="A_MATH_FIDELITY",
            top_k=1,
        )
        assert len(hits_tp) == 1
        assert hits_tp[0].memory_id == "MEM_MATH_002"

        hits_cli = store.retrieve_for_task(
            prompt="Write the exact MikroTik RouterOS firewall CLI command to block TCP port 23 on the input chain.",
            domain_group="D_TOOL_AND_FILEOPS",
            top_k=1,
        )
        assert len(hits_cli) == 1
        assert hits_cli[0].memory_id == "MEM_TOOL_001"

    def test_condition_3_paraphrase_challenge_artifact_and_anti_leak(self):
        runner = WeeklyAutonomousAuditRunner()
        report = runner.run_weekly_audit(live_ollama=False)

        assert DEFAULT_PARAPHRASE_CHALLENGE_PATH.exists()
        raw_chal = DEFAULT_PARAPHRASE_CHALLENGE_PATH.read_bytes()
        assert b"\r\n" not in raw_chal
        assert report["paraphrase_generalization_challenge"]["challenge_sha256"] == hashlib.sha256(raw_chal).hexdigest()
        assert report["verified_memory_store"]["leak_violations_across_all_4_suites"] == 0

    def test_condition_4_raw_traces_sha256_and_lf_parity(self):
        report = json.loads(DEFAULT_A6_REPORT_PATH.read_text(encoding="utf-8"))
        assert DEFAULT_A6_TRACES_PATH.exists()

        raw_traces = DEFAULT_A6_TRACES_PATH.read_bytes()
        assert b"\r\n" not in raw_traces, "Phase A6 raw traces must use pure LF line endings"
        actual_sha = hashlib.sha256(raw_traces).hexdigest()

        assert report["paraphrase_generalization_challenge"]["raw_traces_sha256"] == actual_sha
        assert report["paraphrase_generalization_challenge"]["raw_traces_byte_size"] == len(raw_traces)

    def test_condition_5_live_gpu_paraphrase_generalization_tcr(self):
        report = json.loads(DEFAULT_A6_REPORT_PATH.read_text(encoding="utf-8"))
        chal = report["paraphrase_generalization_challenge"]
        assert chal["total_tasks"] == 10
        assert chal["passed_tasks"] >= 9
        assert chal["live_tcr"] >= 0.90

    def test_condition_6_six_gate_weekly_autonomous_audit_complete(self):
        report = json.loads(DEFAULT_A6_REPORT_PATH.read_text(encoding="utf-8"))
        audit = report["weekly_autonomous_audit_6_gates"]
        assert audit["completion_status"] == "COMPLETE"
        assert audit["verified_gates_count"] == 6
        assert audit["total_gates_count"] == 6
        assert audit["combined_30_task_summary"]["combined_total"] == 30
        assert audit["combined_30_task_summary"]["combined_passed"] >= 29
        assert report["verdict"]["gate_passed"] is True
        assert report["verdict"]["opencode_turn_380_observation_resolved"] is True
