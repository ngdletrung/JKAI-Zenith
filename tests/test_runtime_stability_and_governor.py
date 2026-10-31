"""
Unit Tests for Phase R3: Runtime Stability, Resource Governor & Rollback Engine
File: tests/test_runtime_stability_and_governor.py
"""

import os
import pytest
import tempfile
from core.contracts.canonical_contract import (
    CanonicalState,
    CanonicalFSM,
    ExecutionReceipt,
    Mission
)
from core.runtime.governor_and_recovery import (
    ResourceGovernor,
    RollbackManager,
    RecoveryEngine,
    ErrorSeverity
)


def test_resource_governor_hop_limit():
    gov = ResourceGovernor(max_hops=3)
    assert gov.check_hop_budget() is True

    gov.record_hop()
    gov.record_hop()
    gov.record_hop()
    assert gov.check_hop_budget() is False

    with pytest.raises(ResourceWarning):
        gov.record_hop()


def test_resource_governor_token_limit():
    gov = ResourceGovernor(token_budget=100)
    assert gov.check_token_budget(50) is True

    gov.consume_tokens(80)
    assert gov.check_token_budget(30) is False

    with pytest.raises(ResourceWarning):
        gov.consume_tokens(30)


def test_resource_governor_vram_ceiling():
    gov = ResourceGovernor(max_vram_mb=8192.0)
    assert gov.check_vram_ceiling(7500.0) is True
    assert gov.check_vram_ceiling(8200.0) is False


def test_rollback_manager_restore_modified_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "config.json")
        with open(test_file, "w") as f:
            f.write('{"mode": "safe"}')

        mgr = RollbackManager(backup_dir=os.path.join(tmpdir, "backups"))
        mgr.snapshot_file("m_01", test_file)

        # Giả lập model làm hỏng file
        with open(test_file, "w") as f:
            f.write('{"mode": "CORRUPTED_VALUE"}')

        # Thực thi rollback
        restored = mgr.execute_rollback("m_01")
        assert len(restored) == 1
        assert "RESTORED" in restored[0]

        # Kiểm tra nội dung ban đầu đã trở lại
        with open(test_file, "r") as f:
            assert f.read() == '{"mode": "safe"}'


def test_rollback_manager_remove_created_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        new_file = os.path.join(tmpdir, "rogue_file.py")
        mgr = RollbackManager(backup_dir=os.path.join(tmpdir, "backups"))
        mgr.snapshot_file("m_02", new_file)

        # Giả lập model tạo file mới
        with open(new_file, "w") as f:
            f.write("print('bad')")
        assert os.path.exists(new_file)

        # Rollback phải xóa file mới tạo
        restored = mgr.execute_rollback("m_02")
        assert "REMOVED_NEW_FILE" in restored[0]
        assert not os.path.exists(new_file)


def test_rollback_manager_fsm_integration():
    m = Mission(intent="Thử nghiệm rollback FSM")
    fsm = CanonicalFSM(m)
    fsm.transition(CanonicalState.PLANNED, actor="CONTROLLER", evidence="Đã lập kế hoạch")
    fsm.transition(CanonicalState.AUTHORIZED, actor="KERNEL", evidence="Đã duyệt")
    fsm.transition(CanonicalState.EXECUTING, actor="RUNTIME", evidence="Bắt đầu chạy")

    mgr = RollbackManager()
    mgr.execute_rollback(m.mission_id, fsm=fsm)

    assert fsm.current_state == CanonicalState.ROLLED_BACK


def test_recovery_engine_transient_retry():
    engine = RecoveryEngine(max_retries=2)
    receipt = ExecutionReceipt(
        mission_id="m_03",
        tool_name="browser_scrape",
        exit_code=1,
        error_message="Connection reset by peer: timeout"
    )

    strat1 = engine.determine_strategy("m_03", receipt)
    assert strat1["action"] == "RETRY"
    assert strat1["attempt"] == 1

    strat2 = engine.determine_strategy("m_03", receipt)
    assert strat2["action"] == "RETRY"
    assert strat2["attempt"] == 2

    strat3 = engine.determine_strategy("m_03", receipt)
    assert strat3["action"] == "FAIL_AND_ROLLBACK"


def test_recovery_engine_alternative_tool():
    engine = RecoveryEngine()
    receipt = ExecutionReceipt(
        mission_id="m_04",
        tool_name="BROWSER_CONTROL",
        exit_code=1,
        error_message="No module named 'services'"
    )
    strat = engine.determine_strategy("m_04", receipt)
    assert strat["action"] == "FALLBACK_TOOL"
    assert strat["fallback_tool"] == "HTTP_EXECUTOR_FALLBACK"


def test_recovery_engine_fatal_halt():
    engine = RecoveryEngine()
    receipt = ExecutionReceipt(
        mission_id="m_05",
        tool_name="system_exec",
        exit_code=1,
        error_message="Security policy violation: Invariant breached"
    )
    strat = engine.determine_strategy("m_05", receipt)
    assert strat["action"] == "IMMEDIATE_ROLLBACK_AND_HALT"
