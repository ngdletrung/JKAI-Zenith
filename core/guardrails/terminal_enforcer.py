import re
import logging
from typing import Optional

from .rules_loader import get_guardrails

logger = logging.getLogger("Guardrails.TerminalEnforcer")


def check_command(command: str) -> tuple[bool, Optional[str]]:
    """
    Check a command against terminal policy from .jkairules.json.
    Returns (allowed, reason) — if blocked, reason explains why.
    """
    guardrails = get_guardrails()
    policy = guardrails.get("terminal_policy", {})

    blocked = policy.get("blocked_commands", [])
    for pattern in blocked:
        if command.strip().startswith(pattern):
            return False, f"Command blocked by terminal policy: '{pattern}'"

    allowed = policy.get("allowed_commands", [])
    if allowed:
        for pattern in allowed:
            pat_regex = "^" + pattern.replace("*", ".*") + "$"
            if re.match(pat_regex, command.strip()):
                return True, None
        return False, f"Command not in allowed list. Permitted patterns: {allowed}"

    return True, None


def check_directory(path: str) -> tuple[bool, Optional[str]]:
    guardrails = get_guardrails()
    sandbox = guardrails.get("sandbox", {})
    allowed = sandbox.get("allowed_directories", [])
    blocked = sandbox.get("blocked_patterns", [])

    for pattern in blocked:
        pat_regex = pattern.replace("*", ".*").replace(".", "\\.")
        if re.search(pat_regex, path):
            return False, f"Path matches blocked pattern: '{pattern}'"

    if allowed:
        import os
        norm_path = os.path.normpath(path).replace("\\", "/")
        for allowed_dir in allowed:
            norm_allowed = os.path.normpath(allowed_dir).replace("\\", "/")
            if norm_path.startswith(norm_allowed):
                return True, None
            resolved = os.path.abspath(norm_allowed).replace("\\", "/")
            if norm_path.startswith(resolved):
                return True, None
        return False, f"Path outside allowed directories: {allowed}"

    return True, None
