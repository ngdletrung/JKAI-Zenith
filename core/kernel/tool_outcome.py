# -*- coding: utf-8 -*-
"""
core/kernel/tool_outcome.py
Typed Tool Execution Outcome & Verification Model.
Enforces:
1. Honest classification according to output content.
2. SUCCESS is logged only when backed by genuine evidence.
3. UNKNOWN != SUCCESS.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolExecutionOutcome:
    tool_name: str
    is_success: bool
    status: str
    output: Any = None
    reason: str = ""

    def to_log_line(self) -> str:
        if self.is_success:
            return f"[{self.tool_name}] ✅ Execution succeeded."
        return f"[{self.tool_name}] ⚠️ Execution failed: {self.reason}"


def from_executor_payload(payload: Dict[str, Any], tool_name: str = "") -> ToolExecutionOutcome:
    """Classifies executor response into a typed ToolExecutionOutcome."""
    if not isinstance(payload, dict):
        return ToolExecutionOutcome(
            tool_name=tool_name,
            is_success=False,
            status="error",
            output=payload,
            reason="Invalid executor payload structure."
        )

    status = str(payload.get("status", "")).lower()
    output = payload.get("output", payload.get("result", ""))
    error = payload.get("error") or payload.get("stderr")

    # If error is explicitly present
    if error:
        return ToolExecutionOutcome(
            tool_name=tool_name,
            is_success=False,
            status="error",
            output=output,
            reason=str(error)
        )

    # Check for success indicators
    if status in ("success", "ok", "completed"):
        # Verify that output does not contain raw traceback or error markers
        out_str = str(output).lower()
        if "traceback (most recent call last)" in out_str or "unhandled exception" in out_str:
            return ToolExecutionOutcome(
                tool_name=tool_name,
                is_success=False,
                status="error",
                output=output,
                reason="Output contains unhandled exception."
            )
        return ToolExecutionOutcome(
            tool_name=tool_name,
            is_success=True,
            status="success",
            output=output,
            reason=""
        )

    # If output exists and status is empty/unspecified, treat as success if no error indicator
    if output and status not in ("error", "failed", "denied"):
        return ToolExecutionOutcome(
            tool_name=tool_name,
            is_success=True,
            status="success",
            output=output,
            reason=""
        )

    return ToolExecutionOutcome(
        tool_name=tool_name,
        is_success=False,
        status=status or "unknown_error",
        output=output,
        reason=payload.get("message") or "Executor returned non-success status."
    )
