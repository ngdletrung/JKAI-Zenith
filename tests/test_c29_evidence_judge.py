# -*- coding: utf-8 -*-
"""
C29 — Judicial review must judge evidence, not fabricate a pass.

GET/POST /review_execution claimed in its docstring to "verify real evidence and
fail closed". It actually returned PASS with accuracy_score 0.95 for any payload
without a "status": "error" entry — a fabricated verdict on the endpoint that
gates mission completion.

The previous guard (tests/test_p1_wire_or_delete.py::test_p1_3) never called the
endpoint or its logic: it asserted on locally recomputed booleans, so it could
not fail even while the endpoint lied.

Contract:
1. No results / no dict results -> FAIL, score 0.
2. Error or needs_auth -> FAIL, score 0.
3. Success without concrete output -> not evidence.
4. Score is the proven/total ratio, never a constant.
5. The endpoint delegates to this judge and no longer hard-codes 0.95.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "services" / "ai-brain" / "security" / "evidence_judge.py"
MAIN = ROOT / "services" / "ai-brain" / "main.py"


def judge():
    spec = importlib.util.spec_from_file_location("c29_evidence_judge", JUDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.judge_execution_evidence


def test_no_evidence_fails_closed():
    judge_execution_evidence = judge()
    for payload in (None, [], {}, "", [None, 5, "text"], {"goal": "test goal"}):
        verdict = judge_execution_evidence(payload)
        assert verdict["verdict"] == "FAIL", f"{payload!r} must not pass"
        assert verdict["passed"] is False
        assert verdict["accuracy_score"] == 0.0


def test_error_and_needs_auth_fail_closed():
    judge_execution_evidence = judge()
    for item in (
        {"status": "error", "output": "crash"},
        {"status": "needs_auth", "output": "waiting for user"},
    ):
        verdict = judge_execution_evidence([item])
        assert verdict["verdict"] == "FAIL"
        assert verdict["accuracy_score"] == 0.0


def test_success_status_alone_is_not_evidence():
    judge_execution_evidence = judge()
    assert judge_execution_evidence([{"status": "success"}])["verdict"] == "FAIL"
    assert judge_execution_evidence([{"status": "success", "output": ""}])["verdict"] == "FAIL"
    assert judge_execution_evidence([{"step": "S1", "description": "no status"}])["verdict"] == "FAIL"


def test_score_is_the_proven_ratio_not_a_constant():
    judge_execution_evidence = judge()
    all_proven = judge_execution_evidence([
        {"status": "success", "output": "file written"},
        {"status": "completed", "answer": "42"},
    ])
    assert all_proven["verdict"] == "PASS"
    assert all_proven["accuracy_score"] == 1.0

    partial = judge_execution_evidence([
        {"status": "success", "output": "file written"},
        {"status": "skipped", "output": "No tool specified"},
    ])
    assert partial["verdict"] == "FAIL"
    assert partial["accuracy_score"] == 0.5


def test_endpoint_delegates_and_no_longer_fabricates():
    source = MAIN.read_text(encoding="utf-8")
    assert "judge_execution_evidence(data.get(\"results\"" in source
    assert '"accuracy_score": 0.95' not in source, "the fabricated constant must be gone"
    assert '"Judicial verification confirmed valid execution evidence."' not in source
