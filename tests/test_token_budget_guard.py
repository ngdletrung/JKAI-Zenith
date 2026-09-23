# -*- coding: utf-8 -*-
"""
tests/test_token_budget_guard.py
Unit test suite for TokenBudgetGuard (Giai Đoạn 2: Item 2.2).

Tuân thủ nghiêm ngặt ràng buộc từ Senior Red Team Auditor (Lượt 68):
  1. Vượt 80% -> cảnh báo warn log, không abort.
  2. Vượt 100% -> abort mission (ném TokenBudgetExceededException kế thừa MasterAbortException), trip replan breaker.
  3. Khi usage vắng mặt -> ước lượng heuristic (chars // 4) + warn log, KHÔNG fail-closed.
  4. Stub-only, cấm gọi mạng thật.
  5. Đảm bảo an toàn luồng (thread-safety) khi nhiều worker ghi nhận cùng lúc.
"""

import sys
import os
import threading
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

from core.governance.token_budget_guard import (
    TokenBudgetGuard,
    TokenBudgetConfig,
    TokenBudgetExceededException,
    TokenUsageRecord,
    MissionBudgetLedger,
)
from core.utils.engine import MasterAbortException


class TestTokenBudgetGuard(unittest.TestCase):
    """Bộ kiểm thử cho TokenBudgetGuard theo spec Lượt 68."""

    def setUp(self):
        self.guard = TokenBudgetGuard()
        self.mission_id = "test_mission_budget_001"

    def tearDown(self):
        self.guard.reset(self.mission_id)

    # -------------------------------------------------------------------------
    # 1. Test bình thường trong hạn mức
    # -------------------------------------------------------------------------
    def test_normal_usage_within_budget(self):
        """Tiêu thụ bình thường dưới 80% không cảnh báo, không ném exception."""
        cfg = TokenBudgetConfig(max_total_tokens=1000, warning_threshold_ratio=0.80)
        rec, ledger = self.guard.record_usage(
            mission_id=self.mission_id,
            prompt_tokens=200,
            completion_tokens=300,
            custom_config=cfg
        )
        self.assertEqual(rec.total_tokens, 500)
        self.assertFalse(rec.is_estimated)
        self.assertEqual(ledger.cumulative_total_tokens, 500)
        self.assertFalse(ledger.warned_80)
        self.assertFalse(ledger.tripped)

    # -------------------------------------------------------------------------
    # 2. Test vượt 80% -> Warn log, không abort (Spec 4.1)
    # -------------------------------------------------------------------------
    def test_exceeding_80_percent_triggers_warning_without_abort(self):
        """Vượt 80% hạn mức phải bật cờ warned_80 và không ném lỗi."""
        cfg = TokenBudgetConfig(max_total_tokens=1000, warning_threshold_ratio=0.80)
        # Lần 1: 500 tokens (50%) -> chưa warn
        self.guard.record_usage(
            mission_id=self.mission_id,
            prompt_tokens=200,
            completion_tokens=300,
            custom_config=cfg
        )
        ledger = self.guard.get_or_create_ledger(self.mission_id)
        self.assertFalse(ledger.warned_80)

        # Lần 2: Thêm 350 tokens -> tổng 850 (85%) -> phải bật warn
        with patch.object(self.guard, "_emit_structured_log") as mock_emit:
            rec, ledger = self.guard.record_usage(
                mission_id=self.mission_id,
                prompt_tokens=150,
                completion_tokens=200,
                custom_config=cfg
            )
            self.assertEqual(ledger.cumulative_total_tokens, 850)
            self.assertTrue(ledger.warned_80)
            self.assertFalse(ledger.tripped)
            mock_emit.assert_called_once()
            args, kwargs = mock_emit.call_args
            self.assertEqual(kwargs.get("tag"), "BUDGET_WARNING")

    # -------------------------------------------------------------------------
    # 3. Test vượt 100% -> Abort mission + trip breaker (Spec 4.2)
    # -------------------------------------------------------------------------
    def test_exceeding_100_percent_aborts_mission(self):
        """Vượt 100% hạn mức phải ném TokenBudgetExceededException kế thừa MasterAbortException."""
        cfg = TokenBudgetConfig(max_total_tokens=1000, warning_threshold_ratio=0.80)

        # Tiêu thụ 900 tokens (90%)
        self.guard.record_usage(
            mission_id=self.mission_id,
            prompt_tokens=400,
            completion_tokens=500,
            custom_config=cfg
        )

        # Gọi thêm 200 tokens -> tổng 1100 tokens (> 1000) -> phải trip abort
        with patch.object(self.guard, "_trip_replan_circuit_breaker") as mock_trip:
            with self.assertRaises(TokenBudgetExceededException) as ctx:
                self.guard.record_usage(
                    mission_id=self.mission_id,
                    prompt_tokens=100,
                    completion_tokens=100,
                    custom_config=cfg
                )

            # Phải kế thừa MasterAbortException để dùng chung luồng abort chuẩn
            self.assertIsInstance(ctx.exception, MasterAbortException)
            self.assertIn("Token budget exceeded", str(ctx.exception))

            ledger = self.guard.get_or_create_ledger(self.mission_id)
            self.assertTrue(ledger.tripped)
            self.assertEqual(ledger.cumulative_total_tokens, 1100)
            mock_trip.assert_called_once_with(self.mission_id)

    # -------------------------------------------------------------------------
    # 4. Test usage vắng mặt -> Ước lượng heuristic + warn + KHÔNG abort (Spec 4.3)
    # -------------------------------------------------------------------------
    def test_missing_usage_estimates_heuristically_without_fail_closed(self):
        """Khi usage None từ LLM provider: ước lượng len // 4, đánh dấu is_estimated, không crash."""
        cfg = TokenBudgetConfig(max_total_tokens=10000)
        prompt_sample = "A" * 400      # ~100 tokens
        completion_sample = "B" * 200  # ~50 tokens

        rec, ledger = self.guard.record_usage(
            mission_id=self.mission_id,
            prompt_tokens=None,       # Missing
            completion_tokens=None,   # Missing
            prompt_text=prompt_sample,
            completion_text=completion_sample,
            custom_config=cfg
        )

        self.assertTrue(rec.is_estimated)
        self.assertEqual(rec.prompt_tokens, 100)
        self.assertEqual(rec.completion_tokens, 50)
        self.assertEqual(rec.total_tokens, 150)
        self.assertEqual(ledger.cumulative_total_tokens, 150)
        self.assertFalse(ledger.tripped)

    # -------------------------------------------------------------------------
    # 5. Test an toàn đa luồng (Concurrency Thread-Safety)
    # -------------------------------------------------------------------------
    def test_concurrency_thread_safety(self):
        """50 luồng đồng thời ghi nhận token, tổng tích lũy phải chính xác 100% không mất dữ liệu."""
        cfg = TokenBudgetConfig(max_total_tokens=100000)
        num_threads = 50
        tokens_per_call = 100

        def worker():
            self.guard.record_usage(
                mission_id=self.mission_id,
                prompt_tokens=50,
                completion_tokens=50,
                custom_config=cfg
            )

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ledger = self.guard.get_or_create_ledger(self.mission_id)
        expected_total = num_threads * tokens_per_call
        self.assertEqual(ledger.cumulative_total_tokens, expected_total)
        self.assertEqual(ledger.invocation_count, num_threads)


if __name__ == "__main__":
    unittest.main(verbosity=2)
