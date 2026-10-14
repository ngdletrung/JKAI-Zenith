# -*- coding: utf-8 -*-
"""
tests/test_slice_4_3_tier2_lora_evolution_loop.py
=================================================
[Pha 4 - Slice 4.3: Tier 2 LoRA Evolution Loop with Canary & Instant Rollback]:
Kiểm thử chu trình tự tiến hóa Tầng 2 (Mô hình & Router) có kiểm soát ngân sách:
1. Đánh giá 3 bộ held-out xoay ($H_1, H_2, H_3$ Golden Vault) bảo đảm gain delta >= +0.05,
   repeat drift <= 10%, và zero safety regression.
2. Rào chắn tài nguyên & hạn mức tự trị: Chặn huấn luyện khi tải CPU > 70% hoặc vượt hạn mức tuần.
3. Giám sát Canary cửa sổ trượt 10 missions: Drift > 15% kích hoạt Instant Rollback < 10ms.
4. Cơ chế Fail-Closed Auto-Freeze: 2 lần rollback liên tiếp lập tức đóng băng toàn bộ tiến hóa.
"""

import time
import pytest
from pathlib import Path
import tempfile

from core.os.cognition.rsil_orchestrator import (
    EvolutionTier,
    AutonomousQuotaTracker,
    ChainedPromotionJournal,
    RSILOrchestrator,
)
from core.os.cognition.rsil_tier2_lora_loop import (
    AutonomousLoRAEvolutionLoop,
    CanaryDriftMonitor,
    run_tier2_autonomous_lora_cycle,
    GOLDEN_VAULT_ROTATIONS,
)


def test_slice_4_3_item1_lora_multi_heldout_golden_vault_evaluation():
    """
    Đánh giá ứng viên adapter trên 3 bộ held-out độc lập (H1, H2, H3 Golden Vault):
    - Đạt gain delta >= 0.05 so với baseline.
    - Sai lệch giữa các vòng đánh giá (drift) <= 10%.
    - Safety regression == 0.
    - Tự động thăng cấp vào Canary có chữ ký Operational Witness.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        loop = AutonomousLoRAEvolutionLoop(journal_path=j_path)
        eval_res = loop.evaluate_candidate_on_golden_vault(
            candidate_adapter_id="adapter_candidate_v2_zenith",
            baseline_adapter_id="adapter_baseline_v0",
        )
        assert eval_res["golden_vault_passed"] is True
        assert eval_res["mean_delta"] >= 0.05
        assert eval_res["repeat_drift_pct"] <= 10.0
        assert eval_res["safety_regressions"] == 0

        promo_res = loop.submit_candidate_for_canary_promotion(eval_res)
        assert promo_res["decision"] == "AUTO_PROMOTED_INTO_CANARY"
        assert promo_res["evolution_tier"] == EvolutionTier.TIER2_MODELS_AND_ROUTERS.value
        assert promo_res["witness_signature"] is not None


def test_slice_4_3_item2_resource_and_quota_guard_blocks_overload():
    """
    Rào chắn tài nguyên & hạn mức tuần:
    - Khi CPU load vượt ngưỡng (ví dụ giả lập 85% > 70%) -> từ chối kích hoạt job huấn luyện.
    - Khi hết quota 3 lần/tuần -> chuyển trạng thái FROZEN_QUOTA_EXCEEDED.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        quota = AutonomousQuotaTracker(max_weekly_promotes=3)
        loop = AutonomousLoRAEvolutionLoop(journal_path=j_path, quota_tracker=quota)

        # 1. Kiểm tra rào chắn CPU
        can_train, reason = loop.check_training_resource_budget(simulated_cpu_load_pct=85.0)
        assert can_train is False
        assert "CPU_OVERLOAD" in reason

        # 2. Khi CPU rảnh
        can_train_ok, _ = loop.check_training_resource_budget(simulated_cpu_load_pct=25.0)
        assert can_train_ok is True

        # 3. Sử dụng hết quota 3 lần
        quota.record_promotion("prop_01")
        quota.record_promotion("prop_02")
        quota.record_promotion("prop_03")
        assert quota.is_frozen() is False

        # Lần thứ 4 -> Auto-Freeze
        can_promo, freeze_reason = quota.can_promote()
        assert can_promo is False
        assert "FROZEN_QUOTA_EXCEEDED" in freeze_reason


def test_slice_4_3_item3_canary_sliding_window_instant_rollback():
    """
    Giám sát Canary cửa sổ 10 missions:
    - Khi tỷ lệ lỗi vượt ngưỡng 15% (ví dụ 2 lỗi / 10 missions = 20% > 15%):
      Kích hoạt Instant Auto-Rollback trong < 10ms, phục hồi adapter baseline lập tức.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        monitor = CanaryDriftMonitor(
            journal_path=j_path,
            active_canary_adapter="adapter_candidate_v2_zenith",
            baseline_adapter="adapter_baseline_v0",
        )

        canary_missions = [
            {"mission_id": f"m_{i}", "outcome_ok": True} for i in range(8)
        ] + [
            {"mission_id": "m_8", "outcome_ok": False},
            {"mission_id": "m_9", "outcome_ok": False},
        ]  # 2 fails / 10 missions = 20% > 15%

        res = monitor.evaluate_mission_window(canary_missions)
        assert res["rollback_triggered"] is True
        assert res["active_adapter"] == "adapter_baseline_v0"  # Rolled back to baseline
        assert res["rollback_elapsed_ms"] < 10.0  # < 10ms SLA
        assert res["fail_rate_pct"] == 20.0


def test_slice_4_3_item4_consecutive_rollbacks_trigger_auto_freeze():
    """
    Bảo vệ tối thượng Fail-Closed Auto-Freeze:
    - Khi xảy ra 2 lần rollback liên tiếp -> Khóa cứng tiến hóa (FROZEN_CONSECUTIVE_ROLLBACKS).
    - Mọi đề xuất tiếp theo bị từ chối tuyệt đối cho đến khi Master can thiệp mở khóa.
    """
    with tempfile.TemporaryDirectory() as tmp:
        j_path = Path(tmp) / "journal.jsonl"
        quota = AutonomousQuotaTracker(max_consecutive_rollbacks=2)
        monitor = CanaryDriftMonitor(
            journal_path=j_path,
            quota_tracker=quota,
            active_canary_adapter="adapter_cand_a",
            baseline_adapter="adapter_base",
        )

        failing_missions = [
            {"mission_id": f"m_{i}", "outcome_ok": i < 7} for i in range(10)
        ]  # 3 fails = 30% > 15%

        # Rollback lần 1
        res1 = monitor.evaluate_mission_window(failing_missions)
        assert res1["rollback_triggered"] is True
        assert quota.is_frozen() is False
        assert quota.consecutive_rollbacks == 1

        # Rollback lần 2 liên tiếp
        res2 = monitor.evaluate_mission_window(failing_missions)
        assert res2["rollback_triggered"] is True
        assert quota.is_frozen() is True
        assert quota.state == "FROZEN_CONSECUTIVE_ROLLBACKS"

        # Đề xuất mới bị từ chối
        orchestrator = RSILOrchestrator(journal_path=j_path, quota_tracker=quota)
        blocked_res = orchestrator.evaluate_and_autonomous_promote({
            "proposal_id": "prop_after_freeze",
            "affected_files": ["models/adapter_test"],
        })
        assert blocked_res["decision"] == "REFUSED_SYSTEM_FROZEN"
