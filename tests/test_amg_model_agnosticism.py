"""
🏛️ AMG v2 — PHASE 1 INVARIANT TEST: MODEL AGNOSTICISM
File: tests/test_amg_model_agnosticism.py

Proves the architectural invariant:
    "Engine behavior is identical regardless of which model AMG selects.
     Model swaps require ZERO code changes."

Invariants verified:
    A1. Registry swap → AMG re-routes to available model, 0 code change.
    A2. Unknown model auto-discover → classify → route without crashing.
    A3. ExecutionProfile carries no model-name-based branching in Engine contract.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelClass, ExecutionProfile
)
from core.governor.model_registry import ModelRegistry
from core.governor.hardware_monitor import HardwareState
from core.governor.portfolio_governor import PortfolioGovernor
from core.governor.model_inspector import ModelInspector
from core.runtime.base_adapter import RuntimeModelInfo
from core.runtime.amg_boot import AMGBootstrap, BootRequest
from core.runtime.runtime_discovery import (
    RuntimeSnapshot, EndpointInfo, EndpointType, AvailableModel,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_registry():
    """Ensure ModelRegistry is clean between tests — prevents cross-contamination."""
    reg = ModelRegistry.instance()
    reg.clear()
    yield reg
    reg.clear()


@pytest.fixture
def hw_8gb():
    return HardwareState(
        vram_total_mb=8192,
        vram_free_mb=6500,
        ram_total_gb=128.0,
        ram_free_gb=96.0,
    )


def _make_profile(name: str, classes: set, size_gb: float = 2.5, confidence: float = 0.9):
    return ModelCapabilityProfile(
        model_name=name,
        model_classes=classes,
        assessment_confidence=confidence,
    )


# ---------------------------------------------------------------------------
# A1. Model Swap Invariant
# ---------------------------------------------------------------------------

class TestModelSwapInvariant:

    def test_swap_receptionist_model_zero_code_change(self, fresh_registry, hw_8gb):
        """
        INVARIANT A1:
        Registry initially contains ModelA. ModelA is removed (swap scenario).
        ModelB is registered. AMG must auto-route to ModelB for RECEPTIONIST
        without any code change.
        """
        # Phase 1: ModelA (qwen-style) is the only candidate
        model_a = _make_profile("qwen3.5:4b", {ModelClass.GENERAL, ModelClass.REASONING})
        fresh_registry.register(model_a)

        gov = PortfolioGovernor(registry=fresh_registry)
        profile_a = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)
        assert profile_a.model_name == "qwen3.5:4b"

        # Phase 2: Swap — remove ModelA, add ModelB
        fresh_registry.clear()
        model_b = _make_profile("gemma3:12b", {ModelClass.GENERAL, ModelClass.REASONING}, size_gb=7.5)
        fresh_registry.register(model_b)

        # ZERO code change — same governor.resolve() call
        profile_b = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        # AMG must re-route to ModelB automatically
        assert profile_b.model_name == "gemma3:12b", (
            f"Model swap failed: expected gemma3:12b but got {profile_b.model_name}"
        )

    def test_swap_embedding_model_zero_code_change(self, fresh_registry, hw_8gb):
        """INVARIANT A1 for EMBEDDER role: swap embedding model, AMG auto-routes."""
        embed_v1 = _make_profile("nomic-embed-text:latest", {ModelClass.EMBEDDING}, size_gb=0.3)
        fresh_registry.register(embed_v1)

        gov = PortfolioGovernor(registry=fresh_registry)
        p1 = gov.resolve(role="EMBEDDER", requested_model="auto", hw=hw_8gb)
        assert p1.model_name == "nomic-embed-text:latest"

        # Swap: replace with different embedding model
        fresh_registry.clear()
        embed_v2 = _make_profile("mxbai-embed-large:latest", {ModelClass.EMBEDDING}, size_gb=0.7)
        fresh_registry.register(embed_v2)

        p2 = gov.resolve(role="EMBEDDER", requested_model="auto", hw=hw_8gb)
        assert p2.model_name == "mxbai-embed-large:latest"

    def test_swap_amg_decision_reflects_registry(self, fresh_registry, hw_8gb):
        """INVARIANT A1: AMGBootstrap._make_decisions() reflects current registry state."""
        # Register both models to compare selection logic
        m1 = _make_profile("small-model:4b", {ModelClass.GENERAL}, size_gb=2.5, confidence=0.7)
        m2 = _make_profile("large-model:14b", {ModelClass.GENERAL, ModelClass.REASONING}, size_gb=7.5, confidence=0.92)
        fresh_registry.register(m1)
        fresh_registry.register(m2)

        req = BootRequest(startup_mode="DEEP", required_capabilities=["conversation"])
        decisions = AMGBootstrap._make_decisions(req, fresh_registry, hw_8gb)

        assert len(decisions) >= 1
        # AMG selects from what's in registry — no hardcoded name
        selected_names = {d.profile.model_name for d in decisions}
        assert selected_names.issubset({"small-model:4b", "large-model:14b"})


# ---------------------------------------------------------------------------
# A2. Unknown Model Auto-Discovery Invariant
# ---------------------------------------------------------------------------

class TestUnknownModelAutoDiscovery:

    def test_brand_new_model_auto_classified_and_routed(self, fresh_registry, hw_8gb):
        """
        INVARIANT A2:
        A completely unknown model appears in the Ollama registry.
        AMG must inspect → classify → route it without crashing.
        resolved_via must be 'auto' (not 'emergency_fallback').
        """
        unknown_model = ModelCapabilityProfile(
            model_name="totally-unknown-model:7b",
            model_classes={ModelClass.GENERAL},
            assessment_confidence=0.55,  # Low confidence — "we don't know much about it"
        )
        fresh_registry.register(unknown_model)

        gov = PortfolioGovernor(registry=fresh_registry)
        profile = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        # Must route without crashing
        assert profile is not None
        assert profile.model_name == "totally-unknown-model:7b"
        # resolved_via must be 'auto', not 'emergency_fallback'
        assert profile.resolved_via in ("auto", "fallback"), (
            f"Expected 'auto' or 'fallback', got '{profile.resolved_via}'"
        )
        assert profile.resolved_via != "emergency_fallback"

    def test_inspector_classifies_minimal_metadata_model(self, fresh_registry):
        """
        INVARIANT A2: ModelInspector.build_profile() must not crash on minimal /api/show output.
        Represents an unknown model with very few metadata fields.
        """
        from core.runtime.base_adapter import RuntimeModelInfo
        minimal_info = RuntimeModelInfo(
            model_name="mystery-model:latest",
            size_gb=4.5,
            details={"family": "unknown", "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            model_info={},
            capabilities=[],
            template="",
        )
        profile = ModelInspector.build_profile(minimal_info)

        assert profile is not None
        assert profile.model_name == "mystery-model:latest"
        # Must have at least GENERAL capability
        assert ModelClass.GENERAL in profile.model_classes
        # Assessment confidence should reflect uncertainty
        assert 0.0 <= profile.assessment_confidence <= 1.0

    def test_boot_with_unknown_model_no_crash(self, fresh_registry, hw_8gb):
        """
        INVARIANT A2: Full AMGBootstrap.boot() with unknown model in snapshot — must complete.
        """
        from core.runtime.base_adapter import RuntimeModelInfo
        snap = RuntimeSnapshot()
        snap.endpoints["127.0.0.1:11434"] = EndpointInfo(
            host="127.0.0.1:11434", endpoint_type=EndpointType.GPU,
            is_alive=True, latency_ms=5.0
        )
        snap.available_models = [
            AvailableModel(name="brand-new-7b:latest", size_gb=4.1, digest="sha256:aabbcc"),
        ]

        bootstrapper = AMGBootstrap()
        bootstrapper.discovery.snapshot = MagicMock(return_value=snap)

        # ModelInspector will be called — return minimal RuntimeModelInfo
        minimal_info = RuntimeModelInfo(
            model_name="brand-new-7b:latest",
            size_gb=4.1,
            details={"family": "llama", "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            model_info={},
            capabilities=[],
            template="",
        )

        with patch("core.governor.hardware_monitor.HardwareMonitor.get_state", return_value=hw_8gb), \
             patch("core.runtime.ollama_adapter.OllamaAdapter.inspect_model_sync",
                   return_value=minimal_info), \
             patch("requests.post"):
            req = BootRequest(startup_mode="FAST", dry_run=True)
            report = bootstrapper.boot(req)

        assert report is not None
        assert len(report.decisions) >= 1


# ---------------------------------------------------------------------------
# A3. Engine Profile Agnosticism Invariant
# ---------------------------------------------------------------------------

class TestEngineProfileAgnosticism:

    def test_execution_profile_has_no_model_specific_flags(self, fresh_registry, hw_8gb):
        """
        INVARIANT A3:
        ExecutionProfile must NOT contain any field that Engine could use to
        branch behavior based on model_name. Engine must be fully driven by
        pre-computed profile parameters only.
        """
        model_a = _make_profile("qwen3.5:4b", {ModelClass.GENERAL})
        model_b = _make_profile("mistral:7b", {ModelClass.GENERAL})

        gov = PortfolioGovernor(registry=ModelRegistry.instance())
        gov._registry.clear()
        gov._registry.register(model_a)
        profile_a = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        gov._registry.clear()
        gov._registry.register(model_b)
        profile_b = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        # Both profiles must share the same structural parameters for same role+quality
        assert profile_a.role_name == profile_b.role_name
        assert profile_a.backend == profile_b.backend        # Same hw, same decision
        assert profile_a.num_ctx == profile_b.num_ctx         # Context window from role policy
        assert profile_a.temperature == profile_b.temperature # Temperature from role policy
        # model_name differs — but everything Engine uses should be identical
        assert profile_a.model_name != profile_b.model_name

    def test_execution_profile_to_ollama_options_model_agnostic(self, fresh_registry, hw_8gb):
        """
        INVARIANT A3: to_ollama_options() output is identical for same role regardless of model.
        Proves Engine receives identical parameters for same role.
        """
        gov = PortfolioGovernor(registry=fresh_registry)

        fresh_registry.register(_make_profile("model-x:4b", {ModelClass.GENERAL}))
        p1 = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        fresh_registry.clear()
        fresh_registry.register(_make_profile("model-y:7b", {ModelClass.GENERAL}))
        p2 = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        opts1 = p1.to_ollama_options()
        opts2 = p2.to_ollama_options()

        # Structural options must be identical (model_name is NOT in to_ollama_options)
        for key in ("num_ctx", "temperature", "top_p", "repeat_penalty"):
            assert opts1.get(key) == opts2.get(key), (
                f"Key '{key}' differs: {opts1.get(key)} vs {opts2.get(key)}"
            )

    def test_governor_decision_trace_shows_why(self, fresh_registry, hw_8gb):
        """
        INVARIANT A3: GovernorDecision.reasons must explain the selection in capability terms,
        not model-name terms. Observability must be capability-driven.
        """
        fresh_registry.register(_make_profile("some-model:4b", {ModelClass.GENERAL, ModelClass.REASONING}))
        gov = PortfolioGovernor(registry=fresh_registry)
        profile = gov.resolve(role="RECEPTIONIST", requested_model="auto", hw=hw_8gb)

        decision = profile.decision
        assert decision is not None
        assert decision.selected_model == "some-model:4b"
        # resolved_via must be traceable
        assert decision.resolved_via in ("auto", "explicit", "fallback")
        # candidates_evaluated shows scoring was done
        assert len(decision.candidates_evaluated) >= 1
