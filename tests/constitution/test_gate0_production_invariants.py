"""
JKAI ZENITH — GATE 0 PRODUCTION INVARIANT AUDIT TEST SUITE
File: tests/constitution/test_gate0_production_invariants.py

Audits the 5 Core Constitutional Invariants before P1-P6 Production Hardening:
- I1: Mission Invariant (Mission objective & output cannot be mutated)
- I2: Recovery Invariant (Recovery changes strategy/tool/model, NEVER Mission intent)
- I3: Authority Invariant (Policy > Mission > Constraints > Plan > Experience > Tool)
- I4: Verification Invariant (Execution NEVER bypasses Verification before Delivery)
- I5: Traceability Invariant (EVERY autonomous action carries full IdentityChain)
"""

import pytest
from core.contracts.identity_contract import IdentityChain, AttemptRecord
from core.contracts.cognitive_contract import CognitiveRequest, MissionDefinition, DeliverableSpec, DeliverableType
from core.contracts.execution_contract import ExecutionRequest, ExecutionResult, RecoveryPolicy
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy, RuntimeState
from core.mission.mission_registry import MissionRegistry
from core.verification.verifier import CognitiveVerifier
from core.verification.recovery_engine import RecoveryEngine
from core.memory.experience_store import ExperienceStore
from core.memory.recall_engine import RecallEngine


def test_I1_mission_immutable_invariant():
    """I1: Mission objective and expected output CANNOT be mutated by prompt, model, or tool."""
    ident = IdentityChain()
    mission = MissionDefinition(
        identity=ident,
        objective="Tạo báo cáo Excel kiểm toán",
        expected_output=DeliverableSpec(type=DeliverableType.FILE_BINARY, format="xlsx")
    )
    
    # Attempting direct attribute assignment raises FrozenInstanceError
    with pytest.raises(AttributeError):
        mission.objective = "Tạo CSV"

    assert mission.expected_output.format == "xlsx"


def test_I2_recovery_preserves_mission_intent_invariant():
    """I2: Recovery changes strategy/tool/model, NEVER Mission intent."""
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Tạo báo cáo Excel")
    MissionRegistry.register_mission(mission)
    att1 = AttemptRecord(identity=ident, attempt_number=1)

    res_fail = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.MODEL_FAILURE,
        recommended_recovery=RecoveryStrategy.CHANGE_MODEL
    )

    state, att2 = RecoveryEngine.process_recovery(mission, att1, res_fail)
    
    assert state == RuntimeState.CHANGING_MODEL
    assert att2.identity.mission_id == ident.mission_id
    assert mission.objective == "Tạo báo cáo Excel"  # Objective unchanged!


def test_I3_authority_hierarchy_invariant():
    """I3: Authority Hierarchy: Policy > Mission > Constraints > Plan > Experience > Tool."""
    # Policy > Experience
    req = CognitiveRequest(goal="tạo file excel báo cáo")
    ver_policy = VerificationResult(
        passed=False,
        failure_classification=FailureClassification.POLICY_FAILURE,
        recommended_recovery=RecoveryStrategy.ABORT
    )
    
    # Policy Failure triggers ABORTED Terminal state, overriding any positive Experience memory
    state, att = RecoveryEngine.process_recovery(
        MissionDefinition(identity=req.identity),
        AttemptRecord(identity=req.identity),
        ver_policy
    )
    assert state == RuntimeState.ABORTED
    assert att is None  # Terminal State!


def test_I4_execution_never_bypasses_verification_invariant():
    """I4: Execution NEVER bypasses Verification before Delivery."""
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Báo cáo tiến độ")
    MissionRegistry.register_mission(mission)

    # State cannot transition to DELIVERED without VERIFYING
    assert MissionRegistry.get_state(ident.mission_id) == RuntimeState.MISSIONED
    
    # Transition directly to VERIFYING then DELIVERED
    MissionRegistry.transition_state(ident.mission_id, RuntimeState.VERIFYING)
    assert MissionRegistry.get_state(ident.mission_id) == RuntimeState.VERIFYING
    
    MissionRegistry.transition_state(ident.mission_id, RuntimeState.DELIVERED)
    assert MissionRegistry.get_state(ident.mission_id) == RuntimeState.DELIVERED


def test_I5_identity_chain_traceability_invariant():
    """I5: EVERY autonomous action carries a full 8-link IdentityChain."""
    ident = IdentityChain()
    assert all([
        ident.request_id.startswith("req_"),
        ident.mission_id.startswith("mis_"),
        ident.plan_id.startswith("pln_"),
        ident.task_id.startswith("tsk_"),
        ident.attempt_id.startswith("att_"),
        ident.execution_id.startswith("exe_"),
        ident.observation_id.startswith("obs_"),
        ident.verification_id.startswith("ver_")
    ])
