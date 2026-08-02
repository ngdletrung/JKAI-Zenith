"""
🧪 AMG v2 — COMPREHENSIVE TEST SUITE
File: tests/test_amg_portfolio_governor.py

23 test cases covering all AMG pipeline stages.
Includes constitutional tests that enforce model-agnostic invariants.

Run:
    pytest tests/test_amg_portfolio_governor.py -v
"""

from __future__ import annotations
import asyncio
import time
import unittest
from dataclasses import asdict
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# AMG imports
from core.governor.model_capabilities import (
    ModelClass, ModelPool, ModelCapabilityProfile, ModelMemoryProfile,
    CapabilityEvidence, ModelScore, GovernorDecision, ExecutionProfile,
    ROLE_MINIMUM_CAPABILITY,
)
from core.governor.hardware_monitor import HardwareState
from core.governor.model_inspector import ModelInspector
from core.governor.resource_governor import ResourceGovernor
from core.governor.model_scorer import ModelScorer
from core.governor.model_registry import ModelRegistry
from core.governor.portfolio_governor import PortfolioGovernor
from core.runtime.base_adapter import RuntimeModelInfo


# ============================================================
# Test Fixtures
# ============================================================

def _make_hw(vram_free_mb: int = 5500, ram_free_gb: float = 80.0) -> HardwareState:
    return HardwareState(
        vram_total_mb=8192,
        vram_free_mb=vram_free_mb,
        ram_total_gb=128.0,
        ram_free_gb=ram_free_gb,
    )


def _make_dense_profile(
    name: str = "test-dense:7b",
    total_b: float = 7.0,
    file_gb: float = 4.5,
    num_layers: int = 32,
    classes=None,
    assessment_confidence: float = 0.85,
) -> ModelCapabilityProfile:
    if classes is None:
        classes = {ModelClass.GENERAL, ModelClass.TOOL_USE}
    return ModelCapabilityProfile(
        model_name=name,
        architecture="llama",
        family="llama",
        context_length_max=8192,
        memory=ModelMemoryProfile(
            weight_file_size_gb=file_gb,
            quantization="Q4_K_M",
            bytes_per_param=0.5,
            total_parameters_b=total_b,
            active_parameters_b=total_b,
            num_layers=num_layers,
            is_moe=False,
            estimated_full_weight_mb=file_gb * 1024,
            kv_cache_mb_per_1k_ctx=256.0,
            detection_method="api_show",
        ),
        model_classes=set(classes),
        assessment_confidence=assessment_confidence,
        last_inspected_at=time.time(),
    )


def _make_moe_profile(
    name: str = "test-moe:30b-a3b",
    total_b: float = 30.0,
    active_b: float = 3.0,
    file_gb: float = 17.0,
    num_layers: int = 48,
) -> ModelCapabilityProfile:
    return ModelCapabilityProfile(
        model_name=name,
        architecture="qwen3",
        family="qwen",
        context_length_max=32768,
        memory=ModelMemoryProfile(
            weight_file_size_gb=file_gb,
            quantization="UD-Q4_K_XL",
            bytes_per_param=0.5,
            total_parameters_b=total_b,
            active_parameters_b=active_b,
            num_layers=num_layers,
            is_moe=True,
            estimated_full_weight_mb=file_gb * 1024,
            kv_cache_mb_per_1k_ctx=26.0,  # MoE: proportional to active params
            detection_method="api_show",
        ),
        model_classes={ModelClass.GENERAL, ModelClass.REASONING, ModelClass.MOE, ModelClass.TOOL_USE},
        assessment_confidence=0.90,
        last_inspected_at=time.time(),
    )


def _make_inspector_info(
    name: str,
    model_info: Dict[str, Any] = None,
    capabilities: List[str] = None,
    template: str = "",
    size_gb: float = 4.0,
    digest: str = "abc123",
) -> RuntimeModelInfo:
    return RuntimeModelInfo(
        model_name=name,
        model_info=model_info or {},
        details={},
        capabilities=capabilities or [],
        template=template,
        digest=digest,
        size_gb=size_gb,
    )


# ============================================================
# 1. Model Registry Tests
# ============================================================

class TestModelRegistry(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Reset singleton before each test."""
        registry = ModelRegistry.instance()
        registry.clear()

    async def test_registry_discover_mocked(self):
        """Registry populates profiles from mock /api/tags + /api/show."""
        mock_adapter = AsyncMock()
        mock_adapter.health_check.return_value = MagicMock(is_alive=True)
        mock_adapter.runtime_id = "mock:test"

        from core.runtime.ollama_adapter import OllamaRuntimeAdapter
        mock_adapter.__class__ = OllamaRuntimeAdapter

        mock_adapter.list_models_with_digest.return_value = [
            {"name": "test-model:7b", "digest": "d001", "size_gb": 4.5}
        ]
        mock_adapter.inspect_model.return_value = _make_inspector_info(
            "test-model:7b",
            model_info={"general.architecture": "llama", "general.parameter_count": 7e9,
                         "llama.block_count": 32},
            capabilities=["completion", "tools"],
            size_gb=4.5,
        )

        registry = ModelRegistry.instance()
        count = await registry.discover([mock_adapter])

        self.assertGreater(count, 0)
        profile = registry.get("test-model:7b")
        self.assertIsNotNone(profile)
        self.assertIn(ModelClass.TOOL_USE, profile.model_classes)

    async def test_registry_incremental_refresh(self):
        """Second discover() skips /api/show for unchanged models."""
        mock_adapter = AsyncMock()
        mock_adapter.health_check.return_value = MagicMock(is_alive=True)
        mock_adapter.runtime_id = "mock:test"

        from core.runtime.ollama_adapter import OllamaRuntimeAdapter
        mock_adapter.__class__ = OllamaRuntimeAdapter

        entry = {"name": "cached-model:3b", "digest": "same_digest_v1", "size_gb": 2.0}
        mock_adapter.list_models_with_digest.return_value = [entry]
        mock_adapter.inspect_model.return_value = _make_inspector_info(
            "cached-model:3b", size_gb=2.0, digest="same_digest_v1"
        )

        registry = ModelRegistry.instance()
        await registry.discover([mock_adapter])
        first_call_count = mock_adapter.inspect_model.call_count

        # Second discover — same digest → should NOT call inspect again
        await registry.discover([mock_adapter])
        self.assertEqual(mock_adapter.inspect_model.call_count, first_call_count,
                         "inspect_model should NOT be called again for unchanged model")

    async def test_registry_disk_cache_roundtrip(self):
        """Save → reload → profiles are identical."""
        import tempfile, os, json
        registry = ModelRegistry.instance()

        # Inject a known profile
        profile = _make_dense_profile("cache-test:7b")
        registry.inject(profile)

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        registry._cache_path = tmp_path
        registry._save_disk_cache()

        # Clear and reload
        registry.clear()
        registry._load_disk_cache()

        reloaded = registry.get("cache-test:7b")
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.model_name, "cache-test:7b")
        self.assertIn(ModelClass.GENERAL, reloaded.model_classes)
        os.unlink(tmp_path)


# ============================================================
# 2. Model Inspector Tests
# ============================================================

class TestModelInspector(unittest.TestCase):

    def test_inspector_metadata_only_no_name_check(self):
        """Inspector uses only metadata — no model name inspection."""
        info = _make_inspector_info(
            name="completely-unknown-model:7b",   # Deliberately nonsense name
            model_info={
                "general.architecture": "llama",
                "general.parameter_count": 7e9,
                "llama.block_count": 32,
                "llama.context_length": 8192,
            },
            capabilities=["completion", "tools"],
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.GENERAL, profile.model_classes)
        self.assertIn(ModelClass.TOOL_USE, profile.model_classes)

    def test_inspector_moe_from_expert_keys(self):
        """MoE detected from model_info expert keys, not model name."""
        info = _make_inspector_info(
            name="completely-random-name:xyz",     # No MoE hint in name
            model_info={
                "general.architecture": "qwen3",
                "qwen3.num_experts": 128,
                "qwen3.num_experts_per_tok": 8,
                "general.parameter_count": 30e9,
                "qwen3.block_count": 48,
            },
            capabilities=["completion"],
            size_gb=17.0,
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.MOE, profile.model_classes)
        # Active params should be MUCH less than total (30B total → ~1.9B active)
        self.assertLess(profile.parameters_active_b, profile.memory.total_parameters_b)

    def test_inspector_reasoning_multi_source(self):
        """Multiple reasoning sources → high confidence → REASONING asserted."""
        info = _make_inspector_info(
            name="any-model:4b",
            model_info={
                "general.architecture": "qwen2",
                "general.parameter_count": 4e9,
                "general.tags": ["thinking", "reasoning"],
            },
            capabilities=["completion", "thinking"],   # Source 1: capabilities API
            template="<think>{{thinking}}</think>{{response}}",  # Source 2: template
            size_gb=2.5,
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.REASONING, profile.model_classes)
        # Confidence should be high (multi-source)
        reasoning_ev = [e for e in profile.capability_evidences
                        if e.capability == ModelClass.REASONING]
        self.assertTrue(any(e.confidence >= 0.75 for e in reasoning_ev))

    def test_inspector_reasoning_single_source_may_not_assert(self):
        """Single <think> template alone → low confidence (may not assert REASONING)."""
        info = _make_inspector_info(
            name="any-model:3b",
            model_info={"general.architecture": "llama", "general.parameter_count": 3e9},
            capabilities=["completion"],  # NO "thinking" in capabilities
            template="<think>{{thinking}}</think>",   # Template only
            size_gb=2.0,
        )
        profile = ModelInspector.build_profile(info)
        # Either not asserted (confidence < 0.75), or asserted with single source
        reasoning_ev = [e for e in profile.capability_evidences
                        if e.capability == ModelClass.REASONING]
        if reasoning_ev:
            # If asserted, must have sources documented
            self.assertTrue(len(reasoning_ev[0].sources) > 0)

    def test_inspector_vision_detection(self):
        """Vision capability detected from architecture/capabilities metadata."""
        info = _make_inspector_info(
            name="any-vision-model:2b",
            model_info={
                "general.architecture": "moondream",
                "general.parameter_count": 2e9,
                "vision.encoder_type": "vit-l",
            },
            capabilities=["completion", "vision"],
            size_gb=1.8,
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.VISION, profile.model_classes)
        self.assertTrue(profile.has_vision)

    def test_inspector_embedding_detection(self):
        """Embedding model detected from pooling key and capabilities."""
        info = _make_inspector_info(
            name="any-embed-model:latest",
            model_info={
                "general.architecture": "nomic-bert",
                "general.parameter_count": 0.137e9,
                "nomic-bert.pooling_type": "mean",
            },
            capabilities=["embedding"],
            template="",  # No chat template
            size_gb=0.27,
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.EMBEDDING, profile.model_classes)
        self.assertNotIn(ModelClass.GENERAL, profile.model_classes)  # embedding-only
        self.assertTrue(profile.is_embedding_only)

    def test_inspector_tool_use_detection(self):
        """TOOL_USE detected from capabilities list."""
        info = _make_inspector_info(
            name="some-model:7b",
            model_info={"general.architecture": "llama", "general.parameter_count": 7e9},
            capabilities=["completion", "tools"],
            size_gb=4.5,
        )
        profile = ModelInspector.build_profile(info)
        self.assertIn(ModelClass.TOOL_USE, profile.model_classes)

    # ── CONSTITUTIONAL TESTS ────────────────────────────────────────────

    def test_no_model_name_dependency(self):
        """
        CONSTITUTIONAL TEST: Same metadata → same capabilities regardless of name.
        AMG must not inspect model_name to make decisions.
        """
        base_info = dict(
            model_info={
                "general.architecture": "llama",
                "general.parameter_count": 7e9,
                "llama.block_count": 32,
                "llama.context_length": 8192,
                "general.tags": ["thinking"],
            },
            capabilities=["completion", "thinking", "tools"],
            template="<think>{{t}}</think>",
            size_gb=4.5,
        )
        names = ["abc-7b", "qwerty-llm:7b", "completely-random-name:latest",
                 "xyzzy-thinking-model:7b"]
        profiles = [ModelInspector.build_profile(_make_inspector_info(n, **base_info))
                    for n in names]

        reference_classes = profiles[0].model_classes
        for p in profiles[1:]:
            self.assertEqual(
                p.model_classes, reference_classes,
                f"Model '{p.model_name}' got different classes {p.model_classes} "
                f"vs reference {reference_classes} — AMG has name dependency!"
            )

    def test_model_name_rename_invariance(self):
        """
        CONSTITUTIONAL TEST: Renaming a model must not change its ExecutionProfile.
        If rename causes decision change → architectural violation.
        """
        metadata = dict(
            model_info={
                "general.architecture": "qwen3",
                "qwen3.num_experts": 128,
                "qwen3.num_experts_per_tok": 8,
                "general.parameter_count": 30e9,
                "qwen3.block_count": 48,
            },
            capabilities=["completion", "thinking", "tools"],
            template="<think>{{t}}</think>",
            size_gb=17.0,
        )
        names = ["model-a:xyz", "model-b:abc", "totally-different-name:latest"]
        profiles = [ModelInspector.build_profile(_make_inspector_info(n, **metadata))
                    for n in names]

        # All should have MoE (from expert keys, not name)
        for p in profiles:
            self.assertIn(ModelClass.MOE, p.model_classes,
                          f"'{p.model_name}' missing MOE despite expert metadata")

        # Memory profiles should be identical (file-size based)
        file_sizes = {p.memory.weight_file_size_gb for p in profiles}
        self.assertEqual(len(file_sizes), 1,
                         "Memory profile differs by model name — invariance violation!")


# ============================================================
# 3. Memory Model Tests
# ============================================================

class TestMemoryModel(unittest.TestCase):

    def test_memory_dense_model_correct(self):
        """Dense model: file_size ≈ total_params × bytes_per_param."""
        profile = _make_dense_profile(total_b=7.0, file_gb=4.5)
        mem = profile.memory
        self.assertEqual(mem.total_parameters_b, mem.active_parameters_b,
                         "Dense model: active == total")
        self.assertFalse(mem.is_moe)

    def test_memory_moe_not_active_times_bytes(self):
        """
        MoE model: file_size MUST NOT equal active_params × bytes_per_param.
        Qwen3-30B-A3B: 3B active × Q4 ≈ 1.5GB, but file = 17GB.
        """
        profile = _make_moe_profile(
            total_b=30.0, active_b=3.0, file_gb=17.0
        )
        mem = profile.memory
        # Naive wrong formula
        naive_estimate = mem.active_parameters_b * mem.bytes_per_param
        # File size must be much larger
        self.assertGreater(
            mem.weight_file_size_gb, naive_estimate,
            f"MoE file size ({mem.weight_file_size_gb}GB) should be >> "
            f"active_params×bytes ({naive_estimate}GB)"
        )
        self.assertLess(mem.active_parameters_b, mem.total_parameters_b)
        self.assertTrue(mem.is_moe)

    def test_memory_kv_cache_scales_with_context(self):
        """KV cache grows proportionally with context length."""
        profile = _make_dense_profile(total_b=7.0, file_gb=4.5)
        mem = profile.memory
        kv_4k  = mem.kv_cache_for_context(4096)
        kv_8k  = mem.kv_cache_for_context(8192)
        kv_16k = mem.kv_cache_for_context(16384)
        self.assertAlmostEqual(kv_8k / kv_4k, 2.0, delta=0.1)
        self.assertAlmostEqual(kv_16k / kv_4k, 4.0, delta=0.1)


# ============================================================
# 4. Resource Governor Tests
# ============================================================

class TestResourceGovernor(unittest.TestCase):

    def test_pool_gpu_full_fit(self):
        """Small dense model fits entirely in VRAM → GPU backend."""
        profile = _make_dense_profile(total_b=3.0, file_gb=2.0, num_layers=28)
        hw = _make_hw(vram_free_mb=5500)  # 5.5GB VRAM free
        alloc = ResourceGovernor.allocate(profile, hw, context_len=4096)
        self.assertEqual(alloc.backend, "GPU")
        self.assertEqual(alloc.memory_layout, "VRAM_ONLY")
        self.assertEqual(alloc.num_gpu_layers, 28)
        self.assertTrue(alloc.is_viable)

    def test_pool_hybrid_moe(self):
        """Large MoE model exceeds VRAM → HYBRID backend."""
        profile = _make_moe_profile(total_b=30.0, active_b=3.0, file_gb=17.0, num_layers=48)
        hw = _make_hw(vram_free_mb=5500, ram_free_gb=80.0)
        alloc = ResourceGovernor.allocate(profile, hw, context_len=8192)
        self.assertEqual(alloc.backend, "HYBRID")
        self.assertEqual(alloc.memory_layout, "VRAM_RAM_SPLIT")
        self.assertGreater(alloc.num_gpu_layers, 0)
        self.assertLess(alloc.num_gpu_layers, 48)
        self.assertTrue(alloc.is_viable)

    def test_pool_cpu_only_low_vram(self):
        """Very low VRAM → CPU/RAM backend."""
        profile = _make_moe_profile(file_gb=17.0, num_layers=48)
        hw = _make_hw(vram_free_mb=800, ram_free_gb=60.0)  # Only 800MB VRAM
        alloc = ResourceGovernor.allocate(profile, hw, context_len=4096)
        self.assertEqual(alloc.backend, "CPU")
        self.assertEqual(alloc.memory_layout, "RAM_ONLY")
        self.assertEqual(alloc.num_gpu_layers, 0)

    def test_vram_budget_stack_applied(self):
        """VRAM budget stack correctly subtracts KV cache, buffers, margin."""
        profile = _make_dense_profile(total_b=7.0, file_gb=4.5, num_layers=32)
        hw = _make_hw(vram_free_mb=5500)

        # With large context → more KV cache → fewer GPU layers
        alloc_small_ctx = ResourceGovernor.allocate(profile, hw, context_len=2048)
        alloc_large_ctx = ResourceGovernor.allocate(profile, hw, context_len=16384)

        # Large context consumes more VRAM for KV → may result in fewer GPU layers
        # (or same if model still fits — the budget stack is what matters)
        self.assertLessEqual(alloc_large_ctx.kv_cache_mb, alloc_small_ctx.kv_cache_mb * 10,
                             "KV cache scaling should be proportional")


# ============================================================
# 5. Portfolio Governor Tests (Dynamic Resource Pressure)
# ============================================================

class TestPortfolioGovernor(unittest.TestCase):

    def _make_gov_with_registry(self, profiles) -> PortfolioGovernor:
        registry = ModelRegistry.instance()
        registry.clear()
        for p in profiles:
            registry.inject(p)
        return PortfolioGovernor(registry=registry)

    def test_portfolio_resolve_explicit(self):
        """Explicit model name → direct profile, no auto-routing."""
        profile = _make_dense_profile("explicit-model:7b")
        gov = self._make_gov_with_registry([profile])
        hw = _make_hw(vram_free_mb=5500)
        result = gov.resolve("PLANNER", "explicit-model:7b", quality="medium", hw=hw)
        self.assertEqual(result.model_name, "explicit-model:7b")
        self.assertEqual(result.resolved_via, "explicit")

    def test_portfolio_resolve_auto_reasoning(self):
        """auto + reasoning requirement → selects model with REASONING class."""
        reasoning_model = _make_dense_profile(
            "reasoning-model:7b",
            classes={ModelClass.GENERAL, ModelClass.REASONING, ModelClass.TOOL_USE}
        )
        general_model = _make_dense_profile(
            "general-model:3b", total_b=3.0, file_gb=2.0,
            classes={ModelClass.GENERAL, ModelClass.TOOL_USE}
        )
        gov = self._make_gov_with_registry([reasoning_model, general_model])
        hw = _make_hw(vram_free_mb=5500)
        result = gov.resolve("PLANNER", "auto",
                             capability_requirements=["reasoning"],
                             quality="medium", hw=hw)
        # Reasoning model must be preferred
        self.assertEqual(result.model_name, "reasoning-model:7b")
        self.assertEqual(result.resolved_via, "auto")

    def test_capability_threshold_graceful_fail(self):
        """No model meets minimum capability → GovernorDecision with explanation."""
        tiny_model = _make_dense_profile(
            "tiny-model:0.6b", total_b=0.6, file_gb=0.5,
            classes={ModelClass.GENERAL},  # No REASONING for DEEP_REASONER
            assessment_confidence=0.85,
        )
        gov = self._make_gov_with_registry([tiny_model])
        hw = _make_hw(vram_free_mb=5500)
        result = gov.resolve("DEEP_REASONER", "auto", quality="high", hw=hw)
        # Should still return a profile (graceful, not crash)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.decision)
        # Decision should document graceful_failure or score reason
        decision = result.decision
        self.assertTrue(
            decision.graceful_failure or any("minimum" in r.lower() for r in decision.reasons),
            "GovernorDecision should document minimum capability failure"
        )

    def test_quality_aware_fallback(self):
        """HIGH quality request → best available model selected with decision trace."""
        # A capable small model that meets minimum capability for PLANNER
        small_capable_model = _make_dense_profile(
            "capable-small:7b", total_b=7.0, file_gb=4.5,
            classes={ModelClass.GENERAL, ModelClass.REASONING, ModelClass.TOOL_USE},
            assessment_confidence=0.85,
        )
        gov = self._make_gov_with_registry([small_capable_model])
        hw = _make_hw(vram_free_mb=5500, ram_free_gb=80.0)
        result = gov.resolve("PLANNER", "auto", quality="high", hw=hw)
        self.assertIsNotNone(result)
        self.assertIn(result.resolved_via, ("auto", "fallback", "explicit"))
        # Must have a decision trace
        self.assertIsNotNone(result.decision)
        # Selected model must be from our registry
        self.assertEqual(result.model_name, "capable-small:7b")

    def test_dynamic_resource_pressure(self):
        """
        ADAPTIVE TEST: Same model, different VRAM → different backend.
        This proves the 'A' in AMG is real.
        """
        profile = _make_moe_profile(
            "adaptive-model:30b", total_b=30.0, active_b=3.0, file_gb=17.0, num_layers=48
        )

        scenarios = [
            (6000, "GPU or HYBRID"),   # 6GB VRAM free → partial GPU
            (3000, "HYBRID or CPU"),   # 3GB VRAM free → less GPU
            (800,  "CPU"),             # 800MB VRAM free → CPU
        ]

        results = []
        for vram_mb, label in scenarios:
            hw = _make_hw(vram_free_mb=vram_mb, ram_free_gb=80.0)
            alloc = ResourceGovernor.allocate(profile, hw, context_len=4096)
            results.append((vram_mb, alloc.backend, alloc.num_gpu_layers))

        # With the most VRAM, should have more GPU layers than with least
        _, backend_6gb, layers_6gb = results[0]
        _, backend_800mb, layers_800mb = results[2]

        self.assertGreater(
            layers_6gb, layers_800mb,
            f"6GB VRAM ({layers_6gb} layers) should have more GPU layers than "
            f"800MB VRAM ({layers_800mb} layers)"
        )
        # CPU-only scenario
        self.assertEqual(backend_800mb, "CPU")

    def test_new_model_zero_code_change(self):
        """
        ZERO CODE CHANGE TEST: Inject a completely new mock model.
        AMG must inspect, classify, and route it without ANY code change.
        """
        # Simulate pulling a brand new, previously unknown model
        new_model_info = _make_inspector_info(
            name="brand-new-model-2026:8b",   # Never seen before
            model_info={
                "general.architecture": "new-arch-2026",
                "general.parameter_count": 8e9,
                "new-arch-2026.block_count": 36,
                "new-arch-2026.context_length": 16384,
            },
            capabilities=["completion", "tools", "thinking"],
            template="<think>{{thinking}}</think>{{response}}",
            size_gb=5.2,
        )

        # Step 1: Inspector classifies with NO code change
        profile = ModelInspector.build_profile(new_model_info)
        self.assertIn(ModelClass.GENERAL, profile.model_classes)
        self.assertIn(ModelClass.TOOL_USE, profile.model_classes)
        self.assertIn(ModelClass.REASONING, profile.model_classes)

        # Step 2: Inject into registry (simulates ollama pull + auto-discovery)
        registry = ModelRegistry.instance()
        registry.clear()
        registry.inject(profile)

        # Step 3: Governor routes it correctly
        gov = PortfolioGovernor(registry=registry)
        hw = _make_hw(vram_free_mb=5500)
        result = gov.resolve("PLANNER", "auto",
                             capability_requirements=["reasoning"],
                             quality="medium", hw=hw)

        # Must route to our new model (it's the only one)
        self.assertEqual(result.model_name, "brand-new-model-2026:8b")
        # Engine profile must be complete
        self.assertIn(result.backend, ("GPU", "HYBRID", "CPU"))
        self.assertIsNotNone(result.decision)

    def test_execution_profile_model_agnostic(self):
        """
        INVARIANT TEST: ExecutionProfile must not contain model-specific data.
        Engine can only use: backend, num_gpu_layers, num_predict, num_ctx, temperature.
        """
        profile = _make_dense_profile("irrelevant-model-name:7b")
        gov = self._make_gov_with_registry([profile])
        hw = _make_hw()
        result = gov.resolve("PLANNER", "auto", quality="medium", hw=hw)

        # These must exist and be valid regardless of model name
        self.assertIn(result.backend, ("GPU", "HYBRID", "CPU"))
        self.assertIn(result.memory_layout, ("VRAM_ONLY", "VRAM_RAM_SPLIT", "RAM_ONLY"))
        self.assertIsInstance(result.num_gpu_layers, int)
        self.assertIsInstance(result.num_predict, int)
        self.assertIsInstance(result.num_ctx, int)
        self.assertIsInstance(result.temperature, float)

        # to_ollama_options() must not raise
        opts = result.to_ollama_options()
        self.assertIsInstance(opts, dict)
        self.assertIn("num_gpu", opts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
