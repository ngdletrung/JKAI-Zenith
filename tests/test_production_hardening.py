"""
Regression tests for the production-hardening fixes:
1. prompt_assembler / prompt_engine.core import cleanly (no sys.path collision)
2. surgery_engine + capability_broker singleton & token privileges
3. SHELL_EXECUTOR enforces centralized terminal policy
4. No hardcoded Windows paths in key modules
"""

import os
import sys
import asyncio

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AI_BRAIN = os.path.join(_ROOT, "services", "ai-brain")
_SHELL_LOGIC = os.path.join(_ROOT, "intelligence", "skills", "CORE", "SHELL_EXECUTOR")


@pytest.fixture(scope="module")
def brain_path():
    if _AI_BRAIN not in sys.path:
        sys.path.insert(0, _AI_BRAIN)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    return _AI_BRAIN


# ── 1. Import regression: prompt_assembler must work in a fresh process ──
def test_prompt_assembler_imports_cleanly(brain_path):
    import importlib

    importlib.import_module("prompt_engine.core")
    assembler = importlib.import_module("prompt_assembler")
    assert hasattr(assembler, "ZenithPromptAssembler")
    assert assembler.ZenithPromptAssembler.classify_task("xin chào") in (
        "CHAT", "FAST_PATH",
    )


def test_master_prompt_architect_imports_via_prompt_engine(brain_path):
    from prompt_engine.core import prompt_core
    task_type, system, user = prompt_core.build(
        goal="kiểm tra lỗi server",
        task_type="CODING",
        role="PLANNER",
    )
    assert task_type == "CODING"
    assert "Planning Mode Workflow" in system
    assert "Strict Agentic Guidelines" in system


# ── 2. Capability Broker: singleton + token lifecycle ──
def test_capability_broker_singleton_and_tokens():
    from core.kernel.capability_broker import (
        capability_broker,
        CapabilityBroker,
        CapabilityType,
    )

    assert isinstance(capability_broker, CapabilityBroker)
    token = capability_broker.issue_token(
        "task-1", CapabilityType.FILESYSTEM, scope=_ROOT.replace("\\", "/")
    )
    assert token.token_id
    assert capability_broker.verify_privilege(token.token_id, CapabilityType.FILESYSTEM, os.path.join(_ROOT, "src", "x.py"))
    assert not capability_broker.verify_privilege(token.token_id, CapabilityType.EXECUTION, _ROOT)
    assert not capability_broker.verify_privilege("bogus-token", CapabilityType.FILESYSTEM, _ROOT)


def test_surgery_engine_imports_and_verifies_syntax():
    from core.kernel.surgery_engine import surgery_engine, SurgeryEngine

    ok, _ = SurgeryEngine.verify_syntax("x = 1\n", "tmp.py")
    assert ok
    bad, diag = SurgeryEngine.verify_syntax("def f(:\n", "tmp.py")
    assert not bad
    assert "SyntaxError" in diag


def test_surgery_engine_sandbox_verify():
    from core.kernel.surgery_engine import SurgeryEngine

    async def _t():
        ok, code, out, err = await SurgeryEngine._sandbox_verify("print('hi')", timeout_sec=5)
        assert ok
        ok2, _, _, _ = await SurgeryEngine._sandbox_verify("import time; time.sleep(10)", timeout_sec=2)
        assert not ok2
    asyncio.run(_t())


# ── 3. SHELL_EXECUTOR enforces centralized terminal policy ──
def _import_shell_executor():
    if _SHELL_LOGIC not in sys.path:
        sys.path.insert(0, _SHELL_LOGIC)
    import importlib

    return importlib.import_module("logic")


def test_shell_executor_allows_policy_permitted_command():
    mod = _import_shell_executor()
    ex = mod.ShellExecutor()

    async def _t():
        r = await ex.execute_command("git status")
        assert r["status"] == "success"
    asyncio.run(_t())


def test_shell_executor_blocks_policy_blocked_command():
    mod = _import_shell_executor()
    ex = mod.ShellExecutor()

    async def _t():
        r = await ex.execute_command("shutdown -h now")
        assert r["status"] == "error"
        assert "Security Violation" in r.get("msg", "")
    asyncio.run(_t())


def test_shell_executor_blocks_chmod_777():
    mod = _import_shell_executor()
    ex = mod.ShellExecutor()

    async def _t():
        r = await ex.execute_command("chmod 777 /etc/passwd")
        assert r["status"] == "error"
    asyncio.run(_t())


def test_shell_executor_hard_failsafe_still_active():
    mod = _import_shell_executor()
    ex = mod.ShellExecutor()

    async def _t():
        r = await ex.execute_command("rm -rf /")
        assert r["status"] == "error"
    asyncio.run(_t())


# ── 4. No hardcoded D:\Docker\JKAI paths in key modules ──
def test_no_hardcoded_workspace_path_in_event_store():
    import core.utils.event_store as es

    with open(es.__file__, encoding="utf-8") as f:
        src = f.read()
    assert 'base_dir = "d:/Docker/JKAI/core/data"' not in src


def test_homunculus_vault_dir_is_repo_relative():
    import core.homunculus.manager as hm

    with open(hm.__file__, encoding="utf-8") as f:
        src = f.read()
    assert 'VAULT_DIR = Path("d:/Docker/JKAI/intelligence/vault")' not in src
    assert "os.getenv(" in src


def test_planner_complexity_is_diacritic_agnostic():
    from planner import Planner

    p = Planner()
    simple = p._estimate_complexity("Viết email chào mừng")
    complex_norm = p._estimate_complexity("phan tich va tich hop he thong pipeline cho du lieu lon")
    assert simple["level"] == "simple"
    assert complex_norm["level"] in ("complex", "extreme")
    assert complex_norm["budget"] > simple["budget"]
