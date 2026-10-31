# -*- coding: utf-8 -*-
"""
tests/test_terminal_approval_and_patch.py
Unit tests verifying the TerminAI-inspired Approval Ladder + JSONL Audit Ledger
and the aider-inspired Multi-Format Smart Patch Engine.
Part of JKAI Zenith SDS v28.24.0.
"""

import json
import tempfile
from pathlib import Path
import pytest

from core.security.terminal_approval_ladder import (
    TerminalApprovalLadder,
    TerminalLadderTier,
    TerminalAuditLedger,
)
from core.utils.smart_patch_engine import SmartPatchEngine, PatchResult


# ═══════════════════════════════════════════════════════════════════
# 💻 TERMINAL APPROVAL LADDER TESTS (TerminAI Pattern)
# ═══════════════════════════════════════════════════════════════════

def test_ladder_tier0_read_only():
    """Kiểm tra Tầng 0 (READ_ONLY): Các lệnh tra cứu an toàn được tự động duyệt 0ms."""
    read_cmds = [
        "git status",
        "git log -n 5",
        "git diff core/kernel/agent_lifecycle.py",
        "ls -la",
        "dir /b",
        "cat README.md",
        "pwd",
        "grep -rn 'class ' .",
    ]
    for cmd in read_cmds:
        verdict = TerminalApprovalLadder.evaluate(cmd)
        assert verdict.allowed is True, f"Lệnh `{cmd}` phải được cho phép tự động."
        assert verdict.tier == TerminalLadderTier.READ_ONLY


def test_ladder_tier1_reversible():
    """Kiểm tra Tầng 1 (REVERSIBLE): Các lệnh phát triển an toàn, có thể kiểm soát/hoàn tác."""
    rev_cmds = [
        "python -m pytest tests/test_agent_lifecycle_fsm.py",
        "pytest -v",
        "ruff check .",
        "git checkout -b test-branch",
        "mkdir temp_dir",
    ]
    for cmd in rev_cmds:
        verdict = TerminalApprovalLadder.evaluate(cmd)
        assert verdict.allowed is True, f"Lệnh `{cmd}` phải được duyệt ở tầng REVERSIBLE."
        assert verdict.tier == TerminalLadderTier.REVERSIBLE


def test_ladder_tier2_irreversible_requires_confirmation():
    """Kiểm tra Tầng 2 (IRREVERSIBLE): Cần cờ confirm=True để thực thi các lệnh nguy cơ cao."""
    danger_cmds = [
        "git reset --hard HEAD~1",
        "git clean -fd",
        "npm install lodash",
    ]
    for cmd in danger_cmds:
        # Khi không có confirm: phải bị chặn
        verdict_unconfirmed = TerminalApprovalLadder.evaluate(cmd, confirm_flag=False)
        assert verdict_unconfirmed.allowed is False
        assert verdict_unconfirmed.tier == TerminalLadderTier.IRREVERSIBLE
        assert verdict_unconfirmed.requires_confirmation is True

        # Khi có confirm: được duyệt
        verdict_confirmed = TerminalApprovalLadder.evaluate(cmd, confirm_flag=True)
        assert verdict_confirmed.allowed is True
        assert verdict_confirmed.tier == TerminalLadderTier.IRREVERSIBLE


def test_ladder_tier3_privileged_hard_block():
    """Kiểm tra Tầng 3 (PRIVILEGED): Chặn tuyệt đối các lệnh can thiệp nhân hệ thống hoặc phá hủy."""
    priv_cmds = [
        "sudo rm -rf /",
        "chmod -R 777 /etc",
        "reg add HKLM\\Software\\Test",
        "taskkill /f /im explorer.exe",
        ":(){ :|:& };:", # Fork bomb
    ]
    for cmd in priv_cmds:
        verdict = TerminalApprovalLadder.evaluate(cmd)
        assert verdict.allowed is False, f"Lệnh độc hại `{cmd}` phải bị chặn đứng."
        assert verdict.tier == TerminalLadderTier.PRIVILEGED
        assert verdict.requires_human_approval is True


def test_terminal_audit_ledger_cryptographic_chain():
    """Kiểm tra TerminalAuditLedger: Ghi sổ cái JSONL với chuỗi băm mật mã SHA-256."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger = TerminalAuditLedger(log_dir=tmp_dir)

        v1 = TerminalApprovalLadder.evaluate("git status")
        r1 = ledger.record_execution(
            task_id="task_audit_1",
            command="git status",
            verdict=v1,
            exit_code=0,
            duration_ms=12.5,
            cwd="/workspace",
            output_snippet="On branch main\nnothing to commit",
        )

        v2 = TerminalApprovalLadder.evaluate("pytest -v")
        r2 = ledger.record_execution(
            task_id="task_audit_1",
            command="pytest -v",
            verdict=v2,
            exit_code=0,
            duration_ms=45.2,
            cwd="/workspace",
            output_snippet="45 passed in 15s",
        )

        # Kiểm tra tính toàn vẹn chuỗi băm
        assert r1["entry_hash"] != ""
        assert r2["prev_hash"] == r1["entry_hash"]
        assert Path(ledger.log_path).exists()

        lines = [json.loads(l) for l in Path(ledger.log_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2
        assert lines[0]["command"] == "git status"
        assert lines[1]["command"] == "pytest -v"


# ═══════════════════════════════════════════════════════════════════
# 📁 SMART PATCH ENGINE TESTS (aider Pattern)
# ═══════════════════════════════════════════════════════════════════

def test_smart_patch_tier1_exact_match():
    """Kiểm tra SmartPatchEngine Cấp 1 (Exact Match): Thay thế chính xác từng ký tự."""
    orig = "def calculate_fee(amount):\n    return amount * 0.1\n"
    tgt = "return amount * 0.1"
    repl = "return amount * 0.15"

    res = SmartPatchEngine.apply_patch(orig, tgt, repl)
    assert res.success is True
    assert res.tier_used == 1
    assert "return amount * 0.15" in res.content


def test_smart_patch_tier2_whitespace_normalized():
    """Kiểm tra SmartPatchEngine Cấp 2: Tự động điều chỉnh khi lệch thụt lề (2 spaces vs 4 spaces)."""
    orig = (
        "class OrderService:\n"
        "    def process_order(self, order_id):\n"
        "        # Validate order\n"
        "        if not order_id:\n"
        "            raise ValueError('Invalid order id')\n"
        "        return True\n"
    )

    # Target được sinh bởi model nhỏ 3B với thụt lề 2 spaces thay vì 8/12 spaces
    tgt_bad_indent = (
        "if not order_id:\n"
        "  raise ValueError('Invalid order id')"
    )
    repl_content = (
        "if not order_id:\n"
        "  logger.warning('Missing id')\n"
        "  raise ValueError('Order id is required')"
    )

    res = SmartPatchEngine.apply_patch(orig, tgt_bad_indent, repl_content)
    assert res.success is True
    assert res.tier_used == 2
    # Thụt lề phải được tự động căn chỉnh chuẩn 8/12 spaces theo file gốc
    assert "        if not order_id:\n" in res.content
    assert "        logger.warning('Missing id')\n" in res.content or "            logger.warning" in res.content
    assert "Order id is required" in res.content


def test_smart_patch_tier3_unified_diff():
    """Kiểm tra SmartPatchEngine Cấp 3: Áp dụng khối Unified Diff (--- / +++ / @@)."""
    orig = (
        "def greet(name):\n"
        "    print('Hello ' + name)\n"
        "    return True\n"
    )

    diff = (
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -2,2 +2,2 @@\n"
        "-    print('Hello ' + name)\n"
        "+    print(f'Hello, {name}!')\n"
    )

    res = SmartPatchEngine.apply_patch(orig, diff, diff)
    assert res.success is True
    assert "Hello, {name}!" in res.content
    assert "Hello ' + name" not in res.content


def test_smart_patch_non_matching_graceful_failure():
    """Kiểm tra SmartPatchEngine khi đoạn mã mục tiêu hoàn toàn không tồn tại."""
    orig = "def sample():\n    return 1\n"
    tgt = "def non_existent_function():\n    pass"
    repl = "def replaced():\n    pass"

    res = SmartPatchEngine.apply_patch(orig, tgt, repl)
    assert res.success is False
    assert "Không tìm thấy" in res.message
    assert res.content == orig
