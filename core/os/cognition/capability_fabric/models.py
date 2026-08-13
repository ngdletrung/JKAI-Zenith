"""
core/os/cognition/capability_fabric/models.py
Capability Fabric — Capability Registry, Graph, Gap Detection, and Composition Models.

Transforms JKAI from a Tool-based agent into a Capability-based Autonomous Agent.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class CapabilityCategory(str, Enum):
    DOCUMENT_OFFICE = "DOCUMENT_OFFICE"
    CODE_MANIPULATION = "CODE_MANIPULATION"
    FILESYSTEM = "FILESYSTEM"
    RESEARCH_RETRIEVAL = "RESEARCH_RETRIEVAL"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    SYSTEM_AUTOMATION = "SYSTEM_AUTOMATION"


@dataclass
class CapabilitySpec:
    """Explicit declaration of what a capability can, cannot, requires, produces, and how it is verified."""
    capability_id: str
    name: str
    category: CapabilityCategory
    can_do: List[str]                  # List of atomic actions it can perform
    cannot_do: List[str]               # Explicit boundaries (what it CANNOT do)
    requires_prerequisites: List[str]  # Tools, runtime, libraries required (e.g. ['python', 'openpyxl'])
    produces_artifacts: List[str]      # File types / artifacts produced (e.g. ['xlsx'])
    verification_methods: List[str]    # Verification probes (e.g. ['openpyxl_chart_check', 'file_exists'])
    primary_tool: str                  # Default tool binding
    fallback_tool: Optional[str] = None


@dataclass
class CapabilityGap:
    """Represents a missing capability required by a mission requirement."""
    requirement_id: str
    missing_capability: str
    reason: str
    resolvable_by_composition: bool = False
    composition_plan: Optional[List[str]] = None


@dataclass
class CapabilityComposition:
    """Recipe to synthesize a missing high-level capability from existing low-level primitives."""
    target_capability: str
    primitive_capabilities: List[str]
    composition_strategy: str          # e.g. "PYTHON_SCRIPT_GENERATION"
    generated_code_template: Optional[str] = None
