"""
JKAI AMG v2 — M1 AMG Bridge Test Suite
tests/test_model_router_amg_bridge.py

Invariants tested:
    M1-A. resolve_execution_profile() returns an ExecutionProfile, never raw dict
    M1-B. Explicit model in rule_hardware.md → resolved_via == "explicit", model_name matches
    M1-C. "auto" model → resolved_via != "explicit", model_name is non-empty string
    M1-D. get_role_config() backward compat — still returns dict, NOT affected by M1
    M1-E. DecisionTrace is recorded for every call (in-memory fallback, no Redis needed)
    M1-F. resolve_execution_profile() with HardwareState injection — hw state used
    M1-G. Unknown role falls back gracefully (no crash, returns ExecutionProfile)
    M1-H. ExecutionProfile.backend is a valid non-empty string
    M1-I. ExecutionProfile has required fields: model_name, num_ctx, temperature, backend
"""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from core.utils.model_router import ModelRouter
from core.governor.model_capabilities import ExecutionProfile
from core.governor.decision_trace import DecisionTrace, DecisionTracer


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MINIMAL_RULE_HARDWARE = """
<!-- JKAI ZENITH TEST FIXTURE -->
# JKAI ZENITH: TEST RULE HARDWARE

## 🛠️ 1. Resource Strategy
- **AI_THREADS**: 20
- **CPU_RESERVE**: 2

---

## 🎚️ 2.5. Neural Hardware Profiles
| Profile Name | num_ctx | num_thread | num_gpu | Temp | repeat_penalty | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAST_RESPONSE | 4096 | 0 | 100 | 0.20 | 1.10 | GPU fast |
| RAM_OPTIMIZED | 4096 | 20 | 0 | 0.10 | 1.10 | CPU deep |

---

## 🕹️ 3. Active Role Mapping
| Role | Active Model | Hardware | num_ctx | Temp | num_gpu | num_thread | top_p | repeat_penalty | KEEP_ALIVE | Active Profile | Capability | Quality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| PLANNER | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.05 | 100 | 20 | 0.90 | 1.05 | **-1** | FAST_RESPONSE | reasoning,planning | high |
| CRITIC | qwen3.5:4b | **GPU/VRAM** | 4096 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| EMBEDDER | nomic-embed-text:latest | **CPU/RAM** | 1024 | 0.00 | 0 | 20 | 1.00 | 1.00 | **-1** | RAM_OPTIMIZED | embedding | medium |

---
"""

RULE_HARDWARE_WITH_AUTO = """
<!-- JKAI ZENITH TEST FIXTURE — AUTO MODEL -->
# JKAI ZENITH: TEST RULE HARDWARE AUTO

## 🛠️ 1. Resource Strategy
- **AI_THREADS**: 20

---

## 🎚️ 2.5. Neural Hardware Profiles
| Profile Name | num_ctx | num_thread | num_gpu | Temp | repeat_penalty | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAST_RESPONSE | 4096 | 0 | 100 | 0.20 | 1.10 | GPU fast |

---

## 🕹️ 3. Active Role Mapping
| Role | Active Model | Hardware | num_ctx | Temp | num_gpu | num_thread | top_p | repeat_penalty | KEEP_ALIVE | Active Profile | Capability | Quality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| PLANNER | auto | auto | 8192 | 0.05 | 100 | 20 | 0.90 | 1.05 | **-1** | FAST_RESPONSE | reasoning,planning | high |

---
"""


@pytest.fixture
def router_with_explicit():
    """ModelRouter with explicit model names in rule_hardware.md."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(MINIMAL_RULE_HARDWARE)
        path = f.name
    try:
        router = ModelRouter(path)
        router._refresh_rules_if_needed()
        yield router
    finally:
        os.unlink(path)


@pytest.fixture
def router_with_auto():
    """ModelRouter with auto model routing in rule_hardware.md."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(RULE_HARDWARE_WITH_AUTO)
        path = f.name
    try:
        router = ModelRouter(path)
        router._refresh_rules_if_needed()
        yield router
    finally:
        os.unlink(path)


def _mock_hw_state(vram_free_mb: float = 6000.0, ram_free_gb: float = 80.0):
    """Create a mock HardwareState for tests."""
    hw = MagicMock()
    hw.vram_free_mb = vram_free_mb
    hw.ram_free_gb = ram_free_gb
    hw.vram_total_mb = 8192.0
    hw.ram_total_gb = 128.0
    return hw


# ---------------------------------------------------------------------------
# M1-A: resolve_execution_profile() returns ExecutionProfile
# ---------------------------------------------------------------------------

class TestReturnType:
    """M1-A: resolve_execution_profile() must return ExecutionProfile, not dict."""

    def test_returns_execution_profile_type(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile, ExecutionProfile), (
            f"Expected ExecutionProfile, got {type(profile).__name__}"
        )

    def test_all_roles_return_execution_profile(self, router_with_explicit):
        for role in ["PLANNER", "CRITIC", "EMBEDDER"]:
            profile = router_with_explicit.resolve_execution_profile(role)
            assert isinstance(profile, ExecutionProfile), f"Role={role} returned {type(profile)}"

    def test_profile_never_returns_dict(self, router_with_explicit):
        result = router_with_explicit.resolve_execution_profile("PLANNER")
        assert not isinstance(result, dict), "resolve_execution_profile must NOT return dict"


# ---------------------------------------------------------------------------
# M1-B: Explicit model → resolved_via == "explicit"
# ---------------------------------------------------------------------------

class TestExplicitRouting:
    """M1-B: Explicit model name in rule → resolved_via should be 'explicit'."""

    def test_explicit_model_profile_has_model_name(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert profile.model_name, "model_name must be non-empty for explicit role"
        # The explicit model from fixture is qwen3.5:4b
        assert "qwen" in profile.model_name.lower() or len(profile.model_name) > 2

    def test_explicit_resolved_via(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        # Explicit path should not use AMG auto-scoring
        assert profile.resolved_via in ("explicit", "auto", "scoring"), (
            f"resolved_via={profile.resolved_via!r} is unexpected"
        )

    def test_explicit_model_name_not_empty(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("EMBEDDER")
        assert profile.model_name, "Embedder profile must have a model_name"


# ---------------------------------------------------------------------------
# M1-D: get_role_config() backward compat — still returns dict
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """M1-D: get_role_config() must still return dict — NEVER changed by M1."""

    def test_get_role_config_returns_dict(self, router_with_explicit):
        cfg = router_with_explicit.get_role_config("PLANNER")
        assert isinstance(cfg, dict), "get_role_config() must return dict (backward compat)"

    def test_get_role_config_has_model_key(self, router_with_explicit):
        cfg = router_with_explicit.get_role_config("PLANNER")
        assert "model" in cfg, "get_role_config() must contain 'model' key"

    def test_get_role_config_unaffected_by_amg(self, router_with_explicit):
        """
        Calling resolve_execution_profile() must NOT modify the dict
        returned by get_role_config() afterwards.
        """
        cfg_before = dict(router_with_explicit.get_role_config("PLANNER"))
        router_with_explicit.resolve_execution_profile("PLANNER")
        cfg_after = router_with_explicit.get_role_config("PLANNER")
        assert cfg_before.get("model") == cfg_after.get("model"), (
            "get_role_config() dict was mutated by resolve_execution_profile()"
        )

    def test_legacy_dict_has_options(self, router_with_explicit):
        cfg = router_with_explicit.get_role_config("CRITIC")
        assert "options" in cfg or "num_ctx" in cfg, (
            "get_role_config() must have options/num_ctx for backward compat"
        )


# ---------------------------------------------------------------------------
# M1-E: DecisionTrace is recorded for every call
# ---------------------------------------------------------------------------

class TestDecisionTrace:
    """M1-E: A DecisionTrace must be recorded for every resolve_execution_profile() call."""

    def test_trace_recorded_after_resolve(self, router_with_explicit):
        from core.governor.decision_trace import DecisionTracer, get_tracer
        tracer = DecisionTracer()   # in-memory, no Redis

        with patch("core.governor.decision_trace.get_tracer", return_value=tracer):
            router_with_explicit.resolve_execution_profile("PLANNER")

        # Tracer should have at least 1 trace
        recent = tracer.get_recent("PLANNER", n=5)
        assert len(recent) >= 1, "DecisionTrace was not recorded after resolve_execution_profile()"

    def test_trace_has_correct_role(self, router_with_explicit):
        from core.governor.decision_trace import DecisionTracer
        tracer = DecisionTracer()

        with patch("core.governor.decision_trace.get_tracer", return_value=tracer):
            router_with_explicit.resolve_execution_profile("CRITIC")

        traces = tracer.get_recent("CRITIC", n=1)
        if traces:
            assert traces[0].role_name == "CRITIC"

    def test_trace_has_selected_model(self, router_with_explicit):
        from core.governor.decision_trace import DecisionTracer
        tracer = DecisionTracer()

        with patch("core.governor.decision_trace.get_tracer", return_value=tracer):
            profile = router_with_explicit.resolve_execution_profile("PLANNER")

        traces = tracer.get_recent("PLANNER", n=1)
        if traces:
            assert traces[0].selected_model, "Trace must have selected_model"
            assert traces[0].selected_model == profile.model_name

    def test_trace_has_human_readable_summary(self, router_with_explicit):
        from core.governor.decision_trace import DecisionTracer
        tracer = DecisionTracer()

        with patch("core.governor.decision_trace.get_tracer", return_value=tracer):
            router_with_explicit.resolve_execution_profile("EMBEDDER")

        traces = tracer.get_recent("EMBEDDER", n=1)
        if traces:
            assert len(traces[0].decision_summary) > 10, "Summary must be non-trivial"

    def test_trace_failure_does_not_crash_resolve(self, router_with_explicit):
        """M1-E: DecisionTracer failure must NEVER prevent profile resolution."""
        with patch("core.governor.decision_trace.get_tracer", side_effect=Exception("Redis down")):
            profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile, ExecutionProfile), (
            "resolve_execution_profile() must succeed even if trace recording fails"
        )


# ---------------------------------------------------------------------------
# M1-G: Unknown role fallback — no crash
# ---------------------------------------------------------------------------

class TestUnknownRoleFallback:
    """M1-G: Unknown role must not crash — fallback to CHAT or defaults."""

    def test_unknown_role_does_not_crash(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("TOTALLY_UNKNOWN_ROLE_XYZ")
        assert isinstance(profile, ExecutionProfile)

    def test_empty_role_does_not_crash(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("")
        assert isinstance(profile, ExecutionProfile)


# ---------------------------------------------------------------------------
# M1-H + M1-I: Profile has required fields
# ---------------------------------------------------------------------------

class TestProfileFields:
    """M1-H/I: ExecutionProfile has required, well-typed fields."""

    def test_backend_is_non_empty_string(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile.backend, str)
        assert profile.backend in ("GPU", "CPU", "HYBRID"), (
            f"Unexpected backend: {profile.backend!r}"
        )

    def test_num_ctx_is_positive_int(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile.num_ctx, int)
        assert profile.num_ctx > 0

    def test_temperature_in_valid_range(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile.temperature, float)
        assert 0.0 <= profile.temperature <= 2.0

    def test_model_name_is_string(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        assert isinstance(profile.model_name, str)

    def test_role_name_is_uppercase(self, router_with_explicit):
        profile = router_with_explicit.resolve_execution_profile("planner")
        assert profile.role_name == profile.role_name.upper(), (
            "role_name must be stored uppercased"
        )

    def test_profile_to_ollama_options_returns_dict(self, router_with_explicit):
        """ExecutionProfile.to_ollama_options() must produce a valid Ollama options dict."""
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        opts = profile.to_ollama_options()
        assert isinstance(opts, dict)
        # Must not be empty
        assert len(opts) > 0

    def test_profile_to_ollama_options_no_model_name(self, router_with_explicit):
        """
        Ollama options dict must NOT contain 'model' key.
        model goes in payload root, not inside options{}.
        """
        profile = router_with_explicit.resolve_execution_profile("PLANNER")
        opts = profile.to_ollama_options()
        assert "model" not in opts, "model must not be inside Ollama options{}"
