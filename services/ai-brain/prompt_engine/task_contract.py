# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/prompt_engine/task_contract.py
# - Role: Task Contract Definition & Validation
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.0 (Cognitive Context Compiler Layer)
#
# [WORKING PRINCIPLES]:
# 1. Deterministic Contract: Compiles objectives, constraints, forbidden actions.
# 2. Risk & Evidence: Defines risk levels and required evidence.
# -----------------------------------------------------------------------------

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TaskContract(BaseModel):
    objective: str = ""
    constraints: List[str] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    risk_level: float = 0.0
    required_evidence: List[str] = Field(default_factory=list)
    output_contract: Dict[str, Any] = Field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Formats Task Contract into structured prompt section."""
        return (
            "<task_contract>\n"
            f"  <objective>{self.objective}</objective>\n"
            f"  <constraints>{json.dumps(self.constraints, ensure_ascii=False)}</constraints>\n"
            f"  <forbidden_actions>{json.dumps(self.forbidden_actions, ensure_ascii=False)}</forbidden_actions>\n"
            f"  <success_criteria>{json.dumps(self.success_criteria, ensure_ascii=False)}</success_criteria>\n"
            f"  <risk_level>{self.risk_level}</risk_level>\n"
            "</task_contract>"
        )
