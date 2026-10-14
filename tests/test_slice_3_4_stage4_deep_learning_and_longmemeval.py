# -*- coding: utf-8 -*-
"""
Behavioral Red-to-Green TDD Suite for Slice 3.4 (Giai đoạn 4 Backlog Master — Học Sâu):
- Item 11: Eval LoRA harness + ms-swift (học GLM):
  * Đánh giá ms-swift (SFT/GRPO) làm trainer Phase 3 thay vì tự đóng.
  * Harness đo trước/sau trên tập held-out độc lập (0 overlap với tập train).
  * Chạy thử 1 vòng LoRA nhỏ end-to-end (train -> eval -> quyết định promote/rollback tự động qua kill-switch).
- Item 12: Eval LongMemEval-style cho episodic (bản Việt nhỏ):
  * Bộ câu hỏi held-out về sự kiện/thời gian bằng tiếng Việt.
  * Điểm baseline + 2 lần đo lại ổn định (dao động < 10%).
- Plus Turn 286 OpenCode improvement #1 & #2:
  * Retry-on-timing-spike (`run_20_case_aci_benchmark_with_timing_retry`) cho `test_aci_20_case_static_benchmark`.
  * Đo độ đồng thuận (agreement) giữa rule-based weak-supervision và model/second-pass classifier trên 20 mẫu.
"""

from __future__ import annotations

import pytest


def test_stage4_11_lora_eval_harness_ms_swift_and_auto_promote_rollback():
    """
    Item 11:
    - Evaluates ms-swift SFT/GRPO trainer contract vs custom loop and exports JSONL + CLI specs.
    - Enforces strict held-out isolation (raises ValueError on train/held-out ID overlap).
    - Runs 1 end-to-end micro LoRA loop (train -> eval on 15 held-out cases -> automatic PROMOTE when improved & 0 safety regressions).
    - Verifies automatic KILL_SWITCH_ROLLBACK when a degraded candidate adapter introduces safety regressions or score drop.
    """
    from core.dataset.dataset_manager import (
        HELD_OUT_LORA_EVAL_SET,
        evaluate_ms_swift_vs_custom_trainer_contract,
        run_end_to_end_lora_eval_loop,
    )

    assert len(HELD_OUT_LORA_EVAL_SET) >= 15

    # 1. Verify ms-swift trainer contract evaluation
    trainer_cmp = evaluate_ms_swift_vs_custom_trainer_contract()
    assert trainer_cmp["selected_trainer"] == "ms-swift"
    assert "sft" in trainer_cmp["supported_stages"]
    assert "grpo" in trainer_cmp["supported_stages"]
    assert trainer_cmp["monolithic_import_adopted"] is False  # Rule 5 compliance

    # 2. Run end-to-end micro LoRA loop on valid training set -> automatic PROMOTE
    e2e_promote = run_end_to_end_lora_eval_loop(simulate_degraded_candidate=False)
    assert e2e_promote["held_out_overlap_count"] == 0
    assert e2e_promote["candidate_score"] > e2e_promote["baseline_score"]
    assert e2e_promote["safety_regression_count"] == 0
    assert e2e_promote["decision"] == "PROMOTE"
    assert e2e_promote["active_adapter"] == e2e_promote["candidate_adapter"]

    # 3. Run end-to-end loop with degraded/unsafe candidate -> automatic KILL_SWITCH_ROLLBACK
    e2e_rollback = run_end_to_end_lora_eval_loop(simulate_degraded_candidate=True)
    assert e2e_rollback["decision"] == "KILL_SWITCH_ROLLBACK"
    assert e2e_rollback["active_adapter"] == e2e_rollback["baseline_adapter"]
    assert e2e_rollback["rollback_executed"] is True

    # 4. Verify strict held-out leakage guard raises ValueError if train IDs overlap held-out IDs
    with pytest.raises(ValueError, match="HELD_OUT_DATA_LEAKAGE"):
        run_end_to_end_lora_eval_loop(
            injected_train_ids=[HELD_OUT_LORA_EVAL_SET[0]["id"]]
        )


def test_stage4_12_longmemeval_vi_episodic_benchmark_and_repeat_stability():
    """
    Item 12:
    - Evaluates LongMemEval-style Vietnamese temporal/event benchmark on EpisodicBrain
      across 12 multi-session events and 12 held-out temporal questions.
    - Measures baseline score + 2 repeat evaluations (with session order perturbation)
      and verifies repeat drift < 10%.
    """
    from core.memory.episodic_brain import (
        LONGMEMEVAL_VI_TIMELINE_SESSIONS,
        LONGMEMEVAL_VI_HELD_OUT_QUESTIONS,
        evaluate_longmemeval_vi_episodic_harness,
    )

    assert len(LONGMEMEVAL_VI_TIMELINE_SESSIONS) >= 10
    assert len(LONGMEMEVAL_VI_HELD_OUT_QUESTIONS) >= 10

    report = evaluate_longmemeval_vi_episodic_harness(repeat_runs=2)
    assert report["question_count"] == len(LONGMEMEVAL_VI_HELD_OUT_QUESTIONS)
    assert len(report["temporal_run_scores"]) == 3  # baseline + 2 repeat runs
    assert report["temporal_mean_score"] > report["naive_baseline_score"]
    assert report["temporal_mean_score"] >= 0.85
    assert report["max_run_drift_pct"] < 10.0


def test_turn286_improvements_flaky_timing_guard_and_weak_supervision_agreement():
    """
    Closes Turn 286 OpenCode improvements:
    1. Best-of-3 timing retry helper in test_slice_1_2b_aci_guarded_edit.py so 1 OS scheduling spike doesn't fail full suite.
    2. Agreement metric between primary rule-based weak-supervision and secondary feature-voting verifier on the 20 revisions.
    """
    from tests.test_slice_1_2b_aci_guarded_edit import run_20_case_aci_benchmark_with_timing_retry
    from core.dataset.dataset_manager import evaluate_chunk_revision_labeling_benchmark

    aci_res = run_20_case_aci_benchmark_with_timing_retry(max_attempts=3, budget_ms=15.0)
    assert aci_res["passed_cases"] == 20
    assert aci_res["max_elapsed_ms"] < 15.0
    assert 1 <= aci_res["attempts_used"] <= 3

    ws_bench = evaluate_chunk_revision_labeling_benchmark()
    assert "rule_vs_verifier_agreement" in ws_bench
    assert ws_bench["rule_vs_verifier_agreement"] >= 0.90
