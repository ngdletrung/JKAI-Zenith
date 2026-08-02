"""
Planner schemas — tương thích với services/ai-brain/planner.py.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HardwareTarget(str, Enum):
    ALPHA = "ALPHA"
    BETA = "BETA"


class PlanStep(BaseModel):
    id: str = Field(..., description="Unique step ID — e.g. 'step_01'")
    tool: str = Field(..., description="Exact skill ID from registry. NEVER invent.")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments matching skill signature")
    description: str = Field(..., description="One-line plain-language summary")
    assigned_agent: str = Field(..., description="Agent Soul .md file, e.g. agent_executor_alpha.md")
    hardware_target: HardwareTarget = Field(..., description="ALPHA=GPU reasoning | BETA=CPU I/O")
    expert_mindset: str = Field(..., description="Elite execution instruction for the agent")
    verification: str = Field(..., description="Concrete, testable success criterion")
    parallel: bool = Field(False, description="True if independent of all other steps")
    depends_on: List[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    fallback_tool: Optional[str] = Field(None, description="Backup skill if primary fails")


class Blueprint(BaseModel):
    thought: str = Field("", description="MECE chain-of-thought before generating steps")
    optimization_review: str = Field("", description="Self-Critique BEFORE writing steps")
    steps: List[PlanStep] = Field(..., description="Ordered, parallelised execution steps")
    rationale: str = Field("", description="Strategic rationale for this approach")
    failure_speculation: str = Field("", description="Failure modes and pivot strategies")
    ambiguous: bool = Field(False, description="True if goal requires clarification")
    question: Optional[str] = Field(None, description="Clarification question when ambiguous=True")
    complexity_score: int = Field(1, ge=1, le=10, description="Task complexity 1-10")
    team_pattern: str = Field("pipeline", description="pipeline|fan_out_fan_in|expert_pool|producer_reviewer|supervisor|hierarchical_delegation")
    recommended_critic: bool = Field(False, description="True when producer_reviewer pattern")
