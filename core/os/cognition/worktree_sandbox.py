"""
JKAI ZENITH AI OS — WORKTREE SANDBOX & MUTATION ISOLATION (PHASE 8)
File: core/os/cognition/worktree_sandbox.py

Implements:
- Worktree Sandbox Isolation (D5, D15)
- Path Authorization Gate (Mutations outside worktree directory are strictly rejected)
"""

from __future__ import annotations
import logging
import os
import pathlib
from typing import Dict, Optional, Tuple

from core.os.cognition.event_model import emit_contract_violation

logger = logging.getLogger("jkai.cognition.worktree_sandbox")


class WorktreeSandboxManager:
    """Enforces that all file modifications are confined strictly within the isolated Git Worktree."""

    def __init__(self, base_worktree_dir: str = "d:/Docker/JKAI/.zenith/worktrees"):
        self.base_worktree_dir = pathlib.Path(base_worktree_dir)

    def get_sandbox_path(self, task_id: str) -> pathlib.Path:
        return self.base_worktree_dir / f"wt_DEEP_{task_id}"

    def authorize_mutation_path(self, target_file_path: str, task_id: str, mission_id: str, trace_id: str) -> bool:
        """
        D15: Verifies target path is inside the authorized worktree sandbox.
        Any path attempting to modify the root workspace directly is DENIED.
        """
        sandbox = self.get_sandbox_path(task_id).resolve()
        target = pathlib.Path(target_file_path).resolve()

        # In testing/virtual environment, check if path belongs to sandbox prefix
        try:
            target.relative_to(sandbox)
            return True
        except ValueError:
            logger.warning("[D15-MUTATION-BREACH] Attempted mutation on %s outside sandbox %s", target, sandbox)
            emit_contract_violation(
                contract_id="D15",
                mission_id=mission_id,
                trace_id=trace_id,
                expected=f"Path relative to {sandbox}",
                actual=str(target),
                recovery_policy="ABORT",
                enforcement_point="WorktreeSandboxManager.authorize_mutation_path"
            )
            return False


# Global Sandbox Manager
worktree_sandbox = WorktreeSandboxManager()
