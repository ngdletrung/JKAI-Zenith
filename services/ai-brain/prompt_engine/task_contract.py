# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/prompt_engine/task_contract.py
# - Role: Task Contract Definition & Decision Authority Validation
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.1 (Cognitive Execution Contract)
#
# [WORKING PRINCIPLES]:
# 1. Decision Authority: Explicitly scopes file modifications, deletion, messaging.
# 2. Completion Status: Defines required criteria and evidence checklist.
# -----------------------------------------------------------------------------

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DecisionAuthority(BaseModel):
    can_modify_files: bool = True
    can_delete_files: bool = False
    can_send_external_message: bool = False


class CompletionStatus(BaseModel):
    required: List[str] = Field(default_factory=list)
    validated_evidence: List[str] = Field(default_factory=list)


class TaskContract(BaseModel):
    objective: str = ""
    constraints: List[str] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    risk_level: float = 0.0
    required_evidence: List[str] = Field(default_factory=list)
    decision_authority: DecisionAuthority = Field(default_factory=DecisionAuthority)
    completion_status: CompletionStatus = Field(default_factory=CompletionStatus)
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
            f"  <decision_authority>{json.dumps(self.decision_authority.model_dump(), ensure_ascii=False)}</decision_authority>\n"
            f"  <completion_status>{json.dumps(self.completion_status.model_dump(), ensure_ascii=False)}</completion_status>\n"
            "</task_contract>"
        )
