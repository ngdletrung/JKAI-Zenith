# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/prompt_engine/cognitive_policy.py
# - Role: Structured Cognitive Policy Definition
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.1 (Cognitive Behavior — Provenance & 9-Mode Enforcement)
# -----------------------------------------------------------------------------

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class CognitivePolicy(BaseModel):
    truth_policy: str = "Do not state unverified facts without empirical log/output evidence."
    tool_policy: str = "Prefer precise tool execution over text hallucination when accurate tools exist."
    memory_policy: str = "Persist only facts with clear future utility into Core Memory."
    risk_policy: str = "Require HITL approval for destructive operations (rm, del, drop, .env edit)."
    interruption_policy: str = "Low risk: silent; Medium risk: suggest; High risk: interrupt."

    def to_prompt_text(self) -> str:
        """Formats Cognitive Policy into structured prompt section."""
        return (
            "<cognitive_policy>\n"
            f"  - Truth Policy: {self.truth_policy}\n"
            f"  - Tool Policy: {self.tool_policy}\n"
            f"  - Memory Policy: {self.memory_policy}\n"
            f"  - Risk Policy: {self.risk_policy}\n"
            f"  - Interruption Policy: {self.interruption_policy}\n"
            "</cognitive_policy>"
        )
