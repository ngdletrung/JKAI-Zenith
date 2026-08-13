"""
core/os/cognition/escl/capability_brain.py
Capability Brain (HAVE?) — Runtime Introspection, Capability Registry & Gap Detection.

Answers with mathematical certainty:
"What capabilities does JKAI actually have in its runtime environment to fulfill this mission?"
"""

from __future__ import annotations
import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec
from core.os.cognition.escl.tool_contract_registry import tool_contract_registry


@dataclass
class CapabilityAssessment:
    """Result of matching Canonical Mission against Runtime Capabilities."""
    is_executable: bool
    executability_score: float
    matched_capabilities: List[str] = field(default_factory=list)
    capability_gaps: List[str] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    block_reason: Optional[str] = None


class RuntimeCapabilityRegistry:
    """Introspects and caches all active runtime capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, bool] = {}
        self._inspect_runtime()

    def _inspect_runtime(self):
        # 1. Inspect Python Libraries
        self._capabilities["LIB_OPENPYXL"] = (importlib.util.find_spec("openpyxl") is not None)
        self._capabilities["LIB_DOCX"] = (importlib.util.find_spec("docx") is not None)
        self._capabilities["LIB_REPORTLAB"] = (importlib.util.find_spec("reportlab") is not None)
        self._capabilities["LIB_PANDAS"] = (importlib.util.find_spec("pandas") is not None)
        self._capabilities["LIB_REQUESTS"] = (importlib.util.find_spec("requests") is not None)

        # 2. Inspect Specific Engine Features
        self._capabilities["FEATURE_EXCEL_CHARTS"] = self._capabilities["LIB_OPENPYXL"]
        self._capabilities["FEATURE_EXCEL_FORMULAS"] = self._capabilities["LIB_OPENPYXL"]
        self._capabilities["FEATURE_WORD_TABLES"] = self._capabilities["LIB_DOCX"]
        self._capabilities["FEATURE_PDF_CANVAS"] = self._capabilities["LIB_REPORTLAB"]
        self._capabilities["FEATURE_PYTHON_SANDBOX"] = True
        self._capabilities["FEATURE_DISK_WRITE"] = os.access("d:/Docker/JKAI/files", os.W_OK) if os.path.exists("d:/Docker/JKAI/files") else True

    def has_capability(self, capability_name: str) -> bool:
        return self._capabilities.get(capability_name, False)

    def get_all_capabilities(self) -> Dict[str, bool]:
        return dict(self._capabilities)


class CapabilityBrain:
    """Matches mission requirements against verified runtime capabilities."""

    def __init__(self, registry: Optional[RuntimeCapabilityRegistry] = None):
        self.registry = registry or RuntimeCapabilityRegistry()

    def evaluate_mission_executability(self, spec: CanonicalMissionSpec) -> CapabilityAssessment:
        matched: List[str] = []
        gaps: List[str] = []
        tools: List[str] = []

        # 1. Check Artifact Engine
        if spec.artifact_type == "XLSX":
            if self.registry.has_capability("LIB_OPENPYXL"):
                matched.append("XLSX_ENGINE_OPENPYXL")
                tools.append("OFFICE_SUITE_MASTER")
            else:
                gaps.append("MISSING_XLSX_ENGINE (openpyxl not installed)")

            if spec.chart_required:
                if self.registry.has_capability("FEATURE_EXCEL_CHARTS"):
                    matched.append("EXCEL_CHART_SYNTHESIS")
                else:
                    gaps.append("MISSING_CHART_ENGINE")

            if spec.formulas_required:
                if self.registry.has_capability("FEATURE_EXCEL_FORMULAS"):
                    matched.append("EXCEL_FORMULA_SYNTHESIS")
                else:
                    gaps.append("MISSING_FORMULA_ENGINE")

        elif spec.artifact_type == "DOCX":
            if self.registry.has_capability("LIB_DOCX"):
                matched.append("DOCX_ENGINE_PYTHON_DOCX")
                tools.append("OFFICE_SUITE_MASTER")
            else:
                gaps.append("MISSING_DOCX_ENGINE (python-docx not installed)")

        elif spec.artifact_type == "PDF":
            if self.registry.has_capability("LIB_REPORTLAB"):
                matched.append("PDF_ENGINE_REPORTLAB")
                tools.append("OFFICE_SUITE_MASTER")
            else:
                gaps.append("MISSING_PDF_ENGINE (reportlab not installed)")

        elif spec.artifact_type == "PY":
            if self.registry.has_capability("FEATURE_PYTHON_SANDBOX"):
                matched.append("PYTHON_SANDBOX_RUNNER")
                tools.append("PYTHON_SANDBOX_RUNNER")
            else:
                gaps.append("MISSING_PYTHON_SANDBOX")

        elif spec.artifact_type == "3D_GAME_ENGINE":
            gaps.append("UNSUPPORTED_3D_WEBGL_ENGINE (Unity/Unreal/WebGL runtime not supported)")

        # 2. Check Exotic Unsupported Requirements (e.g. 3d, webgl, game)
        if any("3d" in p or "webgl" in p or "game" in p for p in spec.purposes):
            if "UNSUPPORTED_3D_GAME_ENGINE" not in str(gaps):
                gaps.append("UNSUPPORTED_3D_WEBGL_CAPABILITY")

        # 3. Calculate Executability Formula
        total_checks = len(matched) + len(gaps)
        score = len(matched) / max(total_checks, 1)
        is_executable = (len(gaps) == 0 and len(matched) > 0)

        block_reason = None
        if not is_executable:
            block_reason = f"CAPABILITY_GAP_DETECTED: {'; '.join(gaps)}"

        return CapabilityAssessment(
            is_executable=is_executable,
            executability_score=score,
            matched_capabilities=matched,
            capability_gaps=gaps,
            recommended_tools=list(set(tools)),
            block_reason=block_reason
        )


capability_brain = CapabilityBrain()
