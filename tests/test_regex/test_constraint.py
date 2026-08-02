"""
Tests for Constraint Engine (core/constraint/). Converted to proper pytest.
"""

import abc
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest

from pydantic import BaseModel, Field
from core.constraint import get_engine, ConstraintEngine, ConstraintResult
from core.constraint.schemas import CriticResult, HardwareTarget, PlanStep, Blueprint
from core.constraint.engines.ollama import OllamaEngine


# ── Abstract base ─────────────────────────────────────────────────────
def test_constraint_engine_abstract():
    assert abc.ABC in ConstraintEngine.__bases__
    assert hasattr(ConstraintEngine, "generate")


# ── OllamaEngine ─────────────────────────────────────────────────────
def test_ollama_engine_basics():
    e = OllamaEngine()
    assert e.name == "ollama"
    assert isinstance(e, ConstraintEngine)


# ── get_engine ────────────────────────────────────────────────────────
def test_get_engine():
    assert get_engine("ollama").name == "ollama"
    assert get_engine().name == "ollama"
    with pytest.raises(ValueError):
        get_engine("nope")


# ── CriticResult schema ──────────────────────────────────────────────
def test_critic_result_schema():
    cr1 = CriticResult(approved=True, thought="Looks good", feedback="ok")
    assert cr1.approved is True
    assert cr1.thought == "Looks good"
    assert cr1.needs_nuclear_key is False
    cr2 = CriticResult(approved=False, feedback="redo", thought="bad",
                       needs_nuclear_key=True)
    assert cr2.needs_nuclear_key is True
    assert isinstance(cr1.model_dump(), dict)


# ── PlanStep schema ──────────────────────────────────────────────────
def test_plan_step_schema():
    ps = PlanStep(
        id="s1", tool="search_web", description="Search web",
        assigned_agent="agent.md", hardware_target=HardwareTarget.ALPHA,
        expert_mindset="", verification="ok",
    )
    assert ps.id == "s1"
    assert ps.parallel is False
    assert ps.depends_on == []
    assert ps.fallback_tool is None
    assert ps.hardware_target == HardwareTarget.ALPHA
    assert ps.hardware_target.value == "ALPHA"


# ── Blueprint schema ──────────────────────────────────────────────────
def test_blueprint_schema():
    ps = PlanStep(
        id="s1", tool="search_web", description="Search web",
        assigned_agent="agent.md", hardware_target=HardwareTarget.ALPHA,
        expert_mindset="", verification="ok",
    )
    bp = Blueprint(
        steps=[ps],
        rationale="test",
        failure_speculation="none",
        complexity_score=5,
    )
    assert len(bp.steps) == 1
    assert bp.complexity_score == 5
    assert bp.ambiguous is False
    assert bp.recommended_critic is False
    assert isinstance(bp.model_dump_json(), str)


# ── ConstraintResult ─────────────────────────────────────────────────
def test_constraint_result():
    cr1 = CriticResult(approved=True, thought="Looks good", feedback="ok")
    r = ConstraintResult(data=cr1, raw='{"approved":true}', engine="test")
    assert r.data is cr1
    assert r.raw == '{"approved":true}'
    assert r.engine == "test"
    assert r.cached is False


# ── OllamaEngine.generate (no server) ─────────────────────────────────
def test_ollama_engine_without_server_raises():
    e = OllamaEngine()
    with pytest.raises(RuntimeError):
        e.generate("hi", CriticResult, timeout=3)
