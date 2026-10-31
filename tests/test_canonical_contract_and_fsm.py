"""
Unit Tests for Phase R1: Canonical Contracts & FSM Engine
File: tests/test_canonical_contract_and_fsm.py
"""

import pytest
import time
from core.contracts.canonical_contract import (
    PolicyDecision,
    CanonicalState,
    VerificationLevel,
    VerificationStatus,
    Mission,
    PlanProposal,
    AuthorizedAction,
    ExecutionReceipt,
    VerificationVerdict,
    CanonicalFSM,
    IllegalStateTransitionError
)


def test_mission_initialization():
    m = Mission(intent="Thực hiện kiểm thử hợp đồng chuẩn hóa Phase R1", risk_level="LOW")
    assert m.mission_id.startswith("m_")
    assert m.state == CanonicalState.RECEIVED
    assert "read" in m.authority_scope
    d = m.to_dict()
    assert d["intent"] == "Thực hiện kiểm thử hợp đồng chuẩn hóa Phase R1"
    assert d["state"] == "RECEIVED"


def test_plan_proposal_has_no_authority():
    """Bảo đảm Model Proposal không thể tự cấp quyền hoặc tự ra quyết định."""
    p = PlanProposal(
        mission_id="m_test123",
        proposed_by="qwen2.5-coder:3b",
        strategy="STEPWISE_VERIFIED",
        steps=[{"step": 1, "action": "read_file", "path": "test.txt"}],
        rationale="Cần đọc file để hiểu nội dung"
    )
    assert p.proposed_by == "qwen2.5-coder:3b"
    assert len(p.steps) == 1
    # Proposal thuần túy là dữ liệu đề xuất, không có method execute hay transition


def test_authorized_action_policy_decision():
    """Hành động chỉ có thể thực thi nếu PolicyDecision là ALLOW."""
    act_denied = AuthorizedAction(
        mission_id="m_test123",
        decision=PolicyDecision.DENY,
        allowed_tool="system_exec"
    )
    assert not act_denied.is_executable()

    act_allowed = AuthorizedAction(
        mission_id="m_test123",
        decision=PolicyDecision.ALLOW,
        allowed_tool="read_file",
        allowed_args={"path": "main.py"}
    )
    assert act_allowed.is_executable()


def test_execution_receipt_and_sha256():
    """Biên lai thực thi ghi nhận kết quả vật lý và SHA-256 chính xác."""
    act = AuthorizedAction(
        mission_id="m_test123",
        decision=PolicyDecision.ALLOW,
        allowed_tool="write_file"
    )
    output_content = "File written successfully: 1234 bytes"
    rcpt = ExecutionReceipt.create(
        action=act,
        tool_name="write_file",
        exit_code=0,
        output_text=output_content,
        artifacts=["output.txt"]
    )
    assert rcpt.exit_code == 0
    assert len(rcpt.stdout_sha256) == 64
    assert rcpt.artifacts == ["output.txt"]


def test_verification_verdict_levels():
    """Kiểm chứng độc lập qua 4 tầng L1-L4 và các tiêu chí nghiệp vụ."""
    vrd = VerificationVerdict(
        mission_id="m_test123",
        receipt_refs=["rcpt_1"],
        status=VerificationStatus.COMPLETE,
        levels_passed={
            VerificationLevel.L1_PHYSICAL.value: True,
            VerificationLevel.L2_SYNTACTIC.value: True,
            VerificationLevel.L3_STRUCTURAL.value: True,
            VerificationLevel.L4_SEMANTIC.value: True,
        },
        criteria_results={"syntax_valid": True, "tests_passed": True}
    )
    assert vrd.is_verified_complete()

    # Thất bại nếu 1 tầng L3 bị fail
    vrd.levels_passed[VerificationLevel.L3_STRUCTURAL.value] = False
    assert not vrd.is_verified_complete()


def test_fsm_happy_path_lifecycle():
    """Vòng đời chuẩn: RECEIVED -> PLANNED -> AUTHORIZED -> EXECUTING -> VERIFYING -> COMPLETE."""
    m = Mission(intent="Happy path test")
    fsm = CanonicalFSM(m)

    assert fsm.current_state == CanonicalState.RECEIVED

    # 1. Controller lập kế hoạch
    fsm.transition(CanonicalState.PLANNED, actor="CONTROLLER", evidence="Proposal drafted")
    assert fsm.current_state == CanonicalState.PLANNED

    # 2. Kernel cấp phép
    fsm.transition(CanonicalState.AUTHORIZED, actor="KERNEL_POLICY_GATE", evidence="Policy passed")
    assert fsm.current_state == CanonicalState.AUTHORIZED

    # 3. Runtime bắt đầu thực thi
    fsm.transition(CanonicalState.EXECUTING, actor="RUNTIME_EXECUTOR", evidence="Action started")
    assert fsm.current_state == CanonicalState.EXECUTING

    # 4. Chuyển sang giai đoạn kiểm chứng
    fsm.transition(CanonicalState.VERIFYING, actor="RUNTIME_EXECUTOR", evidence="Execution done")
    assert fsm.current_state == CanonicalState.VERIFYING

    # 5. Verifier độc lập chứng nhận hoàn thành
    fsm.transition(CanonicalState.COMPLETE, actor="VERIFIER_GATE", evidence="L1-L4 verified 100%")
    assert fsm.current_state == CanonicalState.COMPLETE

    assert len(fsm.history) == 6


def test_fsm_illegal_transition_rejection():
    """FSM từ chối nhảy cóc trạng thái trái phép (ví dụ RECEIVED -> COMPLETE)."""
    m = Mission(intent="Illegal transition test")
    fsm = CanonicalFSM(m)

    with pytest.raises(IllegalStateTransitionError):
        fsm.transition(CanonicalState.COMPLETE, actor="KERNEL", evidence="Cannot jump directly")


def test_fsm_model_actor_invariant_breach():
    """Model tuyệt đối không được phép làm actor thay đổi trạng thái FSM."""
    m = Mission(intent="Model invariant test")
    fsm = CanonicalFSM(m)

    with pytest.raises(PermissionError) as exc_info:
        fsm.transition(CanonicalState.PLANNED, actor="MODEL", evidence="Model trying to transition")
    assert "[INVARIANT-VIOLATION]" in str(exc_info.value)


def test_fsm_non_verifier_cannot_mark_complete():
    """Actor không phải Kernel hay Verifier không thể tự đóng dấu COMPLETE."""
    m = Mission(intent="Verifier authority test")
    fsm = CanonicalFSM(m)
    fsm.transition(CanonicalState.PLANNED, actor="CONTROLLER")
    fsm.transition(CanonicalState.AUTHORIZED, actor="KERNEL_POLICY_GATE")
    fsm.transition(CanonicalState.EXECUTING, actor="RUNTIME_EXECUTOR")
    fsm.transition(CanonicalState.VERIFYING, actor="RUNTIME_EXECUTOR")

    with pytest.raises(PermissionError) as exc_info:
        fsm.transition(CanonicalState.COMPLETE, actor="CONTROLLER", evidence="Controller says complete")
    assert "không có thẩm quyền chứng nhận COMPLETE" in str(exc_info.value)
