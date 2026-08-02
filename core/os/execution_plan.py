# [ZENITH FILE DIRECTIVE]
# - File: core/os/execution_plan.py
# - Role: Execution Plan representation v1
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0 (Integrated)

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ExecutionPlanStep(BaseModel):
    step_id: str
    description: str
    assigned_agent: str = "general"  # e.g. workspace, web, database, critic
    required_tools: List[str] = Field(default_factory=list)
    status: str = "pending"          # pending, running, completed, failed

class ExecutionPlan(BaseModel):
    selected_pipeline: str = "fast"  # fast, deep
    estimated_cost: float = 0.0
    confidence_score: float = 1.0
    is_provisional: bool = False
    steps: List[ExecutionPlanStep] = Field(default_factory=list)
    reasoning_route: str = ""        # Giải trình ngắn của Planner về phán quyết định tuyến
