# -*- coding: utf-8 -*-
"""
🏛️ JKAI ZENITH — TOKEN BUDGET GUARD (P1 / Giai Đoạn 2: Item 2.2)
File: core/governance/token_budget_guard.py

Role:
  Kiểm soát chi phí và ngân sách Token cho từng Mission/Task.
  Chặn đứng rủi ro "đốt token vô hạn" khi gặp vòng lặp lỗi hoặc hallucination loop.

Ràng buộc thiết kế từ Senior Red Team Auditor (Lượt 68):
  1. Đếm tập trung: sử dụng eval_count/prompt_eval_count từ Ollama / LLM provider.
  2. Khi usage vắng mặt: ước lượng heuristic (chars // 4) + log warning, KHÔNG fail-closed.
  3. Ngưỡng 80%: phát cảnh báo structured log [BUDGET_WARNING].
  4. Ngưỡng 100%: abort mission (ném TokenBudgetExceededException), đánh dấu FAILED,
     đồng thời trip replan circuit breaker.
  5. Thread-safe tracking theo task_id / mission_id.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, Tuple

from core.utils.engine import MasterAbortException

logger = logging.getLogger("TokenBudgetGuard")


class TokenBudgetExceededException(MasterAbortException):
    """
    Ném ra khi một mission tiêu thụ vượt quá 100% ngân sách token cho phép.
    Kế thừa MasterAbortException để tái sử dụng toàn bộ luồng abort chuẩn của JKAI (không đẻ đường thứ 2).
    """
    pass


@dataclass
class TokenBudgetConfig:
    """Cấu hình hạn mức ngân sách token."""
    max_total_tokens: int = 50000
    warning_threshold_ratio: float = 0.80
    max_estimated_cost_usd: float = 0.20


@dataclass
class TokenUsageRecord:
    """Bản ghi đo lường một lần suy luận (inference invocation)."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    is_estimated: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class MissionBudgetLedger:
    """Sổ cái ngân sách tích lũy của một mission."""
    mission_id: str
    config: TokenBudgetConfig
    cumulative_prompt_tokens: int = 0
    cumulative_completion_tokens: int = 0
    cumulative_total_tokens: int = 0
    invocation_count: int = 0
    warned_80: bool = False
    tripped: bool = False
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "max_total_tokens": self.config.max_total_tokens,
            "cumulative_prompt_tokens": self.cumulative_prompt_tokens,
            "cumulative_completion_tokens": self.cumulative_completion_tokens,
            "cumulative_total_tokens": self.cumulative_total_tokens,
            "invocation_count": self.invocation_count,
            "warned_80": self.warned_80,
            "tripped": self.tripped,
            "last_updated": self.last_updated,
        }


class TokenBudgetGuard:
    """
    Bộ bảo vệ ngân sách token và chi phí tập trung.
    Singleton hoặc instance-based với Thread-Lock bảo đảm tính toàn vẹn.
    """

    DEFAULT_BUDGET_TOKENS: int = 50000
    WARNING_RATIO: float = 0.80

    def __init__(self):
        self._ledgers: Dict[str, MissionBudgetLedger] = {}
        self._lock = threading.RLock()

    def get_or_create_ledger(
        self,
        mission_id: str,
        custom_config: Optional[TokenBudgetConfig] = None,
    ) -> MissionBudgetLedger:
        """Lấy sổ cái ngân sách hoặc tạo mới với cấu hình tùy biến."""
        with self._lock:
            if mission_id not in self._ledgers:
                cfg = custom_config or TokenBudgetConfig(
                    max_total_tokens=self.DEFAULT_BUDGET_TOKENS,
                    warning_threshold_ratio=self.WARNING_RATIO
                )
                self._ledgers[mission_id] = MissionBudgetLedger(
                    mission_id=mission_id,
                    config=cfg
                )
            return self._ledgers[mission_id]

    def record_usage(
        self,
        mission_id: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        prompt_text: str = "",
        completion_text: str = "",
        custom_config: Optional[TokenBudgetConfig] = None,
    ) -> Tuple[TokenUsageRecord, MissionBudgetLedger]:
        """
        Ghi nhận lượng token tiêu thụ từ một lượt gọi chat/generate.

        Quy tắc:
        1. Nếu prompt_tokens hoặc completion_tokens bị thiếu -> Ước lượng heuristic (len // 4)
           và log WARN, KHÔNG được fail-closed.
        2. Tích lũy vào ledger.
        3. Nếu tích lũy >= 80% hạn mức: Ghi log [BUDGET_WARNING].
        4. Nếu tích lũy > 100% hạn mức:
           - Đánh dấu tripped = True.
           - Trip replan circuit breaker (nếu có thể nạp).
           - Ném TokenBudgetExceededException.
        """
        is_estimated = False

        # Heuristic estimation fallback khi usage không có sẵn từ LLM provider
        p_tok = prompt_tokens
        if p_tok is None or p_tok < 0:
            p_tok = max(1, len(prompt_text) // 4) if prompt_text else 0
            is_estimated = True
            logger.warning(
                "[BUDGET_USAGE_ESTIMATED] Mission %s: prompt_tokens missing, estimated %d from chars",
                mission_id, p_tok
            )

        c_tok = completion_tokens
        if c_tok is None or c_tok < 0:
            c_tok = max(1, len(completion_text) // 4) if completion_text else 0
            is_estimated = True
            logger.warning(
                "[BUDGET_USAGE_ESTIMATED] Mission %s: completion_tokens missing, estimated %d from chars",
                mission_id, c_tok
            )

        call_total = p_tok + c_tok
        usage_rec = TokenUsageRecord(
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            total_tokens=call_total,
            is_estimated=is_estimated,
            timestamp=time.time()
        )

        with self._lock:
            ledger = self.get_or_create_ledger(mission_id, custom_config)
            ledger.cumulative_prompt_tokens += p_tok
            ledger.cumulative_completion_tokens += c_tok
            ledger.cumulative_total_tokens += call_total
            ledger.invocation_count += 1
            ledger.last_updated = time.time()

            max_limit = ledger.config.max_total_tokens
            warn_limit = int(max_limit * ledger.config.warning_threshold_ratio)

            # Kiểm tra ngưỡng 80% (Warning)
            if ledger.cumulative_total_tokens >= warn_limit and not ledger.warned_80:
                ledger.warned_80 = True
                pct = (ledger.cumulative_total_tokens / max_limit) * 100.0
                logger.warning(
                    "[BUDGET_WARNING] Mission %s consumed %d/%d tokens (%.1f%% of budget)",
                    mission_id, ledger.cumulative_total_tokens, max_limit, pct
                )
                self._emit_structured_log(
                    level="WARN",
                    tag="BUDGET_WARNING",
                    mission_id=mission_id,
                    tokens_used=ledger.cumulative_total_tokens,
                    max_tokens=max_limit,
                    percentage=round(pct, 1)
                )

            # Kiểm tra ngưỡng 100% (Abort)
            if ledger.cumulative_total_tokens > max_limit:
                ledger.tripped = True
                pct = (ledger.cumulative_total_tokens / max_limit) * 100.0
                err_msg = (
                    f"Token budget exceeded for mission {mission_id}: "
                    f"consumed {ledger.cumulative_total_tokens} tokens > limit {max_limit} (trip at {pct:.1f}%)"
                )
                logger.error("[BUDGET_EXCEEDED] %s", err_msg)
                self._emit_structured_log(
                    level="CRITICAL",
                    tag="BUDGET_EXCEEDED",
                    mission_id=mission_id,
                    tokens_used=ledger.cumulative_total_tokens,
                    max_tokens=max_limit,
                    percentage=round(pct, 1)
                )

                # Cắt cầu dao replan-breaker để chặn retry storm
                self._trip_replan_circuit_breaker(mission_id)

                raise TokenBudgetExceededException(err_msg)

            return usage_rec, ledger

    def _trip_replan_circuit_breaker(self, mission_id: str):
        """Kích hoạt cầu dao ngắt replan để ngăn retry storm khi đã cháy ngân sách."""
        try:
            from core.recovery.replan_circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker(mission_id)
            if cb and hasattr(cb, "trip"):
                cb.trip(reason=f"Token budget exceeded for mission {mission_id}")
                logger.info("[BUDGET-GUARD] Replan circuit breaker tripped for mission %s", mission_id)
        except Exception as e:
            logger.debug("[BUDGET-GUARD] Could not trip replan breaker: %s", e)

    def _emit_structured_log(self, level: str, tag: str, mission_id: str, **kwargs):
        """Phát log cấu trúc JSON đồng bộ với hệ thống telemetry."""
        try:
            from core.utils.structured_logger import log_structured_event
            log_structured_event(
                event_type="TOKEN_BUDGET_EVENT",
                mission_id=mission_id,
                payload={"tag": tag, "level": level, **kwargs}
            )
        except Exception:
            pass

    def reset(self, mission_id: str):
        """Xóa sạch sổ cái của một mission sau khi hoàn tất."""
        with self._lock:
            self._ledgers.pop(mission_id, None)


# Global singleton instance
token_budget_guard = TokenBudgetGuard()
