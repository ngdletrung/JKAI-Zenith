# -*- coding: utf-8 -*-
"""
Unit test suite cho ModelFallback v2.0 (Adaptive Model Governor)
"""

import pytest
from core.governor.model_fallback import ModelFallback
from core.governor.model_capabilities import (
    ModelCapabilityProfile, QuantitativeCapabilityProfile,
    CapabilityScore, ModelClass
)


class TestModelFallbackV2:
    """Kiểm tra các tính năng nâng cao của ModelFallback v2.0."""

    @pytest.fixture
    def mock_profiles(self):
        # Model A: 3B parameters, high coding strength
        prof_a = ModelCapabilityProfile(
            model_name="coder-model:3b",
            model_classes={ModelClass.CODING},
            _quant_vector=QuantitativeCapabilityProfile(
                coding_strength=CapabilityScore.declared(0.95),
                reasoning_strength=CapabilityScore.declared(0.60),
                reliability=CapabilityScore.declared(0.95)
            )
        )

        # Model B: 7B parameters, high reasoning strength
        prof_b = ModelCapabilityProfile(
            model_name="reasoning-model:7b",
            model_classes={ModelClass.REASONING},
            _quant_vector=QuantitativeCapabilityProfile(
                coding_strength=CapabilityScore.declared(0.50),
                reasoning_strength=CapabilityScore.declared(0.92),
                reliability=CapabilityScore.declared(0.90)
            )
        )

        return [prof_a, prof_b]

    def test_fallback_by_required_capability_coding(self, mock_profiles):
        loaded = {"coder-model:3b", "reasoning-model:7b"}
        # Yêu cầu coding strength cao
        selected = ModelFallback.resolve_fallback(
            requested_model="missing-model:14b",
            loaded_models=loaded,
            registered_profiles=mock_profiles,
            required_capabilities={"coding_strength": 1.0}
        )
        assert selected == "coder-model:3b"

    def test_fallback_by_required_capability_reasoning(self, mock_profiles):
        loaded = {"coder-model:3b", "reasoning-model:7b"}
        # Yêu cầu reasoning strength cao
        selected = ModelFallback.resolve_fallback(
            requested_model="missing-model:14b",
            loaded_models=loaded,
            registered_profiles=mock_profiles,
            required_capabilities={"reasoning_strength": 1.0}
        )
        assert selected == "reasoning-model:7b"

    def test_fallback_health_check_filter(self, mock_profiles):
        loaded = {"coder-model:3b", "reasoning-model:7b"}
        unhealthy = {"coder-model:3b"}  # coder model đang bị quá tải/OOM
        
        selected = ModelFallback.resolve_fallback(
            requested_model="missing-model:14b",
            loaded_models=loaded,
            registered_profiles=mock_profiles,
            required_capabilities={"coding_strength": 1.0},
            unhealthy_models=unhealthy
        )
        assert selected == "reasoning-model:7b"

    def test_fallback_chain_resolution(self, mock_profiles):
        loaded = {"coder-model:3b", "reasoning-model:7b"}
        chain = ModelFallback.resolve_fallback_chain(
            requested_model="missing-model:14b",
            loaded_models=loaded,
            registered_profiles=mock_profiles,
            required_capabilities={"coding_strength": 1.0}
        )
        assert len(chain) == 2
        assert chain[0] == "coder-model:3b"
        assert chain[1] == "reasoning-model:7b"
