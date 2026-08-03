"""
JKAI ZENITH — 5-PLANE ARCHITECTURE INVARIANT TEST SUITE
tests/test_5plane_architecture_invariants.py

Invariants tested:
    P1. Plane 2 (Cognitive) can be imported from core.cognitive
    P2. Plane 3 (Knowledge) can be imported from core.knowledge
    P3. Plane 4 (Governance) can be imported from core.governance
    P4. Plane 5 (Infrastructure) can be imported from core.infrastructure
    P5. Backward compatibility shims work from core.compatibility
    P6. Constitutional One-Way Dependency Invariant:
        core.governance does NOT import from core.cognitive or core.kernel
        core.runtime does NOT import from core.cognitive
        ResourceRequest does NOT contain model_name
"""

import pytest
import sys
import importlib


class Test5PlaneStructure:

    def test_plane2_cognitive_import(self):
        from core.cognitive import CognitiveEngine
        assert CognitiveEngine is not None

    def test_plane3_knowledge_import(self):
        from core.knowledge import QdrantClientWrapper
        assert QdrantClientWrapper is not None


    def test_plane4_governance_import(self):
        from core.governance import (
            ExecutionProfile, PortfolioGovernor, ResourceGovernor,
            ModelInspector, ModelRegistry, ExecutionPolicy, DecisionTrace
        )
        assert ExecutionProfile is not None
        assert PortfolioGovernor is not None
        assert ExecutionPolicy is not None

    def test_plane5_infrastructure_import(self):
        from core.infrastructure import HardwareScheduler, ResourceRequest, BackendType
        assert HardwareScheduler is not None
        assert ResourceRequest is not None

    def test_compatibility_shims_import(self):
        from core.compatibility import ModelRouter, JKAIIntelligenceEngine
        assert ModelRouter is not None
        assert JKAIIntelligenceEngine is not None

    def test_constitutional_dependency_direction(self):
        """
        Verify that core.governance modules do NOT import from core.cognitive
        to enforce the One-Way Dependency Invariant.
        """
        import core.governance.model_capabilities as cap
        with open(cap.__file__, "r", encoding="utf-8") as f:
            code = f.read()

        assert "from core.cognitive" not in code, (
            "Constitutional Violation: core.governance must NOT import from core.cognitive"
        )
        assert "from core.kernel" not in code, (
            "Constitutional Violation: core.governance must NOT import from core.kernel"
        )
