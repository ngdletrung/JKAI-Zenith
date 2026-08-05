"""
JKAI ZENITH AI OS — SCOPE VALIDATOR
File: core/guardrails/scope_validator.py

Validates file system and resource targets against authorized scope boundaries.
Prevents directory traversal and unauthorized path access.
"""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScopeValidationResult:
    allowed: bool
    target_path: str
    reason: str


class ScopeValidator:
    """Validates target file paths against workspace root and allowed scopes."""
    
    DEFAULT_WORKSPACE = Path("D:/Docker/JKAI").resolve()

    @classmethod
    def validate_file_path(
        cls, 
        target_path: str, 
        workspace_root: Optional[str] = None,
        allowed_paths: Optional[List[str]] = None,
        forbidden_paths: Optional[List[str]] = None
    ) -> ScopeValidationResult:
        root = Path(workspace_root).resolve() if workspace_root else cls.DEFAULT_WORKSPACE
        try:
            target = Path(target_path).resolve()
        except Exception as e:
            return ScopeValidationResult(allowed=False, target_path=target_path, reason=f"Invalid path format: {e}")

        # Check explicit forbidden patterns (.git, system root, sensitive dirs)
        forbidden = forbidden_paths or [".git/config", ".env", "C:/Windows", "/etc/shadow"]
        for f_pat in forbidden:
            if f_pat.lower() in str(target).lower():
                return ScopeValidationResult(
                    allowed=False, 
                    target_path=str(target), 
                    reason=f"Target path matches forbidden scope pattern: '{f_pat}'"
                )

        # Ensure path resides within workspace root unless explicitly allowed
        try:
            target.relative_to(root)
        except ValueError:
            # Path is outside workspace root
            if allowed_paths:
                is_explicitly_allowed = any(
                    str(target).lower().startswith(str(Path(a).resolve()).lower()) for a in allowed_paths
                )
                if not is_explicitly_allowed:
                    return ScopeValidationResult(
                        allowed=False, 
                        target_path=str(target), 
                        reason=f"Target path '{target}' is outside workspace root '{root}' and not explicitly allowed."
                    )
            else:
                return ScopeValidationResult(
                    allowed=False, 
                    target_path=str(target), 
                    reason=f"Target path '{target}' is outside workspace root '{root}'."
                )

        return ScopeValidationResult(
            allowed=True,
            target_path=str(target),
            reason="Path is within authorized workspace scope."
        )
