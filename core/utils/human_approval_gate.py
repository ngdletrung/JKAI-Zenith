# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/human_approval_gate.py
# - Role: Human Approval Interrupt & Resume Gate (Inspired by LangGraph HITL)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — Pure Python risk evaluation (< 0.2ms latency).
# 2. Risk Intercept: Detects high-risk operations (delete, formatting, drops).
# 3. Interrupt & Resume: Saves state checkpoint and pauses execution for approval.
# -----------------------------------------------------------------------------

import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("JKAI.HumanApprovalGate")

# Patterns triggering approval requirement
_HIGH_RISK_PATTERNS = [
    r"\b(rm|del|unlink|drop|format|rd /s|Remove-Item)\b",
    r"\b(git reset --hard|git clean -f)\b",
    r"\b(docker system prune|docker rm -f)\b",
]

_HIGH_RISK_FILES = [
    ".env", "rules_software.md", ".jkairules.json"
]


def eval_tool_risk(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Evaluates whether a tool call requires explicit human approval.

    Returns:
        (requires_approval: bool, reason: str)
    """
    if not tool_name:
        return False, ""

    tool_upper = tool_name.upper()
    args_str = str(args or {})

    # 1. Check high-risk command patterns
    if "RUN_COMMAND" in tool_upper or "SYSTEM_CMD" in tool_upper:
        cmd = args.get("command") or args.get("cmd") or args_str
        for pat in _HIGH_RISK_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                reason = f"High-risk command execution pattern detected: '{pat}'"
                logger.warning(f"[APPROVAL-GATE] Intercepted {tool_name}: {reason}")
                return True, reason

    # 2. Check high-risk file modification
    if any(kw in tool_upper for kw in ["WRITE", "REPLACE", "DELETE"]):
        path = str(args.get("path") or args.get("TargetFile") or args.get("target") or "")
        for f in _HIGH_RISK_FILES:
            if f.lower() in path.lower():
                reason = f"Modification of critical system file detected: '{f}'"
                logger.warning(f"[APPROVAL-GATE] Intercepted {tool_name}: {reason}")
                return True, reason

    return False, ""


def create_approval_interrupt(task_id: str, tool_name: str, args: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Create an approval interrupt state payload."""
    payload = {
        "status": "INTERRUPTED_AWAITING_APPROVAL",
        "task_id": task_id,
        "tool_name": tool_name,
        "args": args,
        "reason": reason,
        "requires_approval": True
    }
    try:
        from core.utils.state_checkpoint import save_checkpoint
        save_checkpoint(task_id, "APPROVAL_GATE", payload)
    except Exception as e:
        logger.warning(f"[APPROVAL-INTERRUPT-SAVE-ERR] {e}")
    return payload
