"""
JKAI ZENITH AI OS — TIER 1 CONTRACT SCHEMAS TEST SUITE
File: tests/contracts/test_sop_v2_contracts.py

Verifies contract integrity for Execution Lifecycle, Scope Validator, Mutation Guard, and Observation Normalizer.
"""

import pytest
from core.os.lifecycle.execution_lifecycle_sop import initialize_lifecycle, LifecycleStage
from core.guardrails.scope_validator import ScopeValidator
from core.guardrails.mutation_guard import MutationGuard, MutationType
from core.guardrails.observation_normalizer import ObservationNormalizer, ToolObservation


def test_execution_lifecycle_stages():
    ctx = initialize_lifecycle("m_001", "t_001", "Fix bug in JKAI")
    assert ctx.current_stage == LifecycleStage.ADMIT
    
    ctx.advance_to(LifecycleStage.RESOLVE)
    assert ctx.current_stage == LifecycleStage.RESOLVE
    
    ctx.advance_to(LifecycleStage.AUTHORIZE)
    assert ctx.current_stage == LifecycleStage.AUTHORIZE
    
    ctx.advance_to(LifecycleStage.EXECUTE)
    assert ctx.current_stage == LifecycleStage.EXECUTE
    
    ctx.advance_to(LifecycleStage.VERIFY)
    assert ctx.current_stage == LifecycleStage.VERIFY


def test_scope_validator_workspace_bounds():
    # Valid workspace path
    res = ScopeValidator.validate_file_path("D:/Docker/JKAI/core/os/request_orchestrator.py")
    assert res.allowed is True
    
    # Forbidden sensitive path
    res_forbidden = ScopeValidator.validate_file_path("D:/Docker/JKAI/.env")
    assert res_forbidden.allowed is False
    assert "forbidden" in res_forbidden.reason.lower()


def test_mutation_guard_classification():
    # Read-only tool
    res_read = MutationGuard.evaluate_mutation("read_file", {"path": "d:/Docker/JKAI/README.md"})
    assert res_read.mutation_type == MutationType.READ_ONLY
    assert res_read.allowed is True
    
    # Safe mutation tool
    res_write = MutationGuard.evaluate_mutation("replace_file_content", {"path": "d:/Docker/JKAI/main.py"})
    assert res_write.mutation_type == MutationType.SAFE_MUTATION
    assert res_write.allowed is True
    
    # Destructive command
    res_dest = MutationGuard.evaluate_mutation("run_command", {"command": "rm -rf /"})
    assert res_dest.mutation_type == MutationType.DESTRUCTIVE_MUTATION
    assert res_dest.allowed is False
    assert res_dest.requires_policy_gate is True


def test_observation_normalizer_sha256():
    obs = ObservationNormalizer.normalize(
        tool_id="read_file",
        invocation_id="inv_123",
        raw_result={"stdout": "file content line 1", "stderr": ""},
        status="SUCCESS"
    )
    assert isinstance(obs, ToolObservation)
    assert obs.status == "SUCCESS"
    assert obs.stdout == "file content line 1"
    assert len(obs.evidence_hash) == 64  # Valid SHA-256 hex string
