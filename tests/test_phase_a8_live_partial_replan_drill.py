# -*- coding: utf-8 -*-
"""
tests/test_phase_a8_live_partial_replan_drill.py
================================================
Kiểm thử chứng nhận Phase A8 (Live End-to-End PARTIAL Replan Drill):
1. Chốt chặn Gate kiên quyết từ chối hoàn thành khi giao nộp bán phần (INCOMPLETE).
2. CheckpointStore lưu trữ trạng thái PARTIAL và bảo tồn thành quả qua Time-Travel Backtracking.
3. AdaptiveController nhận diện trạng thái bán phần, lựa chọn nhánh TARGETED_REPAIR.
4. Diễn tập thực chiến Live: Step 1 (giao nộp 2/5) -> Backtrack & Replan -> Step 2 (hoàn tất 5/5) -> COMPLETE.
5. Full-Chain Telemetry ghi nhận toàn bộ chuỗi đa bước có mốc Replan và kết quả cuối cùng.
6. Ghi nhận vật lý vào data/telemetry/recovery_drill_ledger.jsonl đạt chuẩn LF và bảo toàn cấu trúc.
"""

import json
import os
import pytest
from pathlib import Path

from core.os.cognition.mission_completion_gate import MissionCompletionGate
from core.os.cognition.deep_schemas import (
    MissionCriterion,
    CriterionStatus,
    MissionOutcomeStatus,
    RecoveryPolicyType,
)
from core.os.cognition.event_checkpoint import CheckpointStore
from core.os.cognition.adaptive_controller import (
    AdaptiveController,
    CognitiveStateSnapshot,
    AdaptiveStrategy,
)
from core.os.cognition.recovery_drill_harness import (
    RecoveryDrillHarness,
    FaultType,
    DrillResult,
)
from core.telemetry.full_chain_tracer import full_chain_tracer


class TestPhaseA8LivePartialReplanDrill:
    """Bộ kiểm thử thực chứng toàn phần cho đường Replan sau PARTIAL."""

    def test_condition_1_gate_strictly_refuses_partial_delivery(self):
        """
        Điều kiện 1: Khi mới hoàn thành 2/5 tiêu chí, MissionCompletionGate
        kiên quyết trả về INCOMPLETE và không bao giờ báo COMPLETE.
        """
        criteria = [
            MissionCriterion(criterion_id="c1", description="Module A created", status=CriterionStatus.VERIFIED),
            MissionCriterion(criterion_id="c2", description="Module B created", status=CriterionStatus.VERIFIED),
            MissionCriterion(criterion_id="c3", description="Module C created", status=CriterionStatus.UNVERIFIED),
            MissionCriterion(criterion_id="c4", description="Module D created", status=CriterionStatus.UNVERIFIED),
            MissionCriterion(criterion_id="c5", description="Module E created", status=CriterionStatus.UNVERIFIED),
        ]

        outcome = MissionCompletionGate.evaluate(
            mission_id="drill_partial_gate_refusal",
            criteria=criteria,
            verification_context_hash="hash_partial_2_of_5",
            evidence_count=2,
            total_wallclock_ms=50,
        )

        assert outcome.status == MissionOutcomeStatus.INCOMPLETE
        assert outcome.status != MissionOutcomeStatus.COMPLETE
        assert outcome.success_criteria_total == 5
        assert outcome.success_criteria_verified == 2
        assert outcome.success_criteria_unresolved == 3

    def test_condition_2_checkpoint_store_preserves_facts_on_partial(self):
        """
        Điều kiện 2: CheckpointStore lưu trữ trạng thái PARTIAL và khi backtrack
        bảo tồn nguyên vẹn các facts và evidence đã đạt được từ Bước 1.
        """
        store = CheckpointStore()
        partial_evidence = {
            "created_modules": ["mod_a", "mod_b"],
            "sha256": "abc123hash",
        }

        cp = store.create_checkpoint(
            mission_id="m_drill_checkpoint",
            step_id="step_1_initial",
            step_index=1,
            status="PARTIAL",
            evidence=partial_evidence,
            action_name="GENERATE_MODULES",
            trace_id="trace_cp_test",
        )

        assert cp.status == "PARTIAL"
        assert cp.step_index == 1

        best_cp, consolidated_evidence, consolidated_facts = store.backtrack_to_best_checkpoint(
            mission_id="m_drill_checkpoint",
            trace_id="trace_cp_test_replan",
        )

        assert best_cp is not None
        assert best_cp.checkpoint_id == cp.checkpoint_id
        assert "step_1_initial" in consolidated_evidence
        assert consolidated_evidence["step_1_initial"]["created_modules"] == ["mod_a", "mod_b"]

    def test_condition_3_adaptive_controller_selects_targeted_repair(self):
        """
        Điều kiện 3: Khi trạng thái là INCOMPLETE hoặc có unresolved criteria,
        AdaptiveController chọn chính xác chiến lược ERROR_ADAPTIVE_RECOVERY
        với nhánh TARGETED_REPAIR thay vì lặp mù hay chuyển thành FAST_DIRECT.
        """
        ctrl = AdaptiveController()
        snapshot = CognitiveStateSnapshot(
            mission_id="m_drill_controller",
            prompt="Hoàn thiện mã nguồn 5 module",
            outcome_status="INCOMPLETE",
            unresolved_criteria_ids=["c3", "c4", "c5"],
            verified_criteria_ids=["c1", "c2"],
            failed_attempts_count=1,
            step_budget_remaining=4,
        )

        decision = ctrl.decide_strategy(snapshot)

        assert decision.selected_strategy == AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY
        assert decision.recovery_branch == "TARGETED_REPAIR"
        assert decision.step_budget == 3
        assert "partial delivery" in decision.rationale.lower()

    def test_condition_4_live_partial_delivery_replan_drill_end_to_end(self, tmp_path):
        """
        Điều kiện 4: Diễn tập thực chiến Live End-to-End:
        - Bước 1: Worker ban đầu cố tình chỉ tạo 2/5 module -> Gate trả INCOMPLETE.
        - Backtrack & Replan: Controller kích hoạt TARGETED_REPAIR với danh sách [c3, c4, c5].
        - Bước 2: Worker sửa chữa trúng đích tạo nốt 3 module còn lại, tích hợp với kết quả bước 1.
        - Kết quả cuối cùng: 5/5 tiêu chí VERIFIED -> Gate trả COMPLETE.
        - Tỷ lệ phục hồi thành công 100%.
        """
        ledger_file = tmp_path / "test_recovery_ledger.jsonl"
        harness = RecoveryDrillHarness(ledger_path=ledger_file)

        # Worker bước 1: Chỉ tạo mod_1 và mod_2
        def _initial_worker():
            return {
                "modules": {"mod_1": "code_1", "mod_2": "code_2"},
                "version": "v1.0-partial",
            }

        # Criteria evaluator
        all_required = ["mod_1", "mod_2", "mod_3", "mod_4", "mod_5"]
        def _evaluator(output):
            present = output.get("modules", {}) if output else {}
            crits = []
            for m in all_required:
                status = CriterionStatus.VERIFIED if m in present else CriterionStatus.UNVERIFIED
                crits.append(MissionCriterion(criterion_id=f"crit_{m}", description=f"Module {m} present", status=status))
            return crits

        # Worker bước 2: Nhận evidence bước 1 và danh sách thiếu, chỉ sinh các module còn thiếu
        def _targeted_repair_worker(consolidated_evidence, unresolved_ids):
            # Lấy modules đã có từ bước 1
            step1_data = consolidated_evidence.get("step_1_initial", {})
            current_modules = dict(step1_data.get("modules", {}))

            # Sinh trúng đích các module còn thiếu
            for uid in unresolved_ids:
                mod_name = uid.replace("crit_", "")
                current_modules[mod_name] = f"code_repaired_for_{mod_name}"

            return {
                "modules": current_modules,
                "version": "v1.0-repaired-complete",
            }

        # Verifier
        def _verifier(output):
            if not output or "modules" not in output:
                return False
            return len(output["modules"]) == 5

        result = harness.execute_partial_delivery_replan_drill(
            drill_id="drill_live_replan_01",
            initial_worker=_initial_worker,
            targeted_repair_worker=_targeted_repair_worker,
            criteria_evaluator=_evaluator,
            verifier=_verifier,
        )

        assert result.fault_type == FaultType.PARTIAL_DELIVERY
        assert result.recovered is True
        assert result.output_verified is True
        assert result.recovery_mechanism == "CHECKPOINT_BACKTRACK_AND_TARGETED_REPAIR"
        assert result.details["step1_status"] == "INCOMPLETE"
        assert result.details["step1_verified_ratio"] == "2/5"
        assert result.details["step2_status"] == "COMPLETE"
        assert result.details["step2_verified_ratio"] == "5/5"
        assert result.details["recovery_branch"] == "TARGETED_REPAIR"
        assert set(result.details["unresolved_repaired"]) == {"crit_mod_3", "crit_mod_4", "crit_mod_5"}

    def test_condition_5_full_chain_telemetry_trace_parity(self, tmp_path):
        """
        Điều kiện 5: Tích hợp với FullChainTracer để kiểm chứng rằng phiên chạy
        diễn tập ghi nhận đầy đủ trace 5 pha với kết quả hoàn tất xác thực.
        """
        ledger = tmp_path / "telemetry_traces.jsonl"
        from core.telemetry.full_chain_tracer import FullChainTracer
        tracer = FullChainTracer(ledger_path=ledger)

        # 1. Proposal
        t_id = tracer.start_trace(
            mission_id="m_telemetry_drill",
            prompt="Kiểm thử phục hồi bán phần qua FullChainTracer",
            model_id="qwen2.5:3b",
            requested_outputs=["mod_1", "mod_2", "mod_3", "mod_4", "mod_5"],
        )

        # 2. Controller
        tracer.record_controller(
            trace_id=t_id,
            strategy="ERROR_ADAPTIVE_RECOVERY",
            rationale="Switched to TARGETED_REPAIR upon partial completion",
            step_budget=3,
        )

        # 3. Execution
        tracer.record_execution_step(
            trace_id=t_id,
            step_index=1,
            tool_name="worker_initial",
            arguments={"scope": "partial_2_of_5"},
            status="SUCCESS",
            duration_ms=25.0,
            output_summary="Created mod_1, mod_2",
        )
        tracer.record_execution_step(
            trace_id=t_id,
            step_index=2,
            tool_name="targeted_repair",
            arguments={"unresolved": ["crit_mod_3", "crit_mod_4", "crit_mod_5"]},
            status="SUCCESS",
            duration_ms=30.0,
            output_summary="Created mod_3, mod_4, mod_5",
        )

        # 4. Verification
        tracer.record_verification(
            trace_id=t_id,
            total_criteria=5,
            verified_criteria=5,
            unresolved_criteria=0,
            evidence_hashes=["hash_step1", "hash_step2"],
            context_hash="hash_final_verified",
        )

        # 5. Outcome
        final_trace = tracer.finalize_trace(
            trace_id=t_id,
            outcome_status="COMPLETE",
            total_wallclock_ms=88.5,
            total_tokens=150,
            total_vram_peak_mb=128,
        )

        assert final_trace is not None
        assert final_trace.outcome.status == "COMPLETE"
        assert final_trace.controller.strategy == "ERROR_ADAPTIVE_RECOVERY"
        assert final_trace.verification.verified_criteria == 5
        assert final_trace.verification.unresolved_criteria == 0
        assert len(final_trace.execution) == 2

    def test_condition_6_ledger_persistence_and_lf_parity(self, tmp_path):
        """
        Điều kiện 6: Ghi nhận kết quả diễn tập vào ledger file trên đĩa,
        đảm bảo JSON hợp lệ, trường recovered=True và dòng kết thúc bằng LF.
        """
        ledger_file = tmp_path / "drill_ledger.jsonl"
        harness = RecoveryDrillHarness(ledger_path=ledger_file)

        res = harness.execute_partial_delivery_replan_drill(
            drill_id="drill_persistence_01",
            initial_worker=lambda: {"items": [1, 2]},
            targeted_repair_worker=lambda ev, unres: {"items": [1, 2, 3, 4]},
            criteria_evaluator=lambda out: [
                MissionCriterion(
                    criterion_id=f"c_{i}",
                    description=f"Item {i}",
                    status=CriterionStatus.VERIFIED if i in (out.get("items", []) if out else []) else CriterionStatus.UNVERIFIED
                )
                for i in [1, 2, 3, 4]
            ],
            verifier=lambda out: len(out.get("items", [])) == 4,
        )

        assert res.recovered is True
        assert ledger_file.exists()

        raw_bytes = ledger_file.read_bytes()
        assert b"\r\n" not in raw_bytes, "Ledger file must strictly use pure LF line endings"

        line = raw_bytes.decode("utf-8").strip()
        entry = json.loads(line)
        data = entry.get("data", entry)

        assert data["drill_id"] == "drill_persistence_01"
        assert data["fault_type"] == "PARTIAL_DELIVERY"
        assert data["recovered"] is True
        assert data["recovery_mechanism"] == "CHECKPOINT_BACKTRACK_AND_TARGETED_REPAIR"
        assert data["details"]["step1_status"] == "INCOMPLETE"
        assert data["details"]["step2_status"] == "COMPLETE"
