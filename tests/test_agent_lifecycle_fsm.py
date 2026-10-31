"""
tests/test_agent_lifecycle_fsm.py
=================================
Bộ kiểm thử kiểm chuẩn độc lập cho Vũ Khí 3: DeepSeek-Harness Hook-Based Lifecycle FSM.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.kernel.agent_lifecycle import (
    StepContext,
    ToolInvocationContext,
    ToolResultContext,
    LifecycleManager,
    ActionValidationHook,
    CircuitBreakerHook,
    TransactionalMutationHook,
    CoverageAndWorkingMemoryHook,
    TracebackDistillerHook,
    NoFabricationGuardHook,
    MultiFileCoverageGuardHook,
    PreSubmissionReflexionHook,
)
from core.kernel.progress_budget import ProgressBudget


@pytest.mark.asyncio
async def test_action_validation_hook_intercepts_unknown_tool():
    """Kiểm tra ActionValidationHook chặn đứng tool không hợp lệ."""
    hook = ActionValidationHook(known_tools={"view_file", "run_command"})
    step_ctx = StepContext(
        task_id="t1", goal="audit", mode="audit", step=1, max_steps=10, messages=[]
    )
    tool_ctx = ToolInvocationContext(tool="malicious_exec", params={"cmd": "whoami"})

    await hook.before_tool_dispatch(step_ctx, tool_ctx)

    assert tool_ctx.is_intercepted is True
    assert "Action không hợp lệ" in (tool_ctx.interception_observation or "")


@pytest.mark.asyncio
async def test_circuit_breaker_hook_triggers_recovery_guide():
    """Kiểm tra CircuitBreakerHook bẻ gãy dao động lặp view_file."""
    budget = ProgressBudget(max_steps=10)
    # Giả lập đã gọi view_file 2 lần cùng params
    budget.register_action("view_file", {"path": "core/security/egress_gate.py"}, outcome_ok=True)
    budget.register_action("view_file", {"path": "core/security/egress_gate.py"}, outcome_ok=True)

    hook = CircuitBreakerHook()
    step_ctx = StepContext(
        task_id="t1",
        goal="audit",
        mode="audit",
        step=3,
        max_steps=10,
        messages=[],
        budget=budget,
    )
    tool_ctx = ToolInvocationContext(tool="view_file", params={"path": "core/security/egress_gate.py"})

    await hook.before_tool_dispatch(step_ctx, tool_ctx)

    assert tool_ctx.is_intercepted is True
    assert "CIRCUIT-BREAKER" in (tool_ctx.interception_observation or "")


@pytest.mark.asyncio
async def test_traceback_distiller_hook():
    """Kiểm tra TracebackDistillerHook đưa lỗi chính lên đầu log."""
    hook = TracebackDistillerHook()
    step_ctx = StepContext(
        task_id="t1", goal="fix bug", mode="fix", step=1, max_steps=10, messages=[]
    )
    raw_pytest = (
        "collected 1 item\n"
        "test_foo.py F\n"
        "================ FAILURES ================\n"
        ">       assert 1 == 2\n"
        "E       AssertionError: assert 1 == 2\n"
        "FAILED test_foo.py::test_bar - AssertionError\n"
    )
    result_ctx = ToolResultContext(
        tool="run_command",
        params={"command": "pytest"},
        raw_output=raw_pytest,
        processed_output=raw_pytest,
    )

    await hook.after_tool_executed(step_ctx, result_ctx)

    assert result_ctx.processed_output.startswith("🔍 [LỖI CHÍNH]:")
    assert "AssertionError: assert 1 == 2" in result_ctx.processed_output


@pytest.mark.asyncio
async def test_no_fabrication_guard_hook():
    """Kiểm tra NoFabricationGuardHook từ chối bịa đặt nếu chưa đọc tệp."""
    hook = NoFabricationGuardHook()
    step_ctx = StepContext(
        task_id="t1",
        goal="kiểm toán egress_gate.py",
        mode="audit",
        step=2,
        max_steps=10,
        messages=[],
        has_successful_view_file=False,
    )

    approved, rejection = await hook.before_submission(step_ctx, thought="tôi đoán là", final_answer="xong rồi")
    assert approved is False
    assert step_ctx.should_stop is True
    assert "needs_validation" in rejection


@pytest.mark.asyncio
async def test_multi_file_coverage_guard_hook():
    """Kiểm tra MultiFileCoverageGuardHook chặn nộp bài khi thiếu tệp."""
    hook = MultiFileCoverageGuardHook()
    step_ctx = StepContext(
        task_id="t1",
        goal="Kiểm toán 2 tệp: core/security/egress_gate.py và core/security/data_leak_guard.py",
        mode="audit",
        step=2,
        max_steps=10,
        messages=[],
        viewed_files={"core/security/egress_gate.py"},
    )

    approved, rejection = await hook.before_submission(step_ctx, thought="xong", final_answer="Báo cáo đây")
    assert approved is False
    assert "MULTI-FILE GUARD" in rejection
    assert "data_leak_guard.py" in rejection


@pytest.mark.asyncio
async def test_lifecycle_manager_orchestration():
    """Kiểm tra LifecycleManager điều phối chuỗi hooks đúng tuần tự."""
    mgr = LifecycleManager()
    validation_hook = ActionValidationHook(known_tools={"view_file"})
    mgr.register_hook(validation_hook)

    step_ctx = StepContext(
        task_id="t1", goal="test", mode="audit", step=1, max_steps=10, messages=[]
    )
    tool_ctx = ToolInvocationContext(tool="invalid_tool", params={})

    await mgr.run_before_tool_dispatch(step_ctx, tool_ctx)

    assert tool_ctx.is_intercepted is True
    assert "Action không hợp lệ" in (tool_ctx.interception_observation or "")


@pytest.mark.asyncio
async def test_scope_lock_blocks_unscoped_file():
    """Kiểm tra ScopeLock chặn đứng lệnh đọc file nằm ngoài mục tiêu."""
    from core.kernel.agent_lifecycle import ScopeLockAndCoverageCompletionHook
    from core.kernel.coverage_ledger import CoverageLedger

    ledger = CoverageLedger(task_id="t1", goal="Kiểm toán 2 tệp: core/security/egress_gate.py và core/security/data_leak_guard.py")
    hook = ScopeLockAndCoverageCompletionHook()

    step_ctx = StepContext(
        task_id="t1",
        goal="Kiểm toán 2 tệp: core/security/egress_gate.py và core/security/data_leak_guard.py",
        mode="audit",
        step=2,
        max_steps=10,
        messages=[],
        coverage_ledger=ledger,
    )
    # Cố tình gọi đọc canary_guard.py không nằm trong mục tiêu
    tool_ctx = ToolInvocationContext(tool="view_file", params={"path": "core/security/canary_guard.py"})

    await hook.before_tool_dispatch(step_ctx, tool_ctx)

    assert tool_ctx.is_intercepted is True
    assert "SCOPE-VIOLATION BLOCKED" in (tool_ctx.interception_observation or "")


@pytest.mark.asyncio
async def test_completion_lock_blocks_reading_after_100_percent_coverage():
    """Kiểm tra CompletionLock khóa toàn bộ công cụ đọc khi đã đạt 100% độ bao phủ."""
    from core.kernel.agent_lifecycle import ScopeLockAndCoverageCompletionHook
    from core.kernel.coverage_ledger import CoverageLedger

    ledger = CoverageLedger(task_id="t1", goal="Kiểm toán 2 tệp: core/security/egress_gate.py và core/security/data_leak_guard.py")
    ledger.record_file_read("core/security/egress_gate.py")
    ledger.record_file_read("core/security/data_leak_guard.py")

    hook = ScopeLockAndCoverageCompletionHook()

    step_ctx = StepContext(
        task_id="t1",
        goal="Kiểm toán 2 tệp: core/security/egress_gate.py và core/security/data_leak_guard.py",
        mode="audit",
        step=4,
        max_steps=10,
        messages=[],
        coverage_ledger=ledger,
    )
    tool_ctx = ToolInvocationContext(tool="view_file", params={"path": "core/security/egress_gate.py"})

    await hook.before_tool_dispatch(step_ctx, tool_ctx)

    assert tool_ctx.is_intercepted is True
    assert "EVIDENCE COLLECTION 100% COMPLETE" in (tool_ctx.interception_observation or "")

