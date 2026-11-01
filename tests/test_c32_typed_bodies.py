# -*- coding: utf-8 -*-
"""
C32 — A malformed body must be rejected, not crash the worker.

Seven ai-brain routes and one ai-executor route parsed the body with
`await request.json()`. On malformed JSON that raises inside the handler, so the
caller got "500 Internal Server Error" (and the worker logged a traceback)
instead of a 4xx that names the problem. FastAPI already does this correctly
when the body is declared as `dict`, so the fix is to declare it.

Contract:
1. No route in ai-brain or ai-executor parses JSON by hand.
2. Every formerly-raw route declares a typed body.
3. Untouched routes keep their explicit `_safe_get_json` handling.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "services" / "ai-brain" / "main.py"
EXECUTOR = ROOT / "services" / "ai-executor" / "main.py"

TYPED_ROUTES = (
    "review_plan",
    "review_execution_endpoint",
    "dispatch_task",
    "summarize_task",
    "memorize_conversation",
    "distill_knowledge",
    "distill_judicial_endpoint",
    "chat_task",
    "stream_chat",
)


def test_ai_brain_has_no_manual_json_parsing():
    source = BRAIN.read_text(encoding="utf-8")
    assert "await request.json()" not in source
    for name in TYPED_ROUTES:
        assert f"async def {name}(data: dict):" in source, f"{name} must declare its body"


def test_executor_has_no_manual_json_parsing():
    source = EXECUTOR.read_text(encoding="utf-8")
    assert "await request.json()" not in source
    assert "async def openai_completions(payload: dict):" in source


def test_custom_parsers_stay_custom():
    source = BRAIN.read_text(encoding="utf-8")
    assert 'async def plan_task(request: Request):' in source
    assert 'async def receptionist_task(request: Request):' in source
    assert "data = await _safe_get_json(request)" in source
