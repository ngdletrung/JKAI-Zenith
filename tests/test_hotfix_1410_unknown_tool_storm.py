# -*- coding: utf-8 -*-
"""Hotfix 1410: su co mission chung khoan 14/10 — unknown-tool storm breaker,
import resilience cho tools.*, loi executor minh bach, walkthrough version."""

from __future__ import annotations

import sys

TM_PATH = "services/ai-control-plane/task_manager.py"


def _load_storm_helpers():
    """Nap 2 ham thuan khiet tu task_manager ma khong bootstrap service."""
    src = open(TM_PATH, encoding="utf-8").read()
    start = src.index("# ── [HOTFIX-1410: UNKNOWN-TOOL STORM BREAKER]")
    end = src.index("@dataclass(frozen=True", start)
    ns: dict = {}
    exec(compile(src[start:end], "storm_slice", "exec"), ns)
    return ns["is_unknown_tool_failure"], ns["should_break_on_unknown_tools"]


def test_unknown_tool_patterns_cover_executor_messages():
    is_unk, _ = _load_storm_helpers()
    assert is_unk("Tool 'x' (resolved as 'y') not found in registry.")
    assert is_unk("Logic file for 'z' not found at /app/skills.")
    assert is_unk("Tool function 'a' not found in f.py.")
    assert is_unk("Plugin logic file not found: m")
    assert is_unk("Could not create spec/loader for m.")
    assert not is_unk("Tool execution timed out after 120s")
    assert not is_unk("")
    assert not is_unk(None)


def test_storm_breaker_only_breaks_on_pure_unknown_streak():
    _, should_break = _load_storm_helpers()
    # 2 chu ky toan unknown + 0 success -> break
    brk, streak = should_break(
        ["not found in registry", "Tool function 'a' not found in f"], False, 1)
    assert brk is True and streak == 2
    # Da co success -> khong break bao gio
    brk, streak = should_break(["not found in registry"], True, 5)
    assert brk is False and streak == 0
    # Loi hon hop (timeout) -> khong break, reset streak
    brk, streak = should_break(["Tool execution timed out after 120s"], False, 1)
    assert brk is False and streak == 0
    # Chu ky 1 unknown dau tien -> dem, chua break
    brk, streak = should_break(["not found in registry"], False, 0)
    assert brk is False and streak == 1
    assert should_break([], False, 0) == (False, 0)


def test_ensure_tools_importable_puts_repo_root_on_path():
    if "." not in sys.path:
        sys.path.insert(0, ".")
    from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import (
        _ensure_tools_importable,
    )
    _ensure_tools_importable()
    import tools.web_search  # noqa: F401 — phai import duoc sau helper
    assert hasattr(tools.web_search, "execute_real_web_search_sync")


def test_walkthrough_has_no_hardcoded_version():
    text = open("services/mission-control/backend/missions/default/docs/walkthrough.md",
                encoding="utf-8").read()
    assert "v28.4.0" not in text
    assert "CHANGELOG.md" in text


def test_gateway_prefers_error_detail_over_no_output():
    src = open("services/ai-brain/receptionist/executor_gateway.py",
               encoding="utf-8").read()
    assert 'data.get("msg") or data.get("message") or data.get("detail")' in src
