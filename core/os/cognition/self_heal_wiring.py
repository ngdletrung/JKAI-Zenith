# -*- coding: utf-8 -*-
"""
core/os/cognition/self_heal_wiring.py
======================================
Slice Self-Heal Wiring Coordinator.
Đấu nối 4 dây kệ chết:
- Dây 1: Chẩn đoán & Gán nhãn lỗi (ErrorClassifier -> FailureMemory)
- Dây 2: Sinh bản vá ứng viên có kiểm soát (GovernedAutoPatcher)
- Dây 3: Kiểm thử Sandbox & Cổng Master Phê Chuẩn
- Dây 4: Vòng lặp Re-plan có trần cứng từ Critic T5
- Hạn mức tự cứu In-Mission Autonomous Recovery (tối đa 3 lần/mission)
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, List, Optional

from core.recovery.error_classifier import ErrorClassifier, ErrorSubclass
from core.utils.failure_memory import failure_memory, FailureStage
from core.evolution.auto_patcher import auto_patcher, CandidatePatch

logger = logging.getLogger("JKAI.SelfHealWiring")


class AutonomousRecoveryTracker:
    """
    Theo dõi và áp đặt trần ngân sách tự cứu trong một nhiệm vụ (In-Mission Recovery Budget).
    Quy tắc an ninh: Tối đa 3 lần tự cứu/mission cho lỗi Tier 1.
    Lần thứ 4 trở đi bắt buộc dừng và chuyển cờ gọi Master / fail-closed.
    """
    MAX_RECOVERY_BUDGET: int = 3

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.attempts: List[Dict[str, Any]] = []

    def can_attempt_recovery(self) -> bool:
        return len(self.attempts) < self.MAX_RECOVERY_BUDGET

    def record_recovery_attempt(self, strategy: str, details: Optional[Dict[str, Any]] = None) -> int:
        attempt_record = {
            "attempt_index": len(self.attempts) + 1,
            "strategy": strategy,
            "details": details or {},
        }
        self.attempts.append(attempt_record)
        return len(self.attempts)

    def evaluate_next_action(self) -> Dict[str, Any]:
        if self.can_attempt_recovery():
            return {
                "action": "ALLOW_AUTONOMOUS_RECOVERY",
                "remaining_budget": self.MAX_RECOVERY_BUDGET - len(self.attempts),
                "current_attempts": len(self.attempts),
            }
        return {
            "action": "ESCALATE_TO_MASTER",
            "reason": "BUDGET_EXCEEDED_MAX_3",
            "current_attempts": len(self.attempts),
            "max_allowed": self.MAX_RECOVERY_BUDGET,
        }


def evaluate_critic_replan_decision(
    critic_verdict: Dict[str, Any],
    current_replan_count: int = 0,
    max_replan: int = 2,
) -> Dict[str, Any]:
    """
    [Dây 4]: Đánh giá quyết định Re-plan từ Ban Kiểm Soát Critic T5.
    Nếu Critic yêu cầu needs_replan=True và chưa vượt trần (max_replan=2):
    Tổng hợp recommendation thành prompt bổ sung để Planner phân rã sub-queries.
    """
    needs_replan = bool(critic_verdict.get("needs_replan", False))
    is_approved = bool(critic_verdict.get("approved", True))

    if not needs_replan and is_approved:
        return {
            "should_replan": False,
            "reason": "APPROVED_BY_CRITIC",
            "next_replan_count": current_replan_count,
        }

    if current_replan_count >= max_replan:
        return {
            "should_replan": False,
            "reason": "EXCEEDED_MAX_REPLAN",
            "current_replan_count": current_replan_count,
            "max_allowed": max_replan,
        }

    recs = critic_verdict.get("recommendations", [])
    if isinstance(recs, list):
        rec_str = "; ".join(str(r) for r in recs)
    else:
        rec_str = str(recs or "")

    replan_prompt = (
        f"[CRITIC REPLAN INSTRUCTION]: Kế hoạch trước đó chưa đạt chuẩn phê duyệt. "
        f"Lý do: {critic_verdict.get('verdict', 'PARTIAL')}. "
        f"Yêu cầu bổ sung: {rec_str}. "
        f"Hãy phân rã mục tiêu thành các sub-queries cụ thể để thu thập đủ bằng chứng."
    )

    return {
        "should_replan": True,
        "next_replan_count": current_replan_count + 1,
        "replan_prompt": replan_prompt,
        "issues": critic_verdict.get("issues", []),
    }


def execute_self_heal_diagnostic_cycle(
    error_msg: str,
    traceback_str: str,
    suggested_code: str,
    original_code: str,
    task_id: str = "self_heal_task",
) -> Dict[str, Any]:
    """
    [Dây 1 + Dây 2 + Dây 3]: Chu trình tự chẩn đoán, gán nhãn và sinh bản vá ứng viên.
    """
    classifier = ErrorClassifier()
    classification = classifier.classify(error_msg, traceback_str)

    # Dây 1: Ghi nhận lỗi có ngữ nghĩa vào FailureMemory
    diag_report = auto_patcher.diagnose_traceback(traceback_str)
    try:
        import asyncio
        coro = failure_memory.record_failure(
            task_id=task_id,
            goal=f"Execute code at {diag_report.target_file or 'unknown'}",
            task_type="coding",
            failure_stage=FailureStage.TOOL_EXECUTION,
            error_detail=f"{classification.subclass.value}: {error_msg}",
            failed_tools=[diag_report.target_file or "unknown_file"],
            attempted_fix=f"Fix {classification.subclass.value} in {diag_report.target_file}",
            fix_worked=False,
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)
    except Exception as e:
        logger.debug("[FAILURE-MEMORY-RECORD-NOTICE] %s", e)

    # Dây 2: Sinh CandidatePatch an toàn qua GovernedAutoPatcher
    patch = auto_patcher.create_candidate_patch(
        target_file=diag_report.target_file or "patch_target.py",
        original_code=original_code,
        patched_code=suggested_code,
    )

    return {
        "classified_subclass": classification.subclass.value,
        "recovery_group": classification.recovery_group.value,
        "target_file": diag_report.target_file,
        "line_number": diag_report.line_number,
        "patch_generated": bool(patch is not None),
        "patch_id": patch.patch_id,
        "syntax_valid": patch.syntax_valid,
        "diff_preview": patch.diff_preview,
        "requires_master_approval": True,
    }
