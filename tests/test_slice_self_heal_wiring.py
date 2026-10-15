# -*- coding: utf-8 -*-
"""
tests/test_slice_self_heal_wiring.py
====================================
Slice Self-Heal Wiring: Đấu nối 4 dây kệ chết (Chẩn đoán -> Sinh vá -> Thử sandbox -> Cổng Master)
Đồng thuận Turn 343-346 giữa Antigravity & OpenCode.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from core.recovery.error_classifier import ErrorClassifier, ErrorSubclass
from core.utils.failure_memory import failure_memory, FailureStage
from core.evolution.auto_patcher import GovernedAutoPatcher, auto_patcher, CandidatePatch
from core.kernel.replan_circuit_breaker import replan_circuit_breaker


def test_wire_1_executor_failure_classified_and_recorded_in_failure_memory():
    """
    [Dây 1 - Chẩn đoán & Gán nhãn lỗi có cấu trúc]:
    Khi một primitive/executor ném lỗi (vd: ModuleNotFoundError hoặc FileNotFoundError),
    ErrorClassifier phân loại chính xác subclass lỗi và failure_memory ghi nhận root_cause.
    """
    classifier = ErrorClassifier()
    simulated_err = "ModuleNotFoundError: No module named 'tools.custom_scanner'"
    simulated_tb = (
        'Traceback (most recent call last):\n'
        '  File "services/ai-brain/receptionist/executor_gateway.py", line 540, in execute\n'
        '    local_res = await fn(task_id=task_id, **kwargs)\n'
        '  File "intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py", line 951, in search_web\n'
        '    from tools.custom_scanner import run_scan\n'
        "ModuleNotFoundError: No module named 'tools.custom_scanner'\n"
    )

    verdict = classifier.classify(simulated_err, simulated_tb)
    assert verdict.subclass in (
        ErrorSubclass.E08_CAPABILITY_GAP_MISSING_TOOL,
        ErrorSubclass.E03_FILE_NOT_FOUND_OR_BUSY,
        ErrorSubclass.E01_SYNTAX_PARSING_ERROR,
    ), f"Phân loại sai subclass: {verdict.subclass}"

    # Ghi nhận vào failure_memory
    import asyncio
    pattern = asyncio.run(
        failure_memory.record_failure(
            task_id="task_test_001",
            goal="hãy chạy custom_scanner tìm kiếm",
            task_type="coding",
            failure_stage=FailureStage.TOOL_EXECUTION,
            error_detail=f"{verdict.subclass.value}: {simulated_err}",
            failed_tools=["custom_scanner"],
            attempted_fix="Ensure custom_scanner is mounted or use fallback search tool",
            fix_worked=False,
        )
    )

    assert pattern is not None
    assert "custom_scanner" in pattern.failed_tools
    assert "dependency" in pattern.root_cause.lower()
    assert pattern.failure_stage == FailureStage.TOOL_EXECUTION


def test_wire_2_governed_auto_patcher_generates_candidate_patch_on_code_error():
    """
    [Dây 2 - Sinh bản vá ứng viên có kiểm soát cú pháp]:
    GovernedAutoPatcher nhận traceback, định vị đúng file, dòng code,
    sinh Unified Diff và kiểm tra cú pháp AST hợp lệ.
    """
    patcher = GovernedAutoPatcher()
    sample_tb = (
        'Traceback (most recent call last):\n'
        '  File "core/utils/sample_math.py", line 12, in add\n'
        '    return a + b\n'
        'NameError: name \'b\' is not defined\n'
    )
    report = patcher.diagnose_traceback(sample_tb)
    assert report.target_file == "core/utils/sample_math.py"
    assert report.line_number == 12

    orig_code = "def add(a):\n    return a + b\n"
    patched_code = "def add(a, b=0):\n    return a + b\n"

    candidate = patcher.create_candidate_patch(
        target_file=report.target_file,
        original_code=orig_code,
        patched_code=patched_code,
    )

    assert candidate.syntax_valid is True
    assert "patch_" in candidate.patch_id
    assert "b=0" in candidate.diff_preview


def test_wire_3_governed_master_approval_enforces_gce_invariant():
    """
    [Dây 3 - Cổng Master Phê Duyệt]:
    Áp dụng bản vá BẮT BUỘC phải có is_master_approved=True.
    Mọi nỗ lực tự ý apply khi thiếu cờ phê chuẩn đều bị từ chối fail-closed.
    """
    patcher = GovernedAutoPatcher()
    orig = "x = 1\n"
    patched = "x = 2\n"
    cand = patcher.create_candidate_patch("dummy.py", orig, patched)

    # 1. Từ chối khi chưa có phê chuẩn của Master
    unapproved_res = patcher.apply_governed_patch(cand.patch_id, is_master_approved=False)
    assert unapproved_res["success"] is False
    assert "Master" in unapproved_res["error"]

    # 2. Phê chuẩn thành công khi có xác nhận của Master
    approved_res = patcher.apply_governed_patch(cand.patch_id, is_master_approved=True)
    assert approved_res["success"] is True
    assert approved_res["status"] == "COMMITTED"


def test_wire_4_critic_needs_replan_triggers_replan_loop_with_ceiling():
    """
    [Dây 4 - Kích hoạt Luồng Re-plan từ Ban Kiểm Soát T5]:
    Khi Critic T5 trả về approved=False và needs_replan=True,
    bộ điều phối kích hoạt vòng Re-plan tối đa 2 lần, không cho phép lặp vô tận.
    """
    from core.os.cognition.self_heal_wiring import evaluate_critic_replan_decision

    critic_feedback_1 = {
        "approved": False,
        "verdict": "[PARTIAL]",
        "needs_replan": True,
        "recommendations": ["Chia nhỏ thành 2 sub-queries: VN-Index và nhóm ngành"],
    }

    # Lần 1: Cho phép replan
    dec1 = evaluate_critic_replan_decision(critic_feedback_1, current_replan_count=0)
    assert dec1["should_replan"] is True
    assert dec1["next_replan_count"] == 1
    assert "sub-queries" in dec1["replan_prompt"]

    # Lần 2: Vẫn trong trần cho phép (current_count = 1)
    dec2 = evaluate_critic_replan_decision(critic_feedback_1, current_replan_count=1)
    assert dec2["should_replan"] is True
    assert dec2["next_replan_count"] == 2

    # Lần 3: Vượt trần 2 lần -> Dừng và chuyển sang xuất bản báo cáo trung thực
    dec3 = evaluate_critic_replan_decision(critic_feedback_1, current_replan_count=2)
    assert dec3["should_replan"] is False
    assert "EXCEEDED_MAX_REPLAN" in dec3["reason"]


def test_wire_5_in_mission_autonomous_recovery_budget_max_3():
    """
    [Lớp Phòng Thủ 3 - Tự cứu có hạn mức tối đa 3 lần/mission]:
    Quy tắc ranh giới: tối đa 3 lần tự cứu/mission cho lỗi Tier 1.
    Lần thứ 4 bắt buộc dừng và chuyển cờ gọi Master / fail-closed.
    """
    from core.os.cognition.self_heal_wiring import AutonomousRecoveryTracker

    tracker = AutonomousRecoveryTracker(task_id="task_test_budget_001")
    assert tracker.can_attempt_recovery() is True

    # 3 lần tự cứu được phép
    assert tracker.record_recovery_attempt("fallback_tool_retry") == 1
    assert tracker.record_recovery_attempt("param_adjust") == 2
    assert tracker.record_recovery_attempt("degraded_answer") == 3
    assert tracker.can_attempt_recovery() is False

    # Lần thứ 4 vượt hạn mức -> Phải dừng
    decision = tracker.evaluate_next_action()
    assert decision["action"] == "ESCALATE_TO_MASTER"
    assert decision["reason"] == "BUDGET_EXCEEDED_MAX_3"


def test_wire_6_fault_injection_e2e_diagnose_and_heal():
    """
    [Test E2E Gieo Bug - Fault Injection End-to-End]:
    Cố tình gieo 1 lỗi cú pháp/import giả định, hệ thống tự:
    1. Chẩn đoán traceback thành DiagnosticReport
    2. Gán nhãn lỗi qua ErrorClassifier
    3. Sinh CandidatePatch an toàn qua GovernedAutoPatcher
    4. Thẩm định cú pháp đạt chuẩn.
    """
    from core.os.cognition.self_heal_wiring import execute_self_heal_diagnostic_cycle

    faulty_traceback = (
        'Traceback (most recent call last):\n'
        '  File "core/utils/temp_probe.py", line 4, in probe_status\n'
        '    import missing_dependency_pkg\n'
        "ModuleNotFoundError: No module named 'missing_dependency_pkg'\n"
    )

    cycle_result = execute_self_heal_diagnostic_cycle(
        error_msg="No module named 'missing_dependency_pkg'",
        traceback_str=faulty_traceback,
        suggested_code="import sys\n# Fallback dependency",
        original_code="import missing_dependency_pkg\n",
    )

    assert cycle_result["classified_subclass"] in (
        ErrorSubclass.E08_CAPABILITY_GAP_MISSING_TOOL.value,
        ErrorSubclass.E03_FILE_NOT_FOUND_OR_BUSY.value,
        ErrorSubclass.E01_SYNTAX_PARSING_ERROR.value,
    )
    assert cycle_result["patch_generated"] is True
    assert cycle_result["syntax_valid"] is True
    assert cycle_result["requires_master_approval"] is True
