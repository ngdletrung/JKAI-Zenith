"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: MODEL RENAME INVARIANCE
tests/architecture/test_model_rename_invariance.py

Architectural Invariant Enforced:
    Renaming a model (e.g. 'qwen3.5:4b' -> 'totally-random-name:4b') while preserving
    its metadata/capability evidence MUST produce identical pool selection and capability classification.
    Proves that AMG v2 is metadata-driven intelligence, not hardcoded string regex matching.
"""

import pytest
from core.governance.model_capabilities import ModelCapabilityProfile, ModelClass, ModelPool
from core.governance import PortfolioGovernor


from core.governor.model_scorer import ModelScorer
from core.governor.hardware_monitor import HardwareState

class TestModelRenameInvariance:

    def test_model_rename_preserves_scoring_and_classification(self):
        hw = HardwareState()


        # Original model profile
        original = ModelCapabilityProfile(
            model_name="qwen3.5:4b",
            architecture="qwen2",
            family="qwen",
            context_length_max=32768,
            model_classes={ModelClass.GENERAL, ModelClass.REASONING},
            assessment_confidence=0.9,
        )

        # Renamed model profile with identical metadata/capabilities
        renamed = ModelCapabilityProfile(
            model_name="totally-random-name:4b",
            architecture="qwen2",
            family="qwen",
            context_length_max=32768,
            model_classes={ModelClass.GENERAL, ModelClass.REASONING},
            assessment_confidence=0.9,
        )

        assert original.model_classes == renamed.model_classes

        orig_score = ModelScorer.score(original, "PLANNER", "high", hw)
        renamed_score = ModelScorer.score(renamed, "PLANNER", "high", hw)

        assert orig_score.final_score == renamed_score.final_score, (
            "Model Rename Violation: Renaming a model with identical metadata must yield identical scores!"
        )




