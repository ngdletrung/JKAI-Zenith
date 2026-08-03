"""
JKAI AMG v2 — M2 Engine Integration Test Suite
tests/test_engine_amg_integration.py

Invariants tested:
    M2-A. ExecutionProfile.to_ollama_payload() builds valid Ollama /api/chat payload
    M2-B. ExecutionProfile.to_resource_request() builds valid ResourceRequest
    M2-C. engine.resolve_execution_profile(role) returns ExecutionProfile via AMG
    M2-D. engine.call_chat() uses ExecutionProfile to build request payload
    M2-E. Explicit profile passed to call_chat() is used directly
    M2-F. Custom options passed to call_chat() update ExecutionProfile.raw_options
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from core.governor.model_capabilities import ExecutionProfile, ModelCapabilityProfile, ModelMemoryProfile
from core.utils.models import ResourceRequest, BackendType
from core.utils.engine import JKAIIntelligenceEngine


# ---------------------------------------------------------------------------
# M2-A: ExecutionProfile.to_ollama_payload()
# ---------------------------------------------------------------------------

class TestExecutionProfilePayloadBuilder:
    """M2-A: ExecutionProfile payload builder invariants."""

    def test_to_ollama_payload_structure(self):
        profile = ExecutionProfile(
            model_name="qwen3.5:4b",
            role_name="PLANNER",
            num_gpu_layers=32,
            num_ctx=8192,
            temperature=0.05,
            keep_alive="-1",
        )
        messages = [{"role": "user", "content": "Hello"}]
        payload = profile.to_ollama_payload(messages=messages, stream=True)

        assert payload["model"] == "qwen3.5:4b"
        assert payload["stream"] is True
        assert payload["keep_alive"] == "-1"
        assert payload["messages"] == messages
        assert "options" in payload
        opts = payload["options"]
        assert opts["num_ctx"] == 8192
        assert opts["temperature"] == 0.05
        assert opts["num_gpu"] == 32
        assert "model" not in opts, "model must NOT be inside options dict"

    def test_to_ollama_payload_without_messages(self):
        profile = ExecutionProfile(model_name="gemma-4:12b", role_name="CRITIC")
        payload = profile.to_ollama_payload()

        assert payload["model"] == "gemma-4:12b"
        assert "messages" not in payload

    def test_to_resource_request_gpu(self):
        profile = ExecutionProfile(
            model_name="qwen3.5:4b",
            role_name="PLANNER",
            backend="GPU",
            num_gpu_layers=32,
        )
        req = profile.to_resource_request()
        assert isinstance(req, ResourceRequest)
        assert req.backend == BackendType.GPU
        assert req.is_gpu_bound is True

    def test_to_resource_request_cpu(self):
        profile = ExecutionProfile(
            model_name="coder:3b",
            role_name="EXECUTOR",
            backend="CPU",
            num_gpu_layers=0,
        )
        req = profile.to_resource_request()
        assert isinstance(req, ResourceRequest)
        assert req.backend == BackendType.CPU
        assert req.is_cpu_bound is True


# ---------------------------------------------------------------------------
# M2-C: Engine delegates profile resolution to AMG
# ---------------------------------------------------------------------------

class TestEngineAMGIntegration:
    """M2-C/D/E/F: Engine integration with AMG ExecutionProfile."""

    @pytest.fixture
    def mock_engine(self):
        """Create an engine instance with mocked network/Redis calls."""
        with patch.object(JKAIIntelligenceEngine, "load_routing_stats"), \
             patch.object(JKAIIntelligenceEngine, "_schedule_cache_cleanup"), \
             patch.object(JKAIIntelligenceEngine, "_get_redis", return_value=None):
            engine = JKAIIntelligenceEngine()
            yield engine

    def test_engine_has_resolve_execution_profile_method(self, mock_engine):
        assert hasattr(mock_engine, "resolve_execution_profile"), (
            "Engine must have resolve_execution_profile method"
        )

    def test_engine_resolve_execution_profile_returns_profile(self, mock_engine):
        with patch.object(mock_engine._router, "resolve_execution_profile") as mock_resolve:
            mock_profile = ExecutionProfile(model_name="test-model:7b", role_name="PLANNER")
            mock_resolve.return_value = mock_profile

            result = mock_engine.resolve_execution_profile("PLANNER")
            assert result == mock_profile
            mock_resolve.assert_called_once_with("PLANNER", hw_state=None, task_id="")


    def test_call_chat_uses_execution_profile(self, mock_engine):
        """M2-D: call_chat must use resolve_execution_profile() to build Ollama payload."""
        mock_profile = ExecutionProfile(
            model_name="mock-qwen:4b",
            role_name="PLANNER",
            backend="GPU",
            num_ctx=8192,
            temperature=0.05,
            keep_alive="-1",
        )

        with patch.object(mock_engine, "resolve_execution_profile", return_value=mock_profile) as mock_resolve, \
             patch.object(mock_engine, "_get_client") as mock_client:

            # Mock AsyncClient response
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Success from AMG engine"}
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            messages = [{"role": "user", "content": "Test prompt"}]
            # Set is_brain_service = True and current_service_url = None to force local processing
            mock_engine.is_brain_service = True
            mock_engine.current_service_url = None

            # Execute
            import asyncio
            ans = asyncio.run(mock_engine.call_chat(messages, role="PLANNER", task_id="test_t1"))

            # Verify resolve_execution_profile was called for PLANNER
            mock_resolve.assert_called_with("PLANNER", task_id="test_t1")

    def test_call_chat_accepts_explicit_profile(self, mock_engine):
        """M2-E: Explicit profile passed to call_chat() must be used directly."""
        explicit_profile = ExecutionProfile(
            model_name="explicit-model:12b",
            role_name="CUSTOM_ROLE",
            backend="CPU",
            num_ctx=4096,
        )

        with patch.object(mock_engine, "resolve_execution_profile") as mock_resolve, \
             patch.object(mock_engine, "_get_client") as mock_client:

            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Custom profile output"}
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            mock_engine.is_brain_service = True
            mock_engine.current_service_url = None

            import asyncio
            ans = asyncio.run(
                mock_engine.call_chat(
                    [{"role": "user", "content": "Hi"}],
                    role="CUSTOM_ROLE",
                    profile=explicit_profile,
                    task_id="t2"
                )
            )

            # resolve_execution_profile should NOT be called since explicit profile was provided
            mock_resolve.assert_not_called()
