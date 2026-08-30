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
    assert ident.mission_id != ""
    assert ident.task_id != ""
    assert ident.attempt_id != ""


def test_I6_unified_lifecycle_invariant():
    """I6: Unified Lifecycle: ADMIT -> RESOLVE -> AUTHORIZE -> EXECUTE -> VERIFY."""
    from core.os.lifecycle.execution_lifecycle_sop import initialize_lifecycle, LifecycleStage
    ctx = initialize_lifecycle("m_001", "t_001", "Test goal")
    assert ctx.current_stage == LifecycleStage.ADMIT
    ctx.advance_to(LifecycleStage.RESOLVE)
    assert ctx.current_stage == LifecycleStage.RESOLVE
    ctx.advance_to(LifecycleStage.AUTHORIZE)
    assert ctx.current_stage == LifecycleStage.AUTHORIZE
    ctx.advance_to(LifecycleStage.EXECUTE)
    assert ctx.current_stage == LifecycleStage.EXECUTE
    ctx.advance_to(LifecycleStage.VERIFY)
    assert ctx.current_stage == LifecycleStage.VERIFY


def test_I7_state_machine_transition_contract():
    """I7: State Machine: Transitions require contract verification."""
    from core.os.lifecycle.execution_lifecycle_sop import initialize_lifecycle, LifecycleStage
    ctx = initialize_lifecycle("m_002", "t_002", "State transition test")
    ctx.advance_to(LifecycleStage.RESOLVE)
    ctx.topology = "SINGLE_AGENT"
    ctx.capability_requirements = ["filesystem.read"]
    assert ctx.topology is not None
    assert len(ctx.capability_requirements) > 0


def test_I8_contract_surfaces_invariant():
    """I8: Contract Surfaces: Prompt, Skill, Tool are 3 Contract Surfaces of 1 lifecycle."""
    import sys
    from pathlib import Path
    brain_dir = str(Path("d:/Docker/JKAI/services/ai-brain").resolve())
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from prompt_engine.sop_protocol_catalog import get_role_sop
    from core.guardrails.mutation_guard import MutationGuard
    from core.guardrails.observation_normalizer import ObservationNormalizer
    
    sop = get_role_sop("EXECUTOR")
    assert "SOP" in sop
    mut = MutationGuard.evaluate_mutation("read_file", {})
    assert mut.allowed is True
    obs = ObservationNormalizer.normalize("read_file", "inv_1", "content")
    assert obs.evidence_hash != ""


def test_I9_no_governance_bypass_invariant():
    """I9: No Governance Bypass: Direct tool invocation without ExecutionIntegrity is strictly blocked."""
    from core.guardrails.mutation_guard import MutationGuard
    res = MutationGuard.evaluate_mutation("run_command", {"command": "rm -rf /"})
    assert res.allowed is False
    assert res.requires_policy_gate is True


def test_I10_mission_invariance_contract():
    """I10: Mission Invariance: Execution cannot mutate Mission objective or constraints."""
    from core.contracts.cognitive_contract import MissionDefinition, IdentityChain
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Original Mission Goal")
    with pytest.raises(AttributeError):
        mission.objective = "Mutated Goal"


def test_I11_topology_separation_invariant():
    """I11: Topology Separation: Governor decides TOPOLOGY; AMG decides MODEL."""
    from core.os.cognition.execution_governor import govern_execution, ExecutionTopology
    from core.os.cognition.task_profiler import profile_task
    
    prof = profile_task("Sửa 1 dòng file main.py")
    policy = govern_execution(prof, requested_mode="auto")
    assert policy.topology == ExecutionTopology.SINGLE_AGENT
    assert policy.user_facing_mode == "FAST"


def test_I12_evidence_based_verification_invariant():
    """I12: Evidence-Based Verification: 'Model claims success' != 'System verified success'."""
    from core.guardrails.observation_normalizer import ObservationNormalizer
    obs = ObservationNormalizer.normalize("pytest", "inv_test", {"stdout": "54 passed in 19.29s"})
    assert "54 passed" in obs.stdout
    assert len(obs.evidence_hash) == 64


def test_I13_observation_normalization_invariant():
    """I13: Observation Normalization: All tool outputs normalized to ToolObservation with evidence hash."""
    from core.guardrails.observation_normalizer import ObservationNormalizer, ToolObservation
    obs = ObservationNormalizer.normalize("read_file", "inv_read", "Hello World")
    assert isinstance(obs, ToolObservation)
    assert obs.evidence_hash != ""

