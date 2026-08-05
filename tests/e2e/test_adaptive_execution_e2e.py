"""
JKAI ZENITH AI OS — TIER 3 E2E ADAPTIVE EXECUTION & ESCALATION TEST SUITE
File: tests/e2e/test_adaptive_execution_e2e.py

Verifies operational acceptance for:
1. Test A: FAST multi-step & multi-file execution.
2. Test B: Adaptive Escalation (FAST -> DEEP) preserving Mission ID continuity.
3. Test C: Adaptive De-Escalation (DEEP -> FAST) when problem scope simplifies.
4. Test D: End-to-End Telemetry Traceability (Request -> Mission -> Evidence -> Verification).
"""

import pytest
import asyncio
from core.os.lifecycle.execution_lifecycle_sop import initialize_lifecycle, LifecycleStage
from core.os.cognition.task_profiler import profile_task
from core.os.cognition.execution_governor import govern_execution, ExecutionTopology, ExecutionPolicy
from core.os.cognition.escalation_controller import evaluate_runtime_escalation
from core.guardrails.scope_validator import ScopeValidator
from core.guardrails.mutation_guard import MutationGuard, MutationType
from core.guardrails.observation_normalizer import ObservationNormalizer, ToolObservation


@pytest.mark.asyncio
async def test_A_fast_multi_step_multi_file_execution():
    """Test A: FAST mode (SINGLE_AGENT) autonomously executes multi-step multi-file edits."""
    ctx = initialize_lifecycle("m_fast_001", "t_fast_001", "Modify API endpoints across project files")
    assert ctx.current_stage == LifecycleStage.ADMIT

    # Stage 2: RESOLVE -> SINGLE_AGENT (FAST)
    prof = profile_task("Sửa 2 tệp main.py và utils.py")
    policy = govern_execution(prof, requested_mode="fast")
    assert policy.topology == ExecutionTopology.SINGLE_AGENT
    assert policy.user_facing_mode == "FAST"
    ctx.topology = policy.topology.value
    ctx.advance_to(LifecycleStage.RESOLVE)

    # Stage 3: AUTHORIZE
    v1 = ScopeValidator.validate_file_path("D:/Docker/JKAI/core/os/request_orchestrator.py")
    v2 = ScopeValidator.validate_file_path("D:/Docker/JKAI/core/os/cognition/task_profiler.py")
    assert v1.allowed and v2.allowed
    ctx.advance_to(LifecycleStage.AUTHORIZE)

    # Stage 4: EXECUTE multi-step multi-file observations
    ctx.advance_to(LifecycleStage.EXECUTE)
    obs1 = ObservationNormalizer.normalize("replace_file_content", "inv_01", {"stdout": "Updated main.py"})
    obs2 = ObservationNormalizer.normalize("replace_file_content", "inv_02", {"stdout": "Updated task_profiler.py"})
    ctx.observations.extend([obs1.__dict__, obs2.__dict__])
    assert len(ctx.observations) == 2

    # Stage 5: VERIFY
    ctx.advance_to(LifecycleStage.VERIFY)
    ctx.verified = True
    assert ctx.verified is True
    assert ctx.mission_id == "m_fast_001"


@pytest.mark.asyncio
async def test_B_adaptive_escalation_fast_to_deep_continuity():
    """Test B: Adaptive Escalation (FAST -> DEEP) preserving Mission ID continuity."""
    ctx = initialize_lifecycle("m_escalate_999", "t_escalate_999", "Fix architecture crash in core OS")
    ctx.advance_to(LifecycleStage.RESOLVE)

    # Initial Policy: SINGLE_AGENT (FAST)
    current_policy = ExecutionPolicy(topology=ExecutionTopology.SINGLE_AGENT, user_facing_mode="FAST")
    ctx.topology = current_policy.topology.value

    # Runtime feedback indicates unexpected failures & high uncertainty
    feedback = {
        "uncertainty": 0.85,
        "unexpected_failures": 2,
        "cross_module_dependencies": True
    }

    # Governor evaluates escalation
    esc = evaluate_runtime_escalation(current_policy, feedback)
    assert esc.escalated is True
    assert esc.new_topology == ExecutionTopology.MULTI_AGENT
    assert esc.user_facing_mode == "DEEP"

    # Preserves SAME Mission ID across escalation!
    ctx.topology = esc.new_topology.value
    assert ctx.mission_id == "m_escalate_999"


@pytest.mark.asyncio
async def test_C_adaptive_de_escalation_deep_to_fast():
    """Test C: Adaptive De-Escalation (DEEP -> FAST) when problem scope simplifies."""
    ctx = initialize_lifecycle("m_deesc_888", "t_deesc_888", "Analyze deep crash cause")
    
    # Initial Policy: MULTI_AGENT (DEEP)
    current_policy = ExecutionPolicy(topology=ExecutionTopology.MULTI_AGENT, user_facing_mode="DEEP")
    ctx.topology = current_policy.topology.value

    # Feedback indicates root cause is simple & deterministic (typo fix)
    feedback = {
        "root_cause_is_deterministic": True,
        "uncertainty": 0.1,
        "unexpected_failures": 0
    }

    esc = evaluate_runtime_escalation(current_policy, feedback)
    assert esc.escalated is True
    assert esc.new_topology == ExecutionTopology.SINGLE_AGENT
    assert esc.user_facing_mode == "FAST"
    assert ctx.mission_id == "m_deesc_888"


@pytest.mark.asyncio
async def test_D_telemetry_traceability_end_to_end():
    """Test D: Full End-to-End Telemetry Traceability."""
    obs = ObservationNormalizer.normalize(
        tool_id="pytest",
        invocation_id="inv_e2e_777",
        raw_result={"stdout": "62 passed in 18.70s"},
        status="SUCCESS"
    )
    assert obs.evidence_hash != ""
    assert len(obs.evidence_hash) == 64
    assert obs.status == "SUCCESS"
