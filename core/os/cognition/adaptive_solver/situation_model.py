"""
core/os/cognition/adaptive_solver/situation_model.py
Rich Situation Model Assessor & Expected vs Actual Divergence Detector.

Enforces:
- Mission Immutability Hash
- Explicit Expected vs Actual tracking
- Dynamic Strategy Invalidation on unexpected workspace findings
"""

from __future__ import annotations
import hashlib
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from core.os.cognition.adaptive_solver.models import (
    ActionGranularity,
    ExpectedVsActual,
    SituationModel,
)
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class SituationModelAssessor:
    """Maintains and updates JKAI's real-time situational ground truth."""

    def initialize_situation(
        self,
        mission: CanonicalMissionSpec,
        initial_workspace_files: Optional[List[str]] = None,
    ) -> SituationModel:
        files = initial_workspace_files or []
        groups, anomalies = self.cluster_files_by_pattern(files)

        num_groups = len(groups)
        complexity = min(1.0, max(0.1, (len(files) * 0.05) + (num_groups * 0.2)))
        initial_gran = ActionGranularity.PROBE if len(files) > 2 or num_groups > 1 else ActionGranularity.PRECISION

        # Compute immutable hash of mission requirements to guard against tampering
        req_repr = "".join([f"{sc.criterion_id}:{sc.description}" for sc in mission.success_criteria])
        mission_hash = hashlib.sha256(f"{mission.mission_id}:{mission.raw_goal}:{req_repr}".encode()).hexdigest()

        return SituationModel(
            mission_id=mission.mission_id,
            initial_hypothesis=f"Initial hypothesis for '{mission.raw_goal[:60]}...' across {len(files)} discovered files.",
            immutable_mission_hash=mission_hash,
            discovered_files=files,
            homogenous_groups=groups,
            anomalous_items=anomalies,
            known_facts={},
            unknowns=[f"Verify schema consistency across {len(files)} files" if files else "Inspect target environment"],
            expected_vs_actual=[
                ExpectedVsActual(
                    expected_state=f"Expected {len(files)} files to match initial group distribution",
                    observed_reality=f"Classified into {num_groups} groups and {len(anomalies)} anomalies",
                    is_divergent=False
                )
            ],
            current_granularity=initial_gran,
            complexity_score=round(complexity, 2),
            risk_score=0.2 if len(files) > 5 else 0.05,
            confidence_score=0.5,
            progress_percent=0.0,
            updated_at=time.time()
        )

    def cluster_files_by_pattern(self, files: List[str]) -> Tuple[Dict[str, List[str]], List[str]]:
        """Groups files into homogenous template clusters and identifies anomalies."""
        groups: Dict[str, List[str]] = {}
        anomalies: List[str] = []

        for f in files:
            base = os.path.basename(f)
            ext = os.path.splitext(f)[1].lower()

            if "test_" in base or "_test" in base:
                group_key = "tests"
            elif "legacy" in base or "deprecated" in base or "generated" in base:
                anomalies.append(f)
                continue
            elif ext in [".py", ".ts", ".js", ".json", ".yaml", ".xlsx"]:
                group_key = f"standard_{ext.replace('.', '')}"
            else:
                anomalies.append(f)
                continue

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(f)

        return groups, anomalies

    def record_probe_observation(
        self,
        situation: SituationModel,
        probe_target: str,
        expected_behavior: str,
        observed_behavior: str,
    ) -> SituationModel:
        """Records probe result and explicitly detects divergence between Expected vs Actual."""
        is_divergent = False
        div_reason = None
        obs_lower = observed_behavior.lower()

        # Check for divergence indicators (e.g. dependency error, incompatible schema)
        if any(err in obs_lower for err in ["modulenotfound", "importerror", "syntaxerror", "schemamismatch", "incompatible"]):
            is_divergent = True
            div_reason = f"Observation '{observed_behavior[:100]}' contradicted expectation '{expected_behavior}'"
            situation.known_facts[f"divergence:{probe_target}"] = observed_behavior
            situation.complexity_score = min(1.0, situation.complexity_score + 0.3)
            situation.confidence_score = max(0.1, situation.confidence_score - 0.2)
        else:
            situation.known_facts[f"verified:{probe_target}"] = True
            situation.confidence_score = min(1.0, situation.confidence_score + 0.1)

        situation.expected_vs_actual.append(
            ExpectedVsActual(
                expected_state=expected_behavior,
                observed_reality=observed_behavior,
                is_divergent=is_divergent,
                divergence_reason=div_reason
            )
        )

        situation.updated_at = time.time()
        return situation


situation_assessor = SituationModelAssessor()
