"""
JKAI ZENITH AI OS — MUTATION GUARD
File: core/guardrails/mutation_guard.py

Classifies tool execution intents into READ_ONLY, SAFE_MUTATION, or DESTRUCTIVE_MUTATION.
Enforces mandatory Policy Gate authorization for destructive mutations.
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional


class MutationType(str, Enum):
    READ_ONLY = "READ_ONLY"
    SAFE_MUTATION = "SAFE_MUTATION"
    DESTRUCTIVE_MUTATION = "DESTRUCTIVE_MUTATION"


@dataclass
class MutationGuardResult:
    allowed: bool
    mutation_type: MutationType
    requires_policy_gate: bool
    reason: str


class MutationGuard:
    """Evaluates mutation safety for tool calls and shell commands."""
    
    DESTRUCTIVE_PATTERNS = [
        r"rm\s+-rf", r"drop\s+database", r"xóa\s+toàn\s+bộ", r"truncate\s+table",
        r"systemctl\s+stop", r"flush\s+iptables", r"format\s+disk", r"delete\s+production"
    ]

    WRITE_TOOLS = {
        "replace_file_content", "multi_replace_file_content", "write_to_file",
        "delete_file", "git_commit", "git_push", "docker_stop"
    }

    READ_TOOLS = {
        "read_file", "view_file", "list_dir", "grep_search",
        "search_web", "read_url_content", "check_status"
    }

    @classmethod
    def evaluate_mutation(cls, tool_name: str, parameters: Dict[str, Any]) -> MutationGuardResult:
        name = (tool_name or "").strip().lower()
        cmd = str(parameters.get("command") or parameters.get("CommandLine") or "")

        # Check for Destructive Patterns in parameters / command
        if any(re.search(pat, cmd, re.I) for pat in cls.DESTRUCTIVE_PATTERNS):
            return MutationGuardResult(
                allowed=False,  # Blocked unless explicit Policy Gate approval provided
                mutation_type=MutationType.DESTRUCTIVE_MUTATION,
                requires_policy_gate=True,
                reason="Destructive system command detected. Requires Policy Gate authorization."
            )

        if name in cls.WRITE_TOOLS or "write" in name or "edit" in name:
            return MutationGuardResult(
                allowed=True,
                mutation_type=MutationType.SAFE_MUTATION,
                requires_policy_gate=False,
                reason="Standard file/state write operation within isolated workspace."
            )

        return MutationGuardResult(
            allowed=True,
            mutation_type=MutationType.READ_ONLY,
            requires_policy_gate=False,
            reason="Read-only operation causing 0 side-effects."
        )
