"""
Planner agent registry tests. Run: python core/utils/test_planner_agents.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-brain"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("INTELLIGENCE_DIR", str(ROOT / "intelligence"))


def test_list_agents_includes_new_souls():
    from planner import Planner

    agents = Planner.list_agent_soul_files()
    assert "agent_strategist.md" in agents
    assert "agent_master_graphic.md" in agents
    assert all(a.startswith("agent_") and a.endswith(".md") for a in agents)


def test_role_hints_resolve():
    from planner import Planner

    valid = set(Planner.list_agent_soul_files())
    assert Planner.soul_for_agent_role("strategic market analysis", valid) == "agent_strategist.md"
    assert Planner.soul_for_agent_role("graphic design banner", valid) == "agent_master_graphic.md"


def test_verify_rejects_ghost():
    from planner import Planner

    p = Planner()
    errs = p._verify_agent_souls({
        "steps": [{"assigned_agent": "agent_nonexistent_xyz.md", "tool": "X"}]
    })
    assert any("Ghost" in e for e in errs)


def run_all():
    tests = [
        test_list_agents_includes_new_souls,
        test_role_hints_resolve,
        test_verify_rejects_ghost,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("OK", fn.__name__)
        except Exception as e:
            failed += 1
            print("FAIL", fn.__name__, e)
    if failed:
        raise SystemExit(failed)
    print(f"All {len(tests)} passed.")


if __name__ == "__main__":
    run_all()
