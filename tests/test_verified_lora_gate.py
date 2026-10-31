"""
Unit Tests for Phase R5: Verified LoRA Gate, Intervention Hierarchy & Learning Loop
File: tests/test_verified_lora_gate.py
"""

import pytest
from core.learning.verified_lora_gate import (
    InterventionType,
    RootCause,
    InterventionSelector,
    GoldTraceLedger,
    LoRAPromotionGate
)


def test_intervention_hierarchy_ordering():
    """Bảo đảm trật tự can thiệp: Prompt -> Memory -> Route -> Tool -> LoRA -> Model Swap."""
    assert InterventionType.PROMPT_CONTEXT < InterventionType.MEMORY_UPDATE
    assert InterventionType.MEMORY_UPDATE < InterventionType.ROUTING_CONTROLLER
    assert InterventionType.ROUTING_CONTROLLER < InterventionType.TOOL_RUNTIME
    assert InterventionType.TOOL_RUNTIME < InterventionType.LORA_FINETUNE
    assert InterventionType.LORA_FINETUNE < InterventionType.MODEL_SWAP


def test_intervention_selection_by_root_cause():
    """Bảo đảm lỗi do context/memory/tool không bị can thiệp sai lầm bằng LoRA."""
    assert InterventionSelector.select_appropriate_intervention(RootCause.MISSING_CONTEXT) == InterventionType.PROMPT_CONTEXT
    assert InterventionSelector.select_appropriate_intervention(RootCause.STALE_MEMORY) == InterventionType.MEMORY_UPDATE
    assert InterventionSelector.select_appropriate_intervention(RootCause.WRONG_ROUTING) == InterventionType.ROUTING_CONTROLLER
    assert InterventionSelector.select_appropriate_intervention(RootCause.TOOL_EXECUTION_FAILURE) == InterventionType.TOOL_RUNTIME
    assert InterventionSelector.select_appropriate_intervention(RootCause.MODEL_REASONING_DEFECT) == InterventionType.LORA_FINETUNE


def test_gold_trace_ledger_threshold():
    """Bảo đảm chỉ kích hoạt LoRA khi có đủ >= 100 gold traces đã xác thực."""
    ledger = GoldTraceLedger()
    assert ledger.is_eligible_for_lora() is False

    for i in range(99):
        ledger.add_trace(f"tr_{i}", "prompt", ["action"], "COMPLETE", "VERIFIER")
    assert ledger.count() == 99
    assert ledger.is_eligible_for_lora() is False

    ledger.add_trace("tr_99", "prompt", ["action"], "COMPLETE", "VERIFIER")
    assert ledger.count() == 100
    assert ledger.is_eligible_for_lora() is True


def test_lora_gate_rejection_insufficient_traces():
    gate = LoRAPromotionGate()
    ok, reason, _ = gate.evaluate_candidate(
        gold_trace_count=45,
        base_model_metrics={"ood_accuracy_pct": 70.0},
        lora_candidate_metrics={"ood_accuracy_pct": 78.0, "base_task_regressions": 0}
    )
    assert ok is False
    assert "REJECTED_INSUFFICIENT_GOLD_TRACES" in reason


def test_lora_gate_rejection_low_gain():
    gate = LoRAPromotionGate(min_ood_gain_pct=3.0)
    ok, reason, meta = gate.evaluate_candidate(
        gold_trace_count=120,
        base_model_metrics={"ood_accuracy_pct": 70.0},
        lora_candidate_metrics={"ood_accuracy_pct": 71.5, "base_task_regressions": 0}
    )
    assert ok is False
    assert "REJECTED_LOW_MARGINAL_GAIN" in reason
    assert meta["marginal_gain_pct"] == 1.5


def test_lora_gate_rejection_regression():
    gate = LoRAPromotionGate(min_ood_gain_pct=2.0, max_allowed_regressions=0)
    ok, reason, meta = gate.evaluate_candidate(
        gold_trace_count=150,
        base_model_metrics={"ood_accuracy_pct": 70.0},
        lora_candidate_metrics={"ood_accuracy_pct": 76.0, "base_task_regressions": 1}
    )
    assert ok is False
    assert "REJECTED_CATASTROPHIC_REGRESSION" in reason
    assert meta["action"] == "ROLLBACK_TO_BASE_MODEL"


def test_lora_gate_clean_promotion():
    gate = LoRAPromotionGate(min_ood_gain_pct=2.0, max_allowed_regressions=0)
    ok, reason, meta = gate.evaluate_candidate(
        gold_trace_count=150,
        base_model_metrics={"ood_accuracy_pct": 70.0},
        lora_candidate_metrics={"ood_accuracy_pct": 75.5, "base_task_regressions": 0}
    )
    assert ok is True
    assert reason == "PROMOTED_VERIFIED_LORA"
    assert meta["status"] == "ACTIVE_IN_PRODUCTION"
    assert meta["marginal_gain_pct"] == 5.5
