# -*- coding: utf-8 -*-
"""
services/ai_executor_service.py
In-process bridge and service functions for AI Executor endpoints with grant verification.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.kernel.policy_snapshot import verify_execution_grant

logger = logging.getLogger("ai_executor_service")


async def run_steps_internal(steps: List[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
    """Fallback runner for internal steps execution."""
    return {"status": "success", "task_id": task_id, "executed_steps": len(steps)}


async def execute_task_with_grant_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    [JKAI-BND-002]: Hàm kiểm tra thẩm quyền ExecutionGrant trước khi thực thi batch steps.
    Trả về: {"status": "success", ...} nếu grant hợp lệ, hoặc {"status": "error", "denied": True} nếu không hợp lệ.
    """
    task_id = payload.get("task_id", "unknown")
    steps = payload.get("steps", [])
    grant = payload.get("grant")

    try:
        is_valid, reason = verify_execution_grant(grant, expected_tool="batch_execute", actual_args={"steps": steps})
        if not is_valid:
            # Fallback kiểm tra per-step grant
            all_valid = False
            if steps and isinstance(steps, list):
                all_valid = True
                for s in steps:
                    st = s.get("tool") or s.get("name")
                    sa = s.get("args", {})
                    sg = s.get("grant")
                    ok, _ = verify_execution_grant(sg, expected_tool=st, actual_args=sa)
                    if not ok:
                        all_valid = False
                        break
            if not all_valid:
                logger.warning(f"❌ [GRANT-DENIED] Từ chối thực thi /execute (Task: {task_id}): {reason}")
                return {
                    "status": "error",
                    "msg": f"FAIL-CLOSED: Execution rejected by Executor Boundary. {reason}",
                    "denied": True,
                }
    except Exception as g_err:
        logger.error(f"❌ [GRANT-VERIFY-ERROR] Lỗi kiểm tra grant /execute: {g_err}")
        return {
            "status": "error",
            "msg": f"FAIL-CLOSED: Grant verification error ({g_err}).",
            "denied": True,
        }

    return await run_steps_internal(steps, task_id)
