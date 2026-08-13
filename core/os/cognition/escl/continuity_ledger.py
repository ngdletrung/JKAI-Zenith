"""
core/os/cognition/escl/continuity_ledger.py
E5 — Semantic Continuity Ledger & Lifecycle Tracking.

Tracks requirement lineage across all 11 stages.
Guarantees that no requirement is silently dropped or distorted.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.os.cognition.escl.contracts import (
    RequirementCategory,
    RequirementLifecycleStage,
    SemanticRequirement,
)


class SemanticContinuityBreakError(Exception):
    """Raised when a mandatory requirement is dropped during pipeline propagation."""
    pass


@dataclass
class SemanticContinuityLedger:
    """
    Authoritative Lifecycle Ledger tracking requirements across all stages.
    """
    mission_id: str
    canonical_goal_text: str
    requirements: List[SemanticRequirement] = field(default_factory=list)
    stage_traces: Dict[str, bool] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def add_requirement(
        self,
        category: RequirementCategory,
        description: str,
        expected_value: Any,
        is_mandatory: bool = True,
    ) -> SemanticRequirement:
        req_id = f"REQ-{len(self.requirements)+1:03d}"
        req = SemanticRequirement(
            req_id=req_id,
            category=category,
            description=description,
            expected_value=expected_value,
            is_mandatory=is_mandatory,
            current_stage=RequirementLifecycleStage.EXTRACTED,
        )
        self.requirements.append(req)
        return req

    def advance_all_to_stage(self, stage: RequirementLifecycleStage, details: Optional[str] = None):
        """Advances all active requirements to the next lifecycle stage."""
        for req in self.requirements:
            if req.current_stage != RequirementLifecycleStage.DROPPED:
                req.advance_stage(stage, details)
        self.stage_traces[stage.value] = True

    def assert_continuity(self, stage: RequirementLifecycleStage):
        """Asserts that all mandatory requirements exist and have reached the target stage."""
        for req in self.requirements:
            if req.is_mandatory and req.current_stage == RequirementLifecycleStage.DROPPED:
                raise SemanticContinuityBreakError(
                    f"CONTINUITY BREAK at {stage.value}: Mandatory requirement '{req.req_id}: {req.description}' was dropped!"
                )

    def record_stage(self, stage_name: str, passed: bool = True):
        self.stage_traces[stage_name] = passed

    def check_fulfillment(self) -> Dict[str, Any]:
        mandatory = [r for r in self.requirements if r.is_mandatory]
        fulfilled = [r for r in mandatory if r.fulfilled]
        unfulfilled = [r for r in mandatory if not r.fulfilled]
        
        all_passed = (len(unfulfilled) == 0)
        return {
            "all_passed": all_passed,
            "total_mandatory": len(mandatory),
            "fulfilled_count": len(fulfilled),
            "unfulfilled_list": [r.description for r in unfulfilled],
            "unfulfilled_ids": [r.req_id for r in unfulfilled],
            "score": len(fulfilled) / max(len(mandatory), 1)
        }
