"""
core/os/cognition/escl/contracts.py
Execution Semantic Contract Layer (ESCL) — Canonical Data Models & Lifecycle Contracts.

Adheres to:
- E0: Semantic Requirement Compiler & Lifecycle Tracking
- E1: Tool Contract Registry (Typed Input/Output/Verification Schemas)
- E2: Canonical Action Schema
- E3: Prompt Contract Specification
- E4: Hardened Lexical Parser & Quarantine
- E5: Semantic Continuity Ledger across 11 Links
- E6: Artifact Semantic Verification (Zero False Success)
- E7: Execution Outcome Normalizer
"""

from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RequirementCategory(str, Enum):
    ARTIFACT_FORMAT = "ARTIFACT_FORMAT"
    ENTITY_COUNT = "ENTITY_COUNT"
    DATA_STRUCTURE = "DATA_STRUCTURE"
    VISUALIZATION = "VISUALIZATION"
    FORMULA = "FORMULA"
    STYLING = "STYLING"
    CONTENT_THEME = "CONTENT_THEME"


class RequirementLifecycleStage(str, Enum):
    EXTRACTED = "EXTRACTED"
    PLANNED = "PLANNED"
    PROMPTED = "PROMPTED"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    CANONICAL_ACTION = "CANONICAL_ACTION"
    TOOL_INVOCATION = "TOOL_INVOCATION"
    ARTIFACT_PRODUCED = "ARTIFACT_PRODUCED"
    VERIFIED = "VERIFIED"
    DROPPED = "DROPPED"


@dataclass
class SemanticRequirement:
    """Individual atomic requirement with lifecycle traceability across all 11 stages."""
    req_id: str
    category: RequirementCategory
    description: str
    expected_value: Any
    is_mandatory: bool = True
    current_stage: RequirementLifecycleStage = RequirementLifecycleStage.EXTRACTED
    fulfilled: bool = False
    evidence_details: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def advance_stage(self, new_stage: RequirementLifecycleStage, details: Optional[str] = None):
        self.current_stage = new_stage
        if details:
            self.evidence_details = details


@dataclass
class CanonicalAction:
    """Canonical action proposal before tool execution."""
    action_id: str
    action_type: str # CREATE_ARTIFACT, MUTATE_CODE, EXECUTE_SCRIPT, QUERY_WEB
    target_artifact_type: Optional[str]
    parameters: Dict[str, Any]
    bound_requirements: List[str] = field(default_factory=list) # List of req_ids
    quarantine: bool = False
    quarantine_reason: Optional[str] = None


@dataclass
class ToolContract:
    """Authoritative contract for a tool."""
    tool_id: str
    version: str
    domain: str
    purpose: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_capabilities: Set[str]
    side_effects: bool
    idempotent: bool
    verification_rules: List[str] = field(default_factory=list)


@dataclass
class PromptContract:
    """Versioned Prompt Contract defining system instruction and strict output schema."""
    prompt_id: str
    version: str
    role: str
    expected_output_format: str # JSON_ACTION, CODE_BLOCK, RAW_TEXT
    allowed_actions: List[str] = field(default_factory=list)
    forbidden_behaviors: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    system_instruction: str = ""


@dataclass
class NormalizedExecutionOutcome:
    """E7: Normalized outcome after raw tool execution."""
    execution_id: str
    tool_id: str
    status: str # SUCCEEDED, FAILED, NEED_INFO, QUARANTINED
    artifact_paths: List[str] = field(default_factory=list)
    produced_requirements: List[str] = field(default_factory=list)
    unresolved_requirements: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    context_hash: str = ""
    timestamp: float = field(default_factory=time.time)
