"""
CriticResult — Pydantic version of the raw CRITIC_SCHEMA dict.
"""

from pydantic import BaseModel, Field


class CriticResult(BaseModel):
    thought: str = Field("", description="Internal reasoning process for the critique")
    approved: bool = Field(..., description="Whether the plan is approved")
    feedback: str = Field("", description="Constructive feedback or modification requests")
    needs_nuclear_key: bool = Field(
        False,
        description="True if the plan requires Master's explicit approval decree",
    )
