# -*- coding: utf-8 -*-
"""
tests/test_phase_a1_completion_and_telemetry.py
================================================
Kiểm thử chứng nhận Phase A1:
1. Completion Authority chuẩn hóa 3 trạng thái bất biến: COMPLETE, INCOMPLETE, BLOCKED.
   - Tuyệt đối cấm báo hoàn thành khi mới sửa 2/5 file.
2. Full-Chain Telemetry 5 pha:
   - Proposal -> Controller -> Execution -> Verification -> Outcome.
   - Phân định chuẩn xác 3 nguồn gốc lỗi (Model vs Controller vs Runtime).
"""

import json
import pytest
from pathlib import Path

from core.os.cognition.mission_completion_gate import MissionCompletionGate, RecoveryManager
from core.os.cognition.deep_schemas import (
    MissionCriterion,
    CriterionStatus,
    MissionOutcomeStatus,
    RecoveryPolicyType,
)
from core.telemetry.full_chain_tracer import FullChainTracer, full_chain_tracer


class TestPhaseA1CompletionAuthority:
    """Kiểm tra Completion Authority 3 trạng thái chuẩn tắc."""

    def test_complete_when_100_percent_verified(self):
        """Đủ 100% tiêu chí xác minh -> Trạng thái COMPLETE."""
        c1 = MissionCriterion(criterion_id="c1", description="File 1 modified", status=CriterionStatus.VERIFIED)
        c2 = MissionCriterion(criterion_id="c2", description="File 2 modified", status=CriterionStatus.VERIFIED)

        outcome = MissionCompletionGate.evaluate(
            mission_id="m_complete_test",
            criteria=[c1, c2],
            verification_context_hash="hash_verified_all",
            evidence_count=2,
            total_wallclock_ms=120,
        )

        assert outcome.status == MissionOutcomeStatus.COMPLETE
        assert outcome.status == MissionOutcomeStatus.COMPLETED_VERIFIED
        assert outcome.status.value == "COMPLETE"
        assert outcome.success_criteria_verified == 2
        assert outcome.success_criteria_unresolved == 0

    def test_incomplete_when_partial_verified_never_claims_done(self):
        """
        [PHASE A1 MANDATE]: Sửa 2/5 file -> Bắt buộc là INCOMPLETE!
        Cấm tuyệt đối ngộ nhận hoàn thành (no more fake completion).
        """
        criteria = [
            MissionCriterion(criterion_id="c1", description="File 1", status=CriterionStatus.VERIFIED),
            MissionCriterion(criterion_id="c2", description="File 2", status=CriterionStatus.VERIFIED),
            MissionCriterion(criterion_id="c3", description="File 3", status=CriterionStatus.UNVERIFIED),
            MissionCriterion(criterion_id="c4", description="File 4", status=CriterionStatus.UNVERIFIED),
            MissionCriterion(criterion_id="c5", description="File 5", status=CriterionStatus.UNVERIFIED),
        ]

        outcome = MissionCompletionGate.evaluate(
            mission_id="m_partial_test",
            criteria=criteria,
            verification_context_hash="hash_partial",
            evidence_count=2,
            total_wallclock_ms=250,
        )

        assert outcome.status == MissionOutcomeStatus.INCOMPLETE
        assert outcome.status.value == "INCOMPLETE"
        assert outcome.status != MissionOutcomeStatus.COMPLETE
        assert outcome.success_criteria_verified == 2
        assert outcome.success_criteria_unresolved == 3

    def test_blocked_when_criterion_falsified_or_blocked(self):
        """Khi có tiêu chí bị FALSIFIED hoặc BLOCKED -> Outcome phải là BLOCKED."""
        criteria = [
            MissionCriterion(criterion_id="c1", description="Step 1", status=CriterionStatus.VERIFIED),
            MissionCriterion(criterion_id="c2", description="Step 2", status=CriterionStatus.FALSIFIED),
        ]

        outcome = MissionCompletionGate.evaluate(
            mission_id="m_blocked_test",
            criteria=criteria,
            verification_context_hash="hash_blocked",
            evidence_count=1,
            total_wallclock_ms=180,
        )

        assert outcome.status == MissionOutcomeStatus.BLOCKED
        assert outcome.status.value == "BLOCKED"


class TestPhaseA1FullChainTelemetry:
    """Kiểm tra Telemetry 5 pha và chẩn đoán quy kết lỗi."""

    def test_full_chain_happy_path_trace(self, tmp_path):
        ledger = tmp_path / "test_traces.jsonl"
        tracer = FullChainTracer(ledger_path=ledger)

        # 1. Proposal
        t_id = tracer.start_trace(
            mission_id="m_full_01",
            prompt="Phân tích báo cáo tài chính Q3",
            model_id="qwen2.5:3b",
            requested_outputs=["table_q3.csv", "summary.md"],
        )

        # 2. Controller
        tracer.record_controller(
            trace_id=t_id,
            strategy="DEEP_DAG",
            rationale="Tác vụ đa bước cần cào dữ liệu và tổng hợp văn bản.",
            step_budget=4,
        )

        # 3. Execution
        tracer.record_execution_step(
            trace_id=t_id,
            step_index=1,
            tool_name="search_web",
            arguments={"query": "báo cáo tài chính Q3 2026"},
            status="SUCCESS",
            duration_ms=45.0,
            output_summary="Đã tìm thấy 3 nguồn báo cáo.",
        )

        # 4. Verification
        tracer.record_verification(
            trace_id=t_id,
            total_criteria=2,
            verified_criteria=2,
            unresolved_criteria=0,
            evidence_hashes=["hash_q3_table", "hash_q3_summary"],
        )

        # 5. Outcome
        final_trace = tracer.finalize_trace(
            trace_id=t_id,
            outcome_status="COMPLETE",
            total_wallclock_ms=1250.0,
            total_tokens=420,
            total_vram_peak_mb=1850,
        )

        assert final_trace.outcome.status == "COMPLETE"
        assert final_trace.error_attribution == "NONE"
        assert ledger.exists()
        line = ledger.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["trace_id"] == t_id
        assert data["error_attribution"] == "NONE"

    def test_error_attribution_runtime_tool_crash(self, tmp_path):
        ledger = tmp_path / "test_traces_err.jsonl"
        tracer = FullChainTracer(ledger_path=ledger)

        t_id = tracer.start_trace(
            mission_id="m_tool_crash",
            prompt="Chạy lệnh hệ thống",
            model_id="qwen2.5:3b",
        )
        tracer.record_controller(t_id, strategy="FAST_DIRECT", rationale="Lệnh đơn.")
        tracer.record_execution_step(
            trace_id=t_id,
            step_index=1,
            tool_name="terminal_exec",
            arguments={"cmd": "invalid_cmd"},
            status="FAILED",
            error_message="CommandNotFound: invalid_cmd",
        )
        tracer.record_verification(t_id, total_criteria=1, verified_criteria=0, unresolved_criteria=1)

        trace = tracer.finalize_trace(t_id, outcome_status="INCOMPLETE", total_wallclock_ms=50.0)
        assert trace.error_attribution == "RUNTIME_TOOL_EXECUTION"
        assert "CommandNotFound" in trace.attribution_reason

    def test_error_attribution_controller_early_stopping(self, tmp_path):
        ledger = tmp_path / "test_traces_early.jsonl"
        tracer = FullChainTracer(ledger_path=ledger)

        t_id = tracer.start_trace(
            mission_id="m_early_stop",
            prompt="Sửa 5 file",
            model_id="qwen2.5:3b",
            requested_outputs=["f1", "f2", "f3", "f4", "f5"],
        )
        tracer.record_controller(t_id, strategy="DEEP_DAG", rationale="Lập kế hoạch 5 bước.", step_budget=5)
        # Chỉ chạy 1 bước rồi dừng trong khi còn 4 criteria chưa xong
        tracer.record_execution_step(
            trace_id=t_id,
            step_index=1,
            tool_name="replace_file_content",
            arguments={"file": "f1"},
            status="SUCCESS",
        )
        tracer.record_verification(t_id, total_criteria=5, verified_criteria=1, unresolved_criteria=4)

        trace = tracer.finalize_trace(t_id, outcome_status="INCOMPLETE", total_wallclock_ms=100.0)
        assert trace.error_attribution == "CONTROLLER_ORCHESTRATION"
        assert "stopped early" in trace.attribution_reason
