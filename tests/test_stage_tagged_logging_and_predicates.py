"""
Unit test suite cho StageFailureTagger và 7-Predicate ModelFailureEvaluator
File: tests/test_stage_tagged_logging_and_predicates.py
"""

import pytest
from core.os.observability.stage_failure_tagger import (
    StageFailureTagger,
    StageName,
    StageOwner,
    StageOutcome,
)
from core.os.cognition.model_failure_predicates import (
    ModelFailureEvaluator,
    ModelFailureReport,
)


def test_stage_failure_tagger_distribution():
    tagger = StageFailureTagger()
    task_id = "test_task_dist_001"

    # Ghi nhận các stage
    tagger.record_stage(task_id, StageName.INGRESS, StageOutcome.PASS, latency_ms=5.0)
    tagger.record_stage(task_id, StageName.ROUTING, StageOutcome.PASS, latency_ms=10.0)
    tagger.record_stage(task_id, StageName.TOOL, StageOutcome.FAIL, owner=StageOwner.EXECUTOR, error_code="HTTP_CONN_ERR", latency_ms=50.0)
    tagger.record_stage(task_id, StageName.MODEL, StageOutcome.FAIL, owner=StageOwner.MODEL, error_code="HALLUCINATED_TOOL", latency_ms=200.0)

    dist = tagger.get_failure_distribution([task_id])
    assert dist["total_failures"] == 2
    assert dist["owner_counts"][StageOwner.EXECUTOR.value] == 1
    assert dist["owner_counts"][StageOwner.MODEL.value] == 1
    assert dist["owner_percentages"][StageOwner.MODEL.value] == 50.0
    # Model failure 50% >= 30% -> trigger labeling
    assert dist["should_trigger_labeling"] is True


def test_p1_context_error_not_attributed_to_model():
    trace = {
        "context": {"kb_context": "Dữ liệu tra cứu: [TIMEOUT] RAG service không phản hồi."},
        "intent": {"mode": "REASONING", "confidence": 0.95},
        "routing": {"pipeline": "fast", "role": "PLANNER", "hardware": "gpu"},
        "authority": {"is_blocked": False},
        "execution": {"tool_name": "none", "available_tools": []},
        "schema_delivery": {"is_corrupted": False, "is_truncated": False},
        "model_output": {"is_action_valid": False, "is_hallucinating": True},
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is False
    assert report.attributed_owner == "RAG"
    assert report.failure_category == "RAG_RETRIEVAL_FAILURE"
    assert report.predicates["P1_context_sufficient"] is False


def test_p4_authority_blocked_not_attributed_to_model():
    trace = {
        "context": {"kb_context": "Context chuẩn"},
        "intent": {"mode": "CODING", "confidence": 0.90},
        "routing": {"pipeline": "deep", "role": "EXECUTOR", "hardware": "gpu"},
        "authority": {"is_blocked": True, "denial_reason": "HARD-DENY: PolicySnapshot forbids delete_file"},
        "execution": {"tool_name": "delete_file", "available_tools": ["delete_file"]},
        "schema_delivery": {"is_corrupted": False, "is_truncated": False},
        "model_output": {"is_action_valid": True},
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is False
    assert report.attributed_owner == "POLICY_KERNEL"
    assert report.failure_category == "AUTHORITY_POLICY_BLOCKED"
    assert report.predicates["P4_authority_granted"] is False


def test_p5_tool_missing_not_attributed_to_model():
    trace = {
        "context": {"kb_context": "Context chuẩn"},
        "intent": {"mode": "CODING", "confidence": 0.90},
        "routing": {"pipeline": "fast", "role": "EXECUTOR", "hardware": "gpu"},
        "authority": {"is_blocked": False},
        "execution": {"tool_name": "non_existent_docker_tool", "available_tools": ["write_to_file", "run_command"]},
        "schema_delivery": {"is_corrupted": False, "is_truncated": False},
        "model_output": {"is_action_valid": True},
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is False
    assert report.attributed_owner == "EXECUTOR"
    assert report.failure_category == "TOOL_INFRASTRUCTURE_UNAVAILABLE"
    assert report.predicates["P5_tool_exists"] is False


def test_p6_schema_cutoff_not_attributed_to_model():
    trace = {
        "context": {"kb_context": "Context chuẩn"},
        "intent": {"mode": "REASONING", "confidence": 0.90},
        "routing": {"pipeline": "fast", "role": "PLANNER", "hardware": "gpu"},
        "authority": {"is_blocked": False},
        "execution": {"tool_name": "view_file", "available_tools": ["view_file"]},
        "schema_delivery": {"is_corrupted": False, "is_truncated": True},
        "model_output": {"is_action_valid": False},
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is False
    assert report.attributed_owner == "RUNTIME"
    assert report.failure_category == "SCHEMA_CORRUPTION_OR_CUTOFF"
    assert report.predicates["P6_schema_intact"] is False


def test_pure_model_behavior_failure_when_all_p1_to_p6_pass():
    trace = {
        "context": {"kb_context": "Context chuẩn mực 100%"},
        "intent": {"mode": "CODING", "confidence": 0.95},
        "routing": {"pipeline": "deep", "role": "EXECUTOR", "hardware": "gpu"},
        "authority": {"is_blocked": False},
        "execution": {"tool_name": "write_to_file", "available_tools": ["write_to_file", "replace_file_content"]},
        "schema_delivery": {"is_corrupted": False, "is_truncated": False},
        "model_output": {
            "is_action_valid": False,
            "is_hallucinating": True,
            "is_premature_stop": True,
        },
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is True
    assert report.attributed_owner == "MODEL"
    assert report.failure_category == "MODEL_BEHAVIOR_FAILURE"
    assert report.predicates["P7_model_diverged"] is True
    # Tất cả P1-P6 phải là True
    for i in range(1, 7):
        key = [k for k in report.predicates.keys() if k.startswith(f"P{i}")][0]
        assert report.predicates[key] is True


def test_no_failure_when_model_and_system_are_clean():
    trace = {
        "context": {"kb_context": "Context chuẩn"},
        "intent": {"mode": "REASONING", "confidence": 0.95},
        "routing": {"pipeline": "fast", "role": "PLANNER", "hardware": "gpu"},
        "authority": {"is_blocked": False},
        "execution": {"tool_name": "write_to_file", "available_tools": ["write_to_file"]},
        "schema_delivery": {"is_corrupted": False, "is_truncated": False},
        "model_output": {"is_action_valid": True, "is_hallucinating": False, "is_premature_stop": False},
    }

    report = ModelFailureEvaluator.evaluate(trace)
    assert report.is_pure_model_failure is False
    assert report.failure_category == "NO_FAILURE_DETECTED"
    assert report.attributed_owner == "NONE"
