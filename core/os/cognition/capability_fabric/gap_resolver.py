"""
core/os/cognition/capability_fabric/gap_resolver.py
Capability Gap Resolver & Dynamic Composition Engine.

Detects capability gaps and composes available primitives to satisfy requirements.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from core.os.cognition.capability_fabric.models import (
    CapabilityComposition,
    CapabilityGap,
    CapabilitySpec,
)
from core.os.cognition.capability_fabric.capability_registry import capability_registry


class CapabilityGapResolver:
    """Detects capability gaps against mission requirements and attempts composition."""

    def analyze_requirements(
        self,
        required_actions: List[str],
    ) -> Tuple[List[CapabilitySpec], List[CapabilityGap]]:
        """Matches required actions to capabilities and flags any unfulfilled gaps."""
        matched_caps: Dict[str, CapabilitySpec] = {}
        gaps: List[CapabilityGap] = []

        for act in required_actions:
            candidates = capability_registry.find_by_action(act)
            if candidates:
                for c in candidates:
                    matched_caps[c.capability_id] = c
            else:
                # Action not directly provided by a registered tool
                # Check if resolvable by python scripting composition
                can_compose = act.startswith("xlsx.") or act.startswith("calc.") or act.startswith("transform.") or act in ["charts", "formulas", "progress_bar"]
                plan = ["system.python_execute", "openpyxl"] if can_compose else None

                gaps.append(CapabilityGap(
                    requirement_id=f"req_{act}",
                    missing_capability=act,
                    reason=f"No direct registered tool advertises atomic action '{act}'.",
                    resolvable_by_composition=can_compose,
                    composition_plan=plan
                ))

        return list(matched_caps.values()), gaps

    def compose_solution(self, gap: CapabilityGap) -> Optional[CapabilityComposition]:
        """Synthesizes a composition recipe to fill a capability gap."""
        if not gap.resolvable_by_composition:
            return None

        if "chart" in gap.missing_capability:
            return CapabilityComposition(
                target_capability=gap.missing_capability,
                primitive_capabilities=["system.python_execute", "xlsx.create_and_chart"],
                composition_strategy="PYTHON_OPENPYXL_SCRIPT_GENERATION",
                generated_code_template="""
import openpyxl
from openpyxl.chart import BarChart, Reference
wb = openpyxl.load_workbook(file_path)
ws = wb.active
chart = BarChart()
chart.title = "Progress Tracking"
data = Reference(ws, min_col=2, min_row=1, max_row=6)
chart.add_data(data, titles_from_data=True)
ws.add_chart(chart, "E2")
wb.save(file_path)
"""
            )
        return None


capability_gap_resolver = CapabilityGapResolver()
