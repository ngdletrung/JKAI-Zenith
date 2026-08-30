# -*- coding: utf-8 -*-
"""
core/kernel/action_validator.py
Action and Tool Parameter Validation Engine.
Provides AST-based parameter verification and required argument checks.
"""

from __future__ import annotations
import ast
from typing import Any, Dict, List, Set

TOOL_REQUIRED_PARAMS: Dict[str, Set[str]] = {
    "write_to_file": {"TargetFile", "CodeContent"},
    "replace_file_content": {"TargetFile", "TargetContent", "ReplacementContent"},
    "run_command": {"CommandLine", "Cwd"},
    "view_file": {"AbsolutePath"},
    "SEARCH_WEB_GLOBAL": {"query"},
    "search_web": {"query"},
    "python_execute": {"code"},
}


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
    # Normalize argument keys for case-insensitive matching
    norm_present = {k.lower() for k in present_keys}

    missing = []
    for req in required:
        if req.lower() not in norm_present:
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
