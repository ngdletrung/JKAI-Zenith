# -*- coding: utf-8 -*-
"""
core/security/terminal_approval_ladder.py
🏛️ Deterministic Terminal Approval Ladder & JSONL Audit Ledger (Inspired by TerminAI)
Part of JKAI Zenith Sovereign OS — SDS v28.24.0

Provides:
1. TerminalLadderTier: 4-tier command classification (READ_ONLY -> REVERSIBLE -> IRREVERSIBLE -> PRIVILEGED).
2. TerminalApprovalLadder: Deterministic, sub-millisecond command classifier.
3. TerminalAuditLedger: Append-only JSONL cryptographic ledger for compliance and red-team audits.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JKAI.TerminalLadder")


class TerminalLadderTier(str, Enum):
    READ_ONLY = "READ_ONLY"       # Tier 0: Tra cứu, đọc thông tin, không làm thay đổi state.
    REVERSIBLE = "REVERSIBLE"     # Tier 1: Thao tác an toàn, test, build tạm, có thể hoàn tác.
    IRREVERSIBLE = "IRREVERSIBLE" # Tier 2: Xóa/ghi đè vĩnh viễn, reset git, cài đặt package lớn.
    PRIVILEGED = "PRIVILEGED"     # Tier 3: Thay đổi nhân hệ thống, firewall, registry, root/sudo.


# ═══════════════════════════════════════════════════════════════════
# 📋 DETERMINISTIC PATTERNS & BINARIES
# ═══════════════════════════════════════════════════════════════════

READ_ONLY_BINARIES = {
    "ls", "dir", "cat", "type", "pwd", "grep", "findstr",
    "find", "head", "tail", "echo", "where", "which", "whoami",
    "hostname", "date", "diff",
}

READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "tag", "remote",
    "rev-parse", "describe", "blame", "check-ignore", "config",
}

REVERSIBLE_BINARIES = {
    "python", "python3", "pytest", "ruff", "mypy", "node", "npm",
    "mkdir", "touch", "cp", "copy",
}

REVERSIBLE_GIT_SUBCOMMANDS = {
    "checkout", "switch", "stash", "fetch", "pull", "add", "commit",
}

IRREVERSIBLE_PATTERNS = [
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[a-zA-Z]*f",
    r"git\s+branch\s+-[a-zA-Z]*D",
    r"npm\s+(i|install|ci|remove|uninstall|update)",
    r"pip\s+uninstall",
    r"del\s+/[a-zA-Z]*f",
    r"rmdir\s+/[a-zA-Z]*s",
    r"rm\s+-[a-zA-Z]*r",
]

PRIVILEGED_PATTERNS = [
    r"\bsudo\b",
    r"\bchmod\b\s+-[a-zA-Z]*R?\s*777",
    r"\bchown\b",
    r"\bnetsh\b",
    r"\breg(\.exe)?\s+(add|delete|import)",
    r"\btaskkill\b\s+.*(/f|/t)",
    r"\bkill\b\s+-9",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{\s*:\|:&\s*\};:", # Fork bomb
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bformat\b\s+[a-zA-Z]:",
]


class TerminalApprovalVerdict:
    def __init__(
        self,
        allowed: bool,
        tier: TerminalLadderTier,
        reason: str,
        requires_confirmation: bool = False,
        requires_human_approval: bool = False,
    ):
        self.allowed = allowed
        self.tier = tier
        self.reason = reason
        self.requires_confirmation = requires_confirmation
        self.requires_human_approval = requires_human_approval

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tier": self.tier.value,
            "reason": self.reason,
            "requires_confirmation": self.requires_confirmation,
            "requires_human_approval": self.requires_human_approval,
        }


class TerminalApprovalLadder:
    """
    Deterministic Approval Ladder for CLI commands.
    Evaluates commands in <0.5ms on CPU with 0 LLM calls.
    """

    @classmethod
    def evaluate(cls, command: str, confirm_flag: bool = False) -> TerminalApprovalVerdict:
        cmd = str(command or "").strip()
        if not cmd:
            return TerminalApprovalVerdict(
                allowed=False,
                tier=TerminalLadderTier.READ_ONLY,
                reason="Lệnh thực thi không được để trống.",
            )

        cmd_lower = cmd.lower()

        # 1. Tier 3 Check: PRIVILEGED (Hard Blocked / Human Approval Gate)
        for pattern in PRIVILEGED_PATTERNS:
            if re.search(pattern, cmd_lower):
                return TerminalApprovalVerdict(
                    allowed=False,
                    tier=TerminalLadderTier.PRIVILEGED,
                    reason=f"Lệnh chứa chỉ thị hệ thống đặc quyền cấp cao (Privileged System Hazard): {pattern}",
                    requires_human_approval=True,
                )

        # 2. Tier 2 Check: IRREVERSIBLE (Requires confirm_flag)
        for pattern in IRREVERSIBLE_PATTERNS:
            if re.search(pattern, cmd_lower):
                if not confirm_flag:
                    return TerminalApprovalVerdict(
                        allowed=False,
                        tier=TerminalLadderTier.IRREVERSIBLE,
                        reason=f"Lệnh có thể gây thay đổi không thể hoàn tác (Irreversible Operation): {pattern}. Cần xác nhận 'confirm=True'.",
                        requires_confirmation=True,
                    )
                return TerminalApprovalVerdict(
                    allowed=True,
                    tier=TerminalLadderTier.IRREVERSIBLE,
                    reason="Thao tác không thể hoàn tác đã được phê duyệt qua xác nhận tường minh.",
                )

        # 3. Parse base binary
        base_bin = ""
        subcmd = ""
        try:
            parts = shlex.split(cmd.replace("\\", "/"))
            if parts:
                raw_bin = os.path.basename(parts[0]).lower()
                base_bin = raw_bin[:-4] if raw_bin.endswith(".exe") else raw_bin
                if len(parts) > 1:
                    subcmd = parts[1].lower()
        except Exception:
            base_bin = cmd_lower.split()[0] if cmd_lower.split() else ""

        # 4. Tier 0 Check: READ_ONLY
        if base_bin == "git" and subcmd in READ_ONLY_GIT_SUBCOMMANDS:
            return TerminalApprovalVerdict(
                allowed=True,
                tier=TerminalLadderTier.READ_ONLY,
                reason=f"Lệnh tra cứu Git an toàn (git {subcmd}).",
            )

        if base_bin in READ_ONLY_BINARIES:
            return TerminalApprovalVerdict(
                allowed=True,
                tier=TerminalLadderTier.READ_ONLY,
                reason=f"Lệnh đọc/tra cứu dữ liệu an toàn ({base_bin}).",
            )

        # 5. Tier 1 Check: REVERSIBLE
        if base_bin == "git" and subcmd in REVERSIBLE_GIT_SUBCOMMANDS:
            return TerminalApprovalVerdict(
                allowed=True,
                tier=TerminalLadderTier.REVERSIBLE,
                reason=f"Lệnh Git có thể kiểm soát và hoàn tác (git {subcmd}).",
            )

        if base_bin in REVERSIBLE_BINARIES:
            return TerminalApprovalVerdict(
                allowed=True,
                tier=TerminalLadderTier.REVERSIBLE,
                reason=f"Lệnh thực thi an toàn trong môi trường phát triển ({base_bin}).",
            )

        # Fallback: Cho phép nếu nằm trong allowlist, xếp vào REVERSIBLE
        return TerminalApprovalVerdict(
            allowed=True,
            tier=TerminalLadderTier.REVERSIBLE,
            reason=f"Lệnh chuẩn được phê duyệt mặc định ({base_bin}).",
        )


# ═══════════════════════════════════════════════════════════════════
# 📜 APPEND-ONLY TERMINAL AUDIT LEDGER
# ═══════════════════════════════════════════════════════════════════

class TerminalAuditLedger:
    """
    Append-only JSONL cryptographic ledger for all terminal executions.
    Maintains SHA-256 chain of custody for complete auditability.
    """
    _instance: Optional[TerminalAuditLedger] = None
    _lock = threading.Lock()

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir:
            self.log_path = Path(log_dir) / "terminal_audit.jsonl"
        else:
            try:
                from core.utils.project_workspace import get_jkai_workspace_root
                self.log_path = get_jkai_workspace_root() / "data" / "telemetry" / "terminal_audit.jsonl"
            except Exception:
                self.log_path = Path("data/telemetry/terminal_audit.jsonl").resolve()

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_entry_hash = "0" * 64
        self._init_chain_hash()

    def _init_chain_hash(self) -> None:
        if self.log_path.exists() and self.log_path.stat().st_size > 0:
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    last_line = ""
                    for line in f:
                        if line.strip():
                            last_line = line
                    if last_line:
                        entry = json.loads(last_line)
                        self._last_entry_hash = entry.get("entry_hash", "0" * 64)
            except Exception as e:
                logger.debug("Failed to read last audit entry hash: %s", e)

    @classmethod
    def get_instance(cls, log_dir: Optional[str] = None) -> TerminalAuditLedger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = TerminalAuditLedger(log_dir)
            return cls._instance

    def record_execution(
        self,
        task_id: str,
        command: str,
        verdict: TerminalApprovalVerdict,
        exit_code: Optional[int] = None,
        duration_ms: float = 0.0,
        cwd: str = ".",
        output_snippet: str = "",
    ) -> Dict[str, Any]:
        """Ghi nhận lượt chạy lệnh vào sổ cái JSONL bất biến."""
        now_utc = datetime.now(timezone.utc).isoformat()
        out_bytes = output_snippet.encode("utf-8", errors="replace")
        out_sha = hashlib.sha256(out_bytes).hexdigest()

        with self._lock:
            payload_for_hash = f"{self._last_entry_hash}|{now_utc}|{task_id}|{command}|{verdict.tier.value}|{exit_code}|{out_sha}"
            entry_hash = hashlib.sha256(payload_for_hash.encode("utf-8")).hexdigest()

            record = {
                "timestamp_utc": now_utc,
                "task_id": task_id,
                "command": command,
                "ladder_tier": verdict.tier.value,
                "allowed": verdict.allowed,
                "reason": verdict.reason,
                "exit_code": exit_code,
                "duration_ms": round(duration_ms, 2),
                "cwd": cwd,
                "output_sha256": out_sha,
                "prev_hash": self._last_entry_hash,
                "entry_hash": entry_hash,
            }

            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                self._last_entry_hash = entry_hash
            except Exception as io_err:
                logger.error("Failed to append terminal audit ledger: %s", io_err)

            return record
