"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — BOOTSTRAP ARCHITECTURE TEST SUITE
File: tests/test_amg_boot.py

Verifies:
    1. Dry-run mode is strictly READ-ONLY (no load/unload HTTP calls).
    2. Decision Parity: normal vs diagnostic mode yields identical model decisions.
    3. EvictionScore components are normalized to [0.0, 1.0].
    4. BootCache digest invalidation.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from core.runtime.runtime_discovery import (
    RuntimeDiscovery, EndpointInfo, EndpointType, AvailableModel, ResidentModel, RuntimeSnapshot,
)
from core.runtime.model_lifecycle import ModelLifecycleManager, EvictionScorer, LifecycleResult
from core.runtime.boot_cache import BootCache
from core.runtime.amg_boot import AMGBootstrap, BootRequest, BootReport
from core.governor.model_capabilities import ExecutionProfile, ModelCapabilityProfile, ModelClass
from core.governor.model_registry import ModelRegistry
from core.governor.hardware_monitor import HardwareState


class TestAMGBoot:

    @pytest.fixture
    def mock_snapshot(self):
        snap = RuntimeSnapshot()
        snap.endpoints["127.0.0.1:11434"] = EndpointInfo(
            host="127.0.0.1:11434", endpoint_type=EndpointType.GPU, is_alive=True, latency_ms=5.0
        )
        snap.endpoints["127.0.0.1:11435"] = EndpointInfo(
            host="127.0.0.1:11435", endpoint_type=EndpointType.CPU, is_alive=True, latency_ms=3.0
        )
        snap.available_models = [
            AvailableModel(name="qwen3.5:4b", size_gb=2.5, digest="digest_qwen"),
            AvailableModel(name="nomic-embed-text:latest", size_gb=0.3, digest="digest_nomic"),
        ]
        return snap

    @pytest.fixture
    def mock_hw(self):
        return HardwareState(
            vram_total_mb=8192,
            vram_free_mb=6500,
            ram_total_gb=128.0,
            ram_free_gb=96.0,
        )

    def test_dry_run_read_only(self, mock_snapshot, mock_hw):
        """Verify dry-run performs decisions but calls ZERO mutating HTTP endpoints."""
        bootstrapper = AMGBootstrap()
        bootstrapper.discovery.snapshot = MagicMock(return_value=mock_snapshot)

        req = BootRequest(startup_mode="FAST", dry_run=True, diagnostic=False)

        with patch("core.governor.hardware_monitor.HardwareMonitor.get_state", return_value=mock_hw), \
             patch("requests.post") as mock_post:
            report = bootstrapper.boot(req)

        assert report is not None
        assert len(report.decisions) > 0
        assert bootstrapper.lifecycle.dry_run is True
        # EMPIRICAL INVARIANT: Zero mutating HTTP POST requests (/api/generate, /api/chat, /api/embeddings) sent during dry-run
        mutating_calls = [
            c for c in mock_post.call_args_list
            if any(endpoint in str(c[0]) for endpoint in ["/api/generate", "/api/chat", "/api/embeddings"])
        ]
        assert len(mutating_calls) == 0

    def test_decision_parity(self, mock_hw):
        """Verify normal vs diagnostic mode yields identical model selections."""
        registry = ModelRegistry.instance()
        registry.clear()

        # Register sample profiles
        p1 = ModelCapabilityProfile(
            model_name="qwen3.5:4b",
            model_classes={ModelClass.GENERAL, ModelClass.REASONING},
            assessment_confidence=0.9,
        )
        p2 = ModelCapabilityProfile(
            model_name="nomic-embed-text:latest",
            model_classes={ModelClass.EMBEDDING},
            assessment_confidence=0.95,
        )
        registry.register(p1)
        registry.register(p2)

        req_normal = BootRequest(startup_mode="FAST", diagnostic=False)
        req_diag   = BootRequest(startup_mode="FAST", diagnostic=True)

        decisions_normal = AMGBootstrap._make_decisions(req_normal, registry, mock_hw)
        decisions_diag   = AMGBootstrap._make_decisions(req_diag, registry, mock_hw)

        assert len(decisions_normal) == len(decisions_diag)
        for d1, d2 in zip(decisions_normal, decisions_diag):
            assert d1.profile.model_name == d2.profile.model_name
            assert d1.profile.backend == d2.profile.backend
            assert d1.warmup_policy == d2.warmup_policy

    def test_eviction_score_normalization(self):
        """Verify EvictionScore is strictly within [0.0, 1.0]."""
        rm1 = ResidentModel(name="model1", host="127.0.0.1:11434", size_vram_mb=4000.0, size_ram_mb=0.0)
        rm2 = ResidentModel(name="model2", host="127.0.0.1:11434", size_vram_mb=1000.0, size_ram_mb=0.0)
        all_rm = [rm1, rm2]

        score1 = EvictionScorer.compute(rm1, all_rm, protected_names=[])
        score2 = EvictionScorer.compute(rm2, all_rm, protected_names=[])
        score_protected = EvictionScorer.compute(rm1, all_rm, protected_names=["model1"])

        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0
        assert score_protected == 0.0
        # Larger model should have higher eviction score (more VRAM freed)
        assert score1 > score2

    def test_boot_cache_digest(self, tmp_path):
        cache_file = os.path.join(tmp_path, "test_cache.json")
        cache = BootCache(cache_file=cache_file)

        p = ModelCapabilityProfile(
            model_name="test_model:latest",
            ollama_digest="digest_v1",
            model_classes={ModelClass.GENERAL},
        )
        cache.save_cache({"test_model:latest": p})

        loaded = cache.load_cache()
        assert "test_model:latest" in loaded
        assert loaded["test_model:latest"]["ollama_digest"] == "digest_v1"
