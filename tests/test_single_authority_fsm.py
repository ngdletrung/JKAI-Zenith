# -*- coding: utf-8 -*-
"""
🧪 TEST SUITE: SINGLE AUTHORITY FSM & STRUCTURED LOGGING
File: tests/test_single_authority_fsm.py
Role: Comprehensive verification for Reliability-First Slice (a)
"""

import json
import pytest
from core.security.single_authority_fsm import (
    SingleAuthorityFSM,
    AuthorityVerdict,
    FSMState,
    FirewallDecisionRecord,
)
from core.observability.structured_logger import (
    StructuredLogger,
    StructuredLogEntry,
    log_structured_event,
)
from core.kernel.execution_integrity import (
    ExecutionIntegrityLayer,
    DecisionOutcome,
    ExecutionDecision,
)
from core.kernel.policy_snapshot import create_policy_snapshot


def test_01_fsm_blacklist_supremacy_blocks_env_file():
    """Blacklist is supreme: .env modification is blocked unconditionally."""
    fsm = SingleAuthorityFSM(mission_id="mission_sec_01")
    snapshot = create_policy_snapshot(
        mission_id="mission_sec_01",
        can_modify_files=True,
        can_delete_files=True
    )
    verdict, reason, record = fsm.evaluate(
        action="write_to_file",
        arguments={"TargetFile": "/workspace/.env", "CodeContent": "SECRET=123"},
        policy_advisory=snapshot
    )
    assert verdict == AuthorityVerdict.DENY
    assert fsm.state == FSMState.DENIED
    assert "prohibited security pattern" in reason
    assert record is not None
    assert record.verdict == "DENY"
    assert record.is_terminal is True


def test_02_fsm_blocks_arbitrary_python_code_execution():
    """Invariant C3: Arbitrary code execution is unconditionally denied."""
    fsm = SingleAuthorityFSM(mission_id="mission_sec_02")
    verdict, reason, record = fsm.evaluate(
        action="python_execute",
        arguments={"code": "import os; os.system('whoami')"}
    )
    assert verdict == AuthorityVerdict.DENY
    assert "Invariant C3" in reason
    assert record.rule_matched == "INVARIANT_C3_ARBITRARY_CODE"


def test_03_fsm_blocks_system_directory_targets():
    """FSM denies paths targeting critical OS system directories."""
    fsm = SingleAuthorityFSM(mission_id="mission_sec_03")
    verdict, reason, record = fsm.evaluate(
        action="write_to_file",
        arguments={"TargetFile": "/etc/shadow", "CodeContent": "hack"}
    )
    assert verdict == AuthorityVerdict.DENY
    assert "protected system directory" in reason


def test_04_fsm_authorized_transition_issues_safe_verdict():
    """Safe action inside workspace reaches AUTHORIZED state."""
    fsm = SingleAuthorityFSM(mission_id="mission_sec_04")
    snapshot = create_policy_snapshot(
        mission_id="mission_sec_04",
        can_modify_files=True
    )
    verdict, reason, record = fsm.evaluate(
        action="write_to_file",
        arguments={"TargetFile": "calculator.py", "CodeContent": "x = 1"},
        policy_advisory=snapshot
    )
    assert verdict == AuthorityVerdict.ALLOW
    assert fsm.state == FSMState.AUTHORIZED
    assert record.grant_id is not None
    assert record.verdict == "ALLOW"


def test_05_fsm_audit_record_conforms_to_14_fields():
    """Audit record must contain all 14 mandatory fields."""
    fsm = SingleAuthorityFSM(mission_id="mission_sec_05", trace_id="tr_fixed_123")
    snapshot = create_policy_snapshot(mission_id="mission_sec_05")
    verdict, reason, record = fsm.evaluate(
        action="view_file",
        arguments={"path": "README.md"},
        policy_advisory=snapshot
    )
    d = record.to_dict()
    mandatory_fields = [
        "timestamp", "mission_id", "trace_id", "action", "target",
        "fsm_state", "verdict", "reason", "risk_level", "rule_matched",
        "caller", "grant_id", "duration_ms", "is_terminal"
    ]
    for field_name in mandatory_fields:
        assert field_name in d, f"Missing audit field: {field_name}"
    assert d["caller"] == "SingleAuthorityFSM"
    assert d["trace_id"] == "tr_fixed_123"


def test_06_structured_logger_emits_valid_json_schema():
    """StructuredLogger output must parse cleanly into standard JSON."""
    logger = StructuredLogger(service_name="test-service")
    json_line = logger.emit(
        message="Execution successfully authorized",
        trace_id="tr_9999",
        tool_name="write_to_file",
        duration_ms=4.52,
        authority_decision="ALLOW",
        extra={"target": "main.py"}
    )
    parsed = json.loads(json_line)
    assert parsed["trace_id"] == "tr_9999"
    assert parsed["tool_name"] == "write_to_file"
    assert parsed["authority_decision"] == "ALLOW"
    assert parsed["duration_ms"] == 4.52
    assert parsed["service"] == "test-service"
    assert parsed["extra"]["target"] == "main.py"


def test_07_execution_integrity_layer_uses_fsm_single_authority():
    """ExecutionIntegrityLayer delegates to FSM as the single authority."""
    layer = ExecutionIntegrityLayer(mission_id="mission_int_01")
    snapshot = create_policy_snapshot(mission_id="mission_int_01", can_modify_files=True)
    
    # Try touching sensitive file: FSM must trigger DENY
    decision = layer.authorize(
        action="write_to_file",
        arguments={"TargetFile": ".env.production", "CodeContent": "KEY=SECRET"},
        snapshot=snapshot
    )
    assert decision.outcome == DecisionOutcome.DENY
    assert "prohibited security pattern" in decision.reason


def test_08_list_dir_parameter_alias_normalization():
    """Verify that list_dir(path='.') is automatically mapped to DirectoryPath via Parameter Aliases."""
    from core.kernel.action_validator import validate_action, ActionDecision
    from core.kernel.tool_contracts import ToolContractRegistry, ListDirContract

    # 1. Direct validation via ToolContractRegistry
    is_valid, err, model = ToolContractRegistry.validate_tool_call("list_dir", {"path": "."})
    assert is_valid is True
    assert isinstance(model, ListDirContract)
    assert model.DirectoryPath == "."

    # 2. End-to-end validate_action check
    verdict = validate_action("list_dir", {"path": "."}, check_firewall=False)
    assert verdict.decision == ActionDecision.PERMIT
    assert "Thiếu tham số bắt buộc" not in verdict.reason


def test_09_view_and_write_file_parameter_aliases():
    """Verify parameter aliases for view_file and write_to_file."""
    from core.kernel.tool_contracts import ToolContractRegistry, ViewFileContract, WriteFileContract

    # view_file with {"path": "main.py"}
    is_valid, err, v_model = ToolContractRegistry.validate_tool_call("view_file", {"path": "main.py"})
    assert is_valid is True
    assert isinstance(v_model, ViewFileContract)
    assert v_model.AbsolutePath == "main.py"

    # write_to_file with {"path": "out.py", "code": "print('ok')"}
    is_valid, err, w_model = ToolContractRegistry.validate_tool_call("write_to_file", {"path": "out.py", "code": "print('ok')"})
    assert is_valid is True
    assert isinstance(w_model, WriteFileContract)
    assert w_model.TargetFile == "out.py"
    assert w_model.CodeContent == "print('ok')"

