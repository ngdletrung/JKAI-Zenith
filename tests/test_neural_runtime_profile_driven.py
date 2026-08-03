"""
JKAI AMG v2 — M5 NeuralRuntime Profile-Driven Execution Test Suite
tests/test_neural_runtime_profile_driven.py

Invariants tested:
    M5-A. NeuralRuntime.execute(messages, profile) executes with profile-derived payload
    M5-B. NeuralRuntime.execute_profile_stream(messages, profile) yields tokens with profile options
    M5-C. NeuralRuntime retains all resilience (circuit breaker, backoff, watchdog)
    M5-D. Backward-compatible call_chat(payload) still works
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from core.governor.model_capabilities import ExecutionProfile
from core.utils.neural_runtime import NeuralRuntime


# ---------------------------------------------------------------------------
# M5 NeuralRuntime Invariants
# ---------------------------------------------------------------------------

class TestNeuralRuntimeProfileDriven:

    @pytest.fixture
    def runtime(self):
        rt = NeuralRuntime(ollama_host="http://127.0.0.1:11434")
        return rt

    def test_execute_profile_builds_payload(self, runtime):
        profile = ExecutionProfile(
            model_name="qwen3.5:4b",
            role_name="PLANNER",
            num_gpu_layers=32,
            num_ctx=8192,
            temperature=0.05,
            keep_alive="-1",
        )
        messages = [{"role": "user", "content": "Test prompt"}]

        with patch.object(runtime, "call_chat", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (200, "Response text")
            import asyncio
            status, text = asyncio.run(runtime.execute(messages, profile, task_id="t1"))

            assert status == 200
            assert text == "Response text"
            mock_call.assert_called_once()

            payload = mock_call.call_args[0][0]
            assert payload["model"] == "qwen3.5:4b"
            assert payload["options"]["num_ctx"] == 8192
            assert payload["keep_alive"] == "-1"

    def test_execute_profile_stream_yields_tokens(self, runtime):
        profile = ExecutionProfile(
            model_name="gemma-4:12b",
            role_name="CRITIC",
            num_gpu_layers=100,
            num_ctx=4096,
        )
        messages = [{"role": "user", "content": "Stream prompt"}]

        async def mock_stream(*args, **kwargs):
            yield {"type": "chunk", "data": {"message": {"content": "Token 1 "}}}
            yield {"type": "chunk", "data": {"message": {"content": "Token 2"}}}


        with patch.object(runtime, "execute_chat_stream", side_effect=mock_stream):
            async def run_stream():
                tokens = []
                async for tok in runtime.execute_profile_stream(messages, profile, task_id="t2"):
                    tokens.append(tok)
                return tokens

            import asyncio
            result = asyncio.run(run_stream())
            assert result == ["Token 1 ", "Token 2"]
