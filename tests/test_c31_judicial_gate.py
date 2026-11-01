# -*- coding: utf-8 -*-
"""
C31 — The judicial verdict must be able to stop a mission.

C29 made /review_execution honest, but ai-control-plane ignored the verdict:
it logged REFLECTED and always moved to VERIFIED. A FAIL that nobody acts on
is a report, not a gate.

Stop only when there is no evidence at all (accuracy_score == 0.0). A partial
FAIL (0 < score < 1) must not stop the mission: with the strict evidence rule,
one skipped step is enough to produce FAIL 0.9, and stopping on that would turn
a reporting bug into an operational outage.

Contract:
1. classify_judicial_outcome maps verdict+score to stop/partial/pass (fail-closed on junk).
2. ai-control-plane transitions to FAILED and returns before VERIFIED on stop.
3. Every stop/partial is counted in the shared system counters.
4. GET /judicial/stats exposes those counters.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "core" / "os" / "cognition" / "judicial_gate.py"
TASK_MANAGER = ROOT / "services" / "ai-control-plane" / "task_manager.py"
BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("c31_judicial_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stop_only_when_no_evidence_at_all():
    gate = load_gate()
    assert gate.classify_judicial_outcome(None) == gate.STOP
    assert gate.classify_judicial_outcome("FAIL") == gate.STOP
    assert gate.classify_judicial_outcome({"verdict": "FAIL"}) == gate.STOP
    assert gate.classify_judicial_outcome({"verdict": "FAIL", "accuracy_score": 0.0}) == gate.STOP
    assert gate.classify_judicial_outcome({"verdict": "FAIL", "accuracy_score": "junk"}) == gate.STOP


def test_partial_failure_warns_but_does_not_stop():
    gate = load_gate()
    assert gate.classify_judicial_outcome({"verdict": "FAIL", "accuracy_score": 0.9}) == gate.PARTIAL
    assert gate.classify_judicial_outcome({"verdict": "FAIL", "accuracy_score": 0.5}) == gate.PARTIAL


def test_pass_is_not_a_stop():
    gate = load_gate()
    assert gate.classify_judicial_outcome({"verdict": "PASS", "accuracy_score": 1.0}) == gate.PASS
    assert gate.classify_judicial_outcome({"verdict": "SUCCESS"}) == gate.PASS


def test_mission_stops_before_verified():
    source = TASK_MANAGER.read_text(encoding="utf-8")
    assert "classify_judicial_outcome(jr)" in source

    stop_block = source.index("_judicial_action == STOP")
    verified_after_gate = source.index("TaskState.VERIFIED", stop_block)
    assert stop_block < verified_after_gate, "the stop check must run before the mission is marked verified"
    assert '"status": "failed"' in source[stop_block:verified_after_gate]

    assert 'system_counters.bump("judicial", _judicial_action)' in source


def test_judicial_counters_are_readable_from_ai_brain():
    source = BRAIN_MAIN.read_text(encoding="utf-8")
    assert "'/judicial/stats'" in source
    assert 'system_counters.read("judicial")' in source
