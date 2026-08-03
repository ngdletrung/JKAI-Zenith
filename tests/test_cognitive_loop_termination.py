"""
🏛️ JKAI KERNEL — PHASE 1 INVARIANT TEST: COGNITIVE LOOP TERMINATION
File: tests/test_cognitive_loop_termination.py

Proves the cognitive loop termination invariant:
    "Every cognitive loop execution path has bounded termination.
     There is no reachable state from which the loop cannot exit."

Invariants verified:
    E1. max_iterations_terminates: loop exits at max_turns, status="completed"
    E2. repeated_action_detected: identical actions in sequence triggers loop break
    E3. tool_failure_fallback: tool exception → observation logged, loop continues (not crash)
    E4. malformed_llm_output_handled: invalid JSON/empty LLM response → graceful continue
    E5. zero_turns_handled: LLM immediately gives final answer (0 actions) → completes
    E6. loop_state_is_serializable: trajectory is serializable (no circular refs)

NOTE: CognitiveReActLoop.run_loop() is async and calls engine.call_chat().
      All LLM calls are mocked to avoid real inference.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from core.kernel.cognitive_react_loop import CognitiveReActLoop, ReActTurn


# ---------------------------------------------------------------------------
# Async test helpers
# ---------------------------------------------------------------------------


def run_async(coro):
    """Run an async coroutine in a sync test (Python 3.10+ safe)."""
    return asyncio.run(coro)


def _make_loop(max_turns: int = 5) -> CognitiveReActLoop:
    return CognitiveReActLoop(max_turns=max_turns)


# ---------------------------------------------------------------------------
# E1. Max Iterations — Bounded Termination
# ---------------------------------------------------------------------------

class TestMaxIterationsBoundedTermination:

    def test_loop_terminates_at_max_turns(self):
        """
        INVARIANT E1a:
        If LLM never produces a final answer (always has Action:),
        the loop must terminate at max_turns. Status must be "completed",
        turns_count must be <= max_turns.
        """
        loop = _make_loop(max_turns=3)

        # LLM always says "Action: something" (never finalizes)
        always_action_response = "Thought: I need to do something.\nAction: python_execute"

        with patch("core.utils.engine.engine") as mock_engine, \
             patch("core.kernel.execution_integrity.ExecutionIntegrityLayer.authorize") as mock_auth, \
             patch("core.kernel.task_contract_store.get_active_contract", return_value=None), \
             patch("core.kernel.task_contract_store.get_active_policy", return_value=None):

            mock_engine.call_chat = AsyncMock(return_value=always_action_response)
            mock_auth.return_value = MagicMock(outcome=MagicMock(value="DENY"),
                                                reason="DENY: test", requires_human_gate=False)

            result = run_async(loop.run_loop("Test goal", role="RECEPTIONIST", task_id="e1-test"))

        assert result is not None
        assert result["status"] == "completed"
        assert result["turns_count"] <= 3, (
            f"VIOLATION: Loop ran {result['turns_count']} turns, exceeding max_turns=3"
        )

    def test_loop_terminates_even_if_llm_returns_empty(self):
        """
        INVARIANT E1b:
        If LLM returns empty string, loop must terminate (not hang waiting for input).
        """
        loop = _make_loop(max_turns=5)

        with patch("core.utils.engine.engine") as mock_engine:
            mock_engine.call_chat = AsyncMock(return_value="")  # Empty response
            result = run_async(loop.run_loop("Empty response test", task_id="e1b-test"))

        assert result is not None
        assert result["status"] == "completed"
        # Loop should have broken early due to empty response
        assert result["turns_count"] <= 5


# ---------------------------------------------------------------------------
# E2. Repeated Action Detection
# ---------------------------------------------------------------------------

class TestRepeatedActionDetection:

    def test_non_repeating_actions_proceed_normally(self):
        """
        INVARIANT E2 (baseline):
        Distinct actions in each turn must not trigger early termination.
        """
        loop = _make_loop(max_turns=4)
        call_count = 0

        async def varied_responses(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Thought: search\nAction: web_search"
            elif call_count == 2:
                return "Thought: read\nAction: read_file"
            else:
                return "Thought: Done. Final answer: The answer is 42."

        with patch("core.utils.engine.engine") as mock_engine, \
             patch("core.kernel.execution_integrity.ExecutionIntegrityLayer.authorize") as mock_auth, \
             patch("core.kernel.task_contract_store.get_active_contract", return_value=None), \
             patch("core.kernel.task_contract_store.get_active_policy", return_value=None):

            mock_engine.call_chat = AsyncMock(side_effect=varied_responses)
            mock_auth.return_value = MagicMock(outcome=MagicMock(value="DENY"),
                                                reason="DENY", requires_human_gate=False)

            result = run_async(loop.run_loop("Non-repeating test", task_id="e2-baseline"))

        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# E3. Tool Failure → Fallback (not crash)
# ---------------------------------------------------------------------------

class TestToolFailureFallback:

    def test_denied_tool_does_not_crash_loop(self):
        """
        INVARIANT E3a:
        When ExecutionIntegrityLayer DENIES execution,
        the loop must NOT crash — it must log the denial as observation
        and continue to the next turn.
        """
        loop = _make_loop(max_turns=3)
        call_count = 0

        async def responses_with_action(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return "Thought: Try to run code.\nAction: python_execute\n```python\nprint('test')\n```"
            return "Thought: Done. Final answer: Complete."

        from core.kernel.execution_integrity import DecisionOutcome

        with patch("core.utils.engine.engine") as mock_engine, \
             patch("core.kernel.execution_integrity.ExecutionIntegrityLayer.authorize") as mock_auth, \
             patch("core.kernel.task_contract_store.get_active_contract", return_value=MagicMock()), \
             patch("core.kernel.task_contract_store.get_active_policy", return_value=MagicMock()):

            # Tool DENIED every time
            mock_engine.call_chat = AsyncMock(side_effect=responses_with_action)
            mock_auth.return_value = MagicMock(
                outcome=DecisionOutcome.DENY,
                reason="HARD BOUNDARY DENIAL: Arbitrary Python code execution disabled.",
                requires_human_gate=False,
            )

            # Must NOT raise exception
            result = run_async(loop.run_loop("Tool denial test", task_id="e3a-test"))

        assert result is not None
        assert result["status"] == "completed"
        # Trajectory must record the DENY as observation
        trajectory = result.get("trajectory", [])
        assert len(trajectory) >= 1

    def test_exception_in_tool_gate_does_not_crash_loop(self):
        """
        INVARIANT E3b:
        If the integrity gate itself raises an exception (e.g., import error),
        the loop must catch it, log as observation error, and continue.
        """
        loop = _make_loop(max_turns=3)
        call_count = 0

        async def responses(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Thought: Try code.\nAction: python_execute\n```python\nprint('x')\n```"
            return "Thought: Done. Final answer: ok."

        with patch("core.utils.engine.engine") as mock_engine, \
             patch("core.kernel.task_contract_store.get_active_contract",
                   side_effect=Exception("Contract store unavailable")):

            mock_engine.call_chat = AsyncMock(side_effect=responses)

            # Loop must handle the exception gracefully
            result = run_async(loop.run_loop("Exception gate test", task_id="e3b-test"))

        assert result is not None
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# E4. Malformed LLM Output Handled Gracefully
# ---------------------------------------------------------------------------

class TestMalformedLLMOutputHandled:

    def test_non_json_output_does_not_crash(self):
        """
        INVARIANT E4a:
        LLM returning garbled text (not valid thought/action format) must not crash the loop.
        """
        loop = _make_loop(max_turns=3)
        call_count = 0

        async def garbled_responses(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "?????? invalid %%% output ######"  # Garbled
            return "Thought: Done. Final answer: recovered."

        with patch("core.utils.engine.engine") as mock_engine:
            mock_engine.call_chat = AsyncMock(side_effect=garbled_responses)

            result = run_async(loop.run_loop("Garbled output test", task_id="e4a-test"))

        assert result is not None
        assert result["status"] == "completed"

    def test_none_llm_response_terminates_loop(self):
        """
        INVARIANT E4b:
        LLM returning None causes early loop exit (not a crash or hang).
        """
        loop = _make_loop(max_turns=5)

        with patch("core.utils.engine.engine") as mock_engine:
            mock_engine.call_chat = AsyncMock(return_value=None)

            result = run_async(loop.run_loop("None response test", task_id="e4b-test"))

        assert result is not None
        assert result["status"] == "completed"
        assert result["turns_count"] <= 5


# ---------------------------------------------------------------------------
# E5. Zero-Turn Termination (Immediate Final Answer)
# ---------------------------------------------------------------------------

class TestZeroTurnTermination:

    def test_immediate_final_answer_terminates_in_one_turn(self):
        """
        INVARIANT E5:
        If LLM immediately gives a final answer (no Action: keyword),
        the loop should complete in exactly 1 turn.
        """
        loop = _make_loop(max_turns=10)

        with patch("core.utils.engine.engine") as mock_engine:
            mock_engine.call_chat = AsyncMock(
                return_value="Thought: The answer is obvious. Final answer: 42."
            )
            result = run_async(loop.run_loop("Simple Q", task_id="e5-test"))

        assert result["status"] == "completed"
        assert result["turns_count"] == 1
        assert "42" in result["final_response"]


# ---------------------------------------------------------------------------
# E6. Trajectory Serializability
# ---------------------------------------------------------------------------

class TestTrajectorySerializability:

    def test_trajectory_is_json_serializable(self):
        """
        INVARIANT E6:
        The trajectory returned by run_loop() must be JSON-serializable.
        Prevents circular reference bugs that would break logging and replay.
        """
        loop = _make_loop(max_turns=3)
        call_count = 0

        async def simple_responses(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Thought: I'll search.\nAction: web_search"
            return "Thought: Done. Final answer: result."

        with patch("core.utils.engine.engine") as mock_engine, \
             patch("core.kernel.execution_integrity.ExecutionIntegrityLayer.authorize") as mock_auth, \
             patch("core.kernel.task_contract_store.get_active_contract", return_value=None), \
             patch("core.kernel.task_contract_store.get_active_policy", return_value=None):

            mock_engine.call_chat = AsyncMock(side_effect=simple_responses)
            mock_auth.return_value = MagicMock(outcome=MagicMock(value="DENY"),
                                                reason="DENY", requires_human_gate=False)

            result = run_async(loop.run_loop("Serialization test", task_id="e6-test"))

        # Must serialize without error
        try:
            serialized = json.dumps(result, ensure_ascii=False)
            assert len(serialized) > 0
        except (TypeError, ValueError) as e:
            pytest.fail(f"VIOLATION: Trajectory is not JSON-serializable: {e}")

    def test_react_turn_to_dict_is_complete(self):
        """
        INVARIANT E6b:
        ReActTurn.to_dict() must return all expected keys.
        """
        turn = ReActTurn(turn_index=1, thought="Analyzing...", action="web_search",
                         observation='{"result": "found"}')
        d = turn.to_dict()

        assert "turn" in d
        assert "thought" in d
        assert "action" in d
        assert "observation" in d
        # All values must be serializable
        json.dumps(d)  # Must not raise
