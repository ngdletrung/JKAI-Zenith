# -*- coding: utf-8 -*-
"""
tests/test_phase_a2_adaptive_controller.py
============================================
Kiểm thử chứng nhận Phase A2: Cognitive Adaptive Controller.
Tuân thủ chỉ đạo của Master Lee Trung & SOP v2.4:
1. FAST_DIRECT: Model nhỏ xử lý tác vụ đơn giản trực tiếp.
2. MULTI_STEP_PLANNING: Tác vụ nhiều bước lập kế hoạch và theo dõi tiến độ.
3. ERROR_ADAPTIVE_RECOVERY: Bằng chứng lỗi dẫn hướng chọn nhánh phục hồi khác (cấm lặp mù).
4. ASK_USER_CLARIFICATION: Thiếu thông tin thì hỏi Master thay vì đoán mò.
5. ESCALATE_MODEL_OR_HUMAN: Độ bất định >= 0.8 hoặc rủi ro HIGH/CRITICAL thì leo thang.
6. Tích hợp Full-Chain Telemetry ghi nhận pha Controller chuẩn xác.
"""

import pytest
from core.os.cognition.adaptive_controller import (
    AdaptiveController,
    AdaptiveStrategy,
    CognitiveStateSnapshot,
    adaptive_controller,
)
from core.telemetry.full_chain_tracer import FullChainTracer


class TestPhaseA2AdaptiveController:
    """Kiểm thử các nhánh chiến lược của Adaptive Controller."""

    def test_strategy_fast_direct_simple_prompt(self):
        """Tác vụ đơn giản -> Chọn FAST_DIRECT, step_budget = 1, không qua DAG cồng kềnh."""
        ctrl = AdaptiveController()
        snapshot = CognitiveStateSnapshot(
            mission_id="m_simple_01",
            prompt="Tính giá trị biểu thức: 15 * 8 + 42",
            is_multi_step=False,
        )

        decision = ctrl.decide_strategy(snapshot)

        assert decision.selected_strategy == AdaptiveStrategy.FAST_DIRECT
        assert decision.step_budget == 1
        assert decision.require_user_interaction is False
        assert "small model" in decision.rationale.lower() or "direct" in decision.rationale.lower()

    def test_strategy_multi_step_planning(self):
        """Tác vụ nhiều bước phát hiện qua cờ hoặc từ khóa -> MULTI_STEP_PLANNING."""
        ctrl = AdaptiveController(default_step_budget=5)
        # Test qua cờ is_multi_step
        snapshot1 = CognitiveStateSnapshot(
            mission_id="m_multi_01",
            prompt="Cập nhật module",
            is_multi_step=True,
            step_budget_remaining=4,
        )
        decision1 = ctrl.decide_strategy(snapshot1)
        assert decision1.selected_strategy == AdaptiveStrategy.MULTI_STEP_PLANNING
        assert decision1.step_budget == 4

        # Test qua từ khóa phân tích trong prompt
        snapshot2 = CognitiveStateSnapshot(
            mission_id="m_multi_02",
            prompt="Bước 1 tạo file config, sau đó sửa mã nguồn và chạy toàn bộ các file test",
            is_multi_step=False,
        )
        decision2 = ctrl.decide_strategy(snapshot2)
        assert decision2.selected_strategy == AdaptiveStrategy.MULTI_STEP_PLANNING
        assert decision2.step_budget >= 2

    def test_strategy_error_adaptive_recovery_branches(self):
        """Gặp lỗi runtime -> ERROR_ADAPTIVE_RECOVERY, chọn nhánh phục hồi dựa trên bằng chứng."""
        ctrl = AdaptiveController()

        # Nhánh 1: Lỗi cú pháp / tham số -> ARGUMENT_RE_ENCODING
        snap_syntax = CognitiveStateSnapshot(
            mission_id="m_err_01",
            prompt="Chạy công cụ",
            recent_errors=[{"error": "TypeError: command got an unexpected keyword argument"}],
            failed_attempts_count=1,
            step_budget_remaining=4,
        )
        dec_syntax = ctrl.decide_strategy(snap_syntax)
        assert dec_syntax.selected_strategy == AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY
        assert dec_syntax.recovery_branch == "ARGUMENT_RE_ENCODING"
        assert dec_syntax.step_budget == 3

        # Nhánh 2: Lỗi mạng / timeout -> FALLBACK_OFFLINE_SEARCH
        snap_net = CognitiveStateSnapshot(
            mission_id="m_err_02",
            prompt="Truy vấn dữ liệu",
            recent_errors=[{"error": "ConnectionTimeout to external API endpoint"}],
            failed_attempts_count=1,
            step_budget_remaining=4,
        )
        dec_net = ctrl.decide_strategy(snap_net)
        assert dec_net.selected_strategy == AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY
        assert dec_net.recovery_branch == "FALLBACK_OFFLINE_SEARCH"

        # Nhánh 3: Lỗi not found / permission -> PATH_RECONCILIATION
        snap_path = CognitiveStateSnapshot(
            mission_id="m_err_03",
            prompt="Đọc file cấu hình",
            recent_errors=[{"error": "FileNotFoundError: [Errno 2] No such file or directory: /app/conf.yaml"}],
            failed_attempts_count=1,
            step_budget_remaining=4,
        )
        dec_path = ctrl.decide_strategy(snap_path)
        assert dec_path.selected_strategy == AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY
        assert dec_path.recovery_branch == "PATH_RECONCILIATION"

        # Nhánh 4: Trước đó là FAST_DIRECT bị hỏng -> PROMOTE_TO_DAG_WITH_CHECKPOINT
        snap_promote = CognitiveStateSnapshot(
            mission_id="m_err_04",
            prompt="Thực thi nhanh",
            recent_errors=[{"error": "Generic execution failure"}],
            failed_attempts_count=1,
            last_strategy_tried=AdaptiveStrategy.FAST_DIRECT,
            step_budget_remaining=3,
        )
        dec_promote = ctrl.decide_strategy(snap_promote)
        assert dec_promote.selected_strategy == AdaptiveStrategy.ERROR_ADAPTIVE_RECOVERY
        assert dec_promote.recovery_branch == "PROMOTE_TO_DAG_WITH_CHECKPOINT"

    def test_strategy_error_adaptive_max_attempts_escalation(self):
        """Thất bại liên tiếp >= 3 lần -> Chuyển sang ESCALATE thay vì lặp vô hạn."""
        ctrl = AdaptiveController()
        snapshot = CognitiveStateSnapshot(
            mission_id="m_err_loop",
            prompt="Cập nhật dependency",
            recent_errors=[{"error": "Repeated failure"}],
            failed_attempts_count=3,
            step_budget_remaining=2,
        )
        decision = ctrl.decide_strategy(snapshot)
        assert decision.selected_strategy == AdaptiveStrategy.ESCALATE_MODEL_OR_HUMAN
        assert decision.require_user_interaction is True
        assert decision.escalation_target == "MASTER_APPROVAL"

    def test_strategy_ask_user_clarification_on_missing_info(self):
        """Thiếu thông tin then chốt -> Dừng lại hỏi Master, cấm hallucinate."""
        ctrl = AdaptiveController()
        snapshot = CognitiveStateSnapshot(
            mission_id="m_ask_01",
            prompt="Deploy contract lên testnet",
            missing_information_keys=["private_key_env_var", "network_rpc_url"],
        )
        decision = ctrl.decide_strategy(snapshot)

        assert decision.selected_strategy == AdaptiveStrategy.ASK_USER_CLARIFICATION
        assert decision.require_user_interaction is True
        assert "private_key_env_var" in decision.rationale

    def test_strategy_escalate_on_high_risk_or_high_uncertainty(self):
        """Rủi ro an toàn hoặc độ bất định vượt ngưỡng an toàn -> ESCALATE."""
        ctrl = AdaptiveController()

        # Rủi ro HIGH -> Yêu cầu Master duyệt
        snap_risk = CognitiveStateSnapshot(
            mission_id="m_risk_01",
            prompt="Xóa toàn bộ volumes dữ liệu production",
            safety_risk_level="HIGH",
        )
        dec_risk = ctrl.decide_strategy(snap_risk)
        assert dec_risk.selected_strategy == AdaptiveStrategy.ESCALATE_MODEL_OR_HUMAN
        assert dec_risk.require_user_interaction is True
        assert dec_risk.escalation_target == "MASTER_APPROVAL"

        # Độ bất định cao >= 0.8 -> Leo thang sang Teacher Model
        snap_unc = CognitiveStateSnapshot(
            mission_id="m_risk_02",
            prompt="Phân tích bài toán toán học phức tạp",
            uncertainty_score=0.85,
            safety_risk_level="LOW",
        )
        dec_unc = ctrl.decide_strategy(snap_unc)
        assert dec_unc.selected_strategy == AdaptiveStrategy.ESCALATE_MODEL_OR_HUMAN
        assert dec_unc.require_user_interaction is True
        assert dec_unc.escalation_target == "TEACHER_MODEL"

    def test_telemetry_integration_with_full_chain_tracer(self, tmp_path):
        """Kiểm tra ghi nhận Controller phase vào FullChainTracer."""
        ledger = tmp_path / "tracer_ledger.jsonl"
        tracer = FullChainTracer(ledger_path=ledger)

        # Khởi tạo trace
        trace_id = tracer.start_trace(
            mission_id="m_telemetry_test",
            prompt="Lập trình hệ thống",
            model_id="q4_small_model",
        )

        # Controller ra quyết định và đồng bộ telemetry
        snapshot = CognitiveStateSnapshot(
            mission_id="m_telemetry_test",
            prompt="Lập trình hệ thống",
            is_multi_step=True,
        )

        ctrl = AdaptiveController()
        # Patch tracer tạm thời để dùng ledger trong tmp_path
        from core.telemetry import full_chain_tracer as fct_module
        orig_instance = fct_module.full_chain_tracer
        fct_module.full_chain_tracer = tracer
        try:
            decision = ctrl.decide_strategy(snapshot, trace_id=trace_id)
            assert decision.selected_strategy == AdaptiveStrategy.MULTI_STEP_PLANNING
            
            # Kiểm tra trace đã được cập nhật Controller phase
            updated_trace = tracer.get_trace(trace_id)
            assert updated_trace is not None
            assert updated_trace.controller is not None
            assert updated_trace.controller.strategy == "MULTI_STEP_PLANNING"
            assert updated_trace.controller.step_budget >= 2
        finally:
            fct_module.full_chain_tracer = orig_instance
