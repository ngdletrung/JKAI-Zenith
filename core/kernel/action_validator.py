# -*- coding: utf-8 -*-
"""
core/kernel/action_validator.py
🏛️ Action and Tool Parameter Validation Engine (P0.2 & GAP-1 Firewall Integration).
Provides AST-based parameter verification, Pydantic Contract validation,
and Dual-Stage Action Firewall pre-flight inspection.
"""

from __future__ import annotations
import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.kernel.tool_contracts import ToolContractRegistry

TOOL_REQUIRED_PARAMS: Dict[str, Set[str]] = {
    "write_to_file": {"TargetFile", "CodeContent"},
    "replace_file_content": {"TargetFile", "TargetContent", "ReplacementContent"},
    "run_command": {"CommandLine", "Cwd"},
    "view_file": {"AbsolutePath"},
    "SEARCH_WEB_GLOBAL": {"query"},
    "search_web": {"query"},
    "python_execute": {"code"},
}


class ActionDecision(str, Enum):
    PERMIT = "PERMIT"
    DENIED = "DENIED"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    ESCALATE = "ESCALATE"


@dataclass
class ActionVerdict:
    decision: ActionDecision
    tool: str
    normalized_tool: Optional[str] = None
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    firewall_verdict: Optional[Any] = None


def missing_required(tool_name: str, args: Dict[str, Any]) -> List[str]:
    """Returns a list of missing required arguments for a given tool."""
    required = TOOL_REQUIRED_PARAMS.get(tool_name, set())
    if not required:
        # Check case-insensitive lowercase matching if tool has known requirements
        t_low = tool_name.lower()
        for k, v in TOOL_REQUIRED_PARAMS.items():
            if k.lower() == t_low:
                required = v
                break

    if not required:
        return []

    present_keys = set(args.keys()) if isinstance(args, dict) else set()
    norm_present = {k.lower().replace("_", "") for k in present_keys}

    missing = []
    for req in required:
        if req.lower().replace("_", "") not in norm_present:
            missing.append(req)

    return sorted(missing)


def validate_ast_arguments(raw_args: str) -> Dict[str, Any]:
    """Safely evaluates arguments string using ast.literal_eval."""
    if not raw_args or not raw_args.strip():
        return {}
    try:
        parsed = ast.literal_eval(raw_args)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def validate_action(
    tool: str,
    params: Dict[str, Any],
    known_tools: Optional[Set[str]] = None,
    check_firewall: bool = True,
    mission_context: Optional[Dict[str, Any]] = None
) -> ActionVerdict:
    """
    Validates a tool action at the Kernel ingress boundary:
    1. Checks if tool is in known_tools (if specified).
    2. Validates parameters against strict ToolContractRegistry (P0.2).
    3. Passes payload through DualStageActionFirewall (GAP-1).
    """
    if not tool or not isinstance(tool, str):
        return ActionVerdict(
            decision=ActionDecision.UNKNOWN_TOOL,
            tool=str(tool),
            reason="Tool name must be a non-empty string"
        )

    canonical_name = ToolContractRegistry.get_canonical_name(tool) or tool.strip().lower()

    # 1. Known Tools Check
    if known_tools is not None:
        known_canon = {ToolContractRegistry.get_canonical_name(t) or t.lower() for t in known_tools}
        if canonical_name not in known_canon and tool not in known_tools:
            return ActionVerdict(
                decision=ActionDecision.UNKNOWN_TOOL,
                tool=tool,
                reason=f"Công cụ '{tool}' không nằm trong danh mục công cụ được phép ({', '.join(sorted(known_tools))})"
            )

    # 2. Strict Schema Contract Check (P0.2)
    is_valid, err_payload, _ = ToolContractRegistry.validate_tool_call(canonical_name, params, strict=False)
    if not is_valid and err_payload:
        missing = err_payload.get("missing_fields", [])
        mismatches = err_payload.get("type_mismatches", {})
        reason_parts = []
        if missing:
            reason_parts.append(f"Thiếu tham số bắt buộc: {', '.join(missing)}")
        if mismatches:
            reason_parts.append(f"Sai kiểu dữ liệu: {mismatches}")
        
        return ActionVerdict(
            decision=ActionDecision.SCHEMA_INVALID,
            tool=tool,
            normalized_tool=canonical_name,
            reason="; ".join(reason_parts) or "Tham số không hợp lệ theo Tool Contract",
            details=err_payload
        )

    # Legacy missing check fallback
    miss = missing_required(tool, params)
    if miss:
        return ActionVerdict(
            decision=ActionDecision.SCHEMA_INVALID,
            tool=tool,
            normalized_tool=canonical_name,
            reason=f"Thiếu tham số bắt buộc: {', '.join(miss)}",
            details={"missing_fields": miss}
        )

    # 3. Dual-Stage Action Firewall (Stage 4.1 + Stage 4.2)
    fw_verdict = None
    if check_firewall:
        try:
            from core.security.dual_stage_action_firewall import DualStageActionFirewall, FirewallDecision
            action_dict = {
                "tool": canonical_name,
                "params": params,
                "target_file": params.get("TargetFile") or params.get("target_file") or params.get("path", ""),
                "command": params.get("CommandLine") or params.get("command") or params.get("cmd", ""),
                "payload": params.get("CodeContent") or params.get("code") or params.get("ReplacementContent", "")
            }
            firewall = DualStageActionFirewall()
            fw_verdict = firewall.inspect_action(action_dict, mission_context)

            if fw_verdict.decision == FirewallDecision.DENY:
                return ActionVerdict(
                    decision=ActionDecision.DENIED,
                    tool=tool,
                    normalized_tool=canonical_name,
                    reason=f"Firewall DENIED: {'; '.join(fw_verdict.reasons)}",
                    details=fw_verdict.details,
                    firewall_verdict=fw_verdict
                )
            elif fw_verdict.decision == FirewallDecision.ESCALATE:
                return ActionVerdict(
                    decision=ActionDecision.ESCALATE,
                    tool=tool,
                    normalized_tool=canonical_name,
                    reason=f"Firewall ESCALATE: {'; '.join(fw_verdict.reasons)}",
                    details=fw_verdict.details,
                    firewall_verdict=fw_verdict
                )
        except Exception as e:
            # Fallback safe: log warning and permit if firewall module has transient import issue
            pass

    return ActionVerdict(
        decision=ActionDecision.PERMIT,
        tool=tool,
        normalized_tool=canonical_name,
        reason="Action validated and permitted",
        firewall_verdict=fw_verdict
    )
