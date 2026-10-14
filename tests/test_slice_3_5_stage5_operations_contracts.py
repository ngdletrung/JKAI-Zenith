# -*- coding: utf-8 -*-
"""
Behavioral Red-to-Green TDD Suite for Slice 3.5 (Giai đoạn 5 Backlog Master — Vận Hành):
- Item 13: Boot page thường trực (học Hindsight):
  * Tier0 + quy ước mission thành 1 đọc rẻ lúc khởi động.
  * Session mới trả lời 6 câu hỏi kiến trúc không cần retrieval (`retrieval_calls_made == 0`),
    tiết kiệm đo được >= 30% token khởi động.
- Item 14: Fork/rewind nhánh đọc (học WeKnora):
  * Rewind + rẽ nhánh thử phương án B cho nhánh đọc/lập kế hoạch; cấm replay với `IRREVERSIBLE_EXTERNAL`.
  * Demo 1 mission rẽ nhánh thất bại rollback sạch 100% rồi chạy nhánh B thành công.
- Item 15: Chunk versioning (học WeKnora):
  * Tri thức dài hạn có version + diff + rollback.
  * Sửa -> rollback khôi phục đúng bản cũ 10/10.
- Plus Turn 288 OpenCode improvement #1:
  * Ngưỡng cảnh báo `drift_alert_status` (> 15% -> `CRITICAL_DRIFT_ALERT`) trong LongMemEval-VI harness.
"""

from __future__ import annotations

from pathlib import Path


def test_stage5_13_always_on_tier0_boot_page_6_questions_and_30pct_token_savings():
    """
    Item 13:
    - Compiles Tier0 + mission conventions into a single-read Boot Page.
    - A fresh session answers 6 architectural questions (`Q1..Q6`) strictly from the Boot Page
      with 0 retrieval calls (`retrieval_calls_made == 0`, `questions_answered_correctly == 6`).
    - Real measured token savings vs cold-start multi-read context is >= 30%.
    """
    from core.utils.repo_map import (
        build_always_on_tier0_boot_page,
        evaluate_boot_page_token_savings_benchmark,
    )

    boot_page = build_always_on_tier0_boot_page()
    assert isinstance(boot_page["boot_page_text"], str)
    assert boot_page["boot_page_tokens"] > 0

    bench = evaluate_boot_page_token_savings_benchmark()
    assert bench["questions_total"] == 6
    assert bench["questions_answered_correctly"] == 6
    assert bench["retrieval_calls_made"] == 0
    assert bench["boot_page_single_read_tokens"] < bench["cold_start_multi_read_tokens"]
    assert bench["token_savings_pct"] >= 30.0


def test_stage5_14_fork_rewind_read_branch_mission_demo_100pct_clean_rollback(tmp_path: Path):
    """
    Item 14:
    - Demo 1 mission that forks Plan Branch A, modifies sandbox planning files, attempts to replay
      an IRREVERSIBLE_EXTERNAL tool (which is refused), fails Branch A, rolls back 100% cleanly
      to checkpoint, and succeeds on Plan Branch B.
    """
    from core.os.cognition.worktree_sandbox import run_fork_rewind_failed_branch_mission_demo

    demo = run_fork_rewind_failed_branch_mission_demo(base_root=tmp_path)
    assert demo["branch_a_status"] == "FAILED_AND_ROLLED_BACK"
    assert demo["irreversible_replay_refused"] is True
    assert demo["clean_rollback_100pct"] is True
    assert demo["leftover_branch_a_artifacts"] == 0
    assert demo["post_rewind_sha256_matches_checkpoint"] is True
    assert demo["branch_b_status"] == "COMPLETED_VERIFIED"


def test_stage5_15_chunk_versioning_diff_and_rollback_10_of_10():
    """
    Item 15:
    - Long-term knowledge chunks support version + line diff + rollback.
    - Across 10 knowledge chunks edited and then rolled back, 10/10 restore the exact prior version content & SHA-256.
    """
    from core.utils.repo_map import evaluate_10_chunk_versioning_rollback_benchmark

    bench = evaluate_10_chunk_versioning_rollback_benchmark()
    assert bench["total_chunks"] == 10
    assert bench["diffs_verified"] == 10
    assert bench["exact_rollbacks_verified"] == 10
    assert bench["rollback_success_rate"] == 1.0


def test_turn288_improvement_longmemeval_drift_alert_threshold():
    """
    Closes Turn 288 OpenCode improvement #1:
    - LongMemEval-VI harness includes explicit `drift_warning_threshold_pct` (10.0%),
      `drift_critical_alert_threshold_pct` (15.0%), and `drift_alert_status` ("OK" vs "CRITICAL_DRIFT_ALERT").
    """
    from core.memory.episodic_brain import (
        classify_longmemeval_drift_alert,
        evaluate_longmemeval_vi_episodic_harness,
    )

    report = evaluate_longmemeval_vi_episodic_harness(repeat_runs=2)
    assert report["drift_warning_threshold_pct"] == 10.0
    assert report["drift_critical_alert_threshold_pct"] == 15.0
    assert report["drift_alert_status"] == "OK"

    assert classify_longmemeval_drift_alert(4.5) == "OK"
    assert classify_longmemeval_drift_alert(12.0) == "WARNING_INVESTIGATE"
    assert classify_longmemeval_drift_alert(18.2) == "CRITICAL_DRIFT_ALERT"
