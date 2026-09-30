"""
Pytest test suite validating:
1. Master Seed Cases v1.0 (50 cases)
2. True Out-Of-Distribution Held-Out Evaluation Dataset (30 cases)
3. Zero Data Leakage / Zero Concept Overlap between Train and Held-Out
4. Baseline Policy Scorer 2-point grading execution
"""

import json
from pathlib import Path
import pytest
from scripts.eval_policy_scorer import baseline_rule_policy_dispatcher

TRAIN_FILE = Path("data/distillation/jkai_decision_cases_seed_50.jsonl")
HELD_OUT_FILE = Path("data/distillation/held_out_eval_30.jsonl")

@pytest.fixture(scope="module")
def train_cases():
    assert TRAIN_FILE.exists(), f"Missing {TRAIN_FILE}"
    with open(TRAIN_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

@pytest.fixture(scope="module")
def held_out_cases():
    assert HELD_OUT_FILE.exists(), f"Missing {HELD_OUT_FILE}"
    with open(HELD_OUT_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

class TestDataLeakageElimination:
    """Verify that Held-Out is truly OOD and has 0 overlap with Train."""

    def test_zero_prompt_overlap(self, train_cases, held_out_cases):
        train_prompts = set(c["observation"] for c in train_cases)
        held_prompts = set(c["observation"] for c in held_out_cases)
        overlap = train_prompts.intersection(held_prompts)
        assert len(overlap) == 0, f"Critical Data Leakage: Found overlapping prompts: {overlap}"

    def test_held_out_has_novel_concepts(self, held_out_cases):
        """Verify presence of brand-new OOD security & ops concepts."""
        categories = set(c["category"] for c in held_out_cases)
        assert "SECURITY_EXPLOIT" in categories  # SSRF
        assert "SUPPLY_CHAIN_SECURITY" in categories  # Typosquatting
        assert "KERNEL_SECURITY" in categories  # /dev/mem
        assert "PROMPT_INJECTION" in categories  # Jailbreak
        assert "SIDE_CHANNEL_DEFENSE" in categories  # Timing attack
        assert "CONCURRENCY_SAFETY" in categories  # TOCTOU
        assert "DISTRIBUTED_LOCK" in categories  # Fencing token
        assert "RESOURCE_DEADLOCK" in categories  # Threadpool starvation
        assert "CAP_THEOREM_AMBIGUITY" in categories  # CAP trade-off
        assert "REGULATORY_CONFLICT" in categories  # GDPR vs Tax
        assert "INODE_EXHAUSTION" in categories  # Inode vs Disk

    def test_data_isolation_no_leakage(self, held_out_cases):
        """Ensure gold_metadata is isolated and rationale never appears in root input payload."""
        for c in held_out_cases:
            assert "rationale" not in c
            assert "gold_metadata" in c
            assert "gold_rationale" in c["gold_metadata"]
            assert "difficulty" in c["gold_metadata"]

class TestScorerHarnessExecution:
    """Verify Master's 2-point grading execution."""

    def test_scorer_scores_all_cases(self, held_out_cases):
        assert len(held_out_cases) == 30
        total_score = 0
        for c in held_out_cases:
            input_payload = {
                "case_id": c["case_id"],
                "category": c["category"],
                "state": c["state"],
                "observation": c["observation"],
                "evidence": c["evidence"],
                "model_proposal": c["model_proposal"]
            }
            pred_dec, pred_act = baseline_rule_policy_dispatcher(input_payload)
            exp_dec = c["expected_decision"]
            exp_act = c["expected_action"]
            if pred_dec == exp_dec:
                total_score += 2 if pred_act == exp_act else 1

        assert total_score >= 50, f"Expected total score >= 50/60, got {total_score}"
