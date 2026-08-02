# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/schema.py
# - Role: Strongly-typed Pydantic schemas for state partitions & events
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class MissionMetadata(BaseModel):
    """Immutable Mission metadata set at initialization."""
    mission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_goal: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    initial_constraints: List[str] = Field(default_factory=list)
    model_profile: str = "default"

class FactItem(BaseModel):
    content: str
    dependencies: List[str] = Field(default_factory=list) # IDs of other facts it relies on
    confidence: float = 1.0
    valid: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MissionFacts(BaseModel):
    """Mutable fact storage supporting Truth Maintenance System."""
    facts_db: Dict[str, FactItem] = Field(default_factory=dict)

class MissionPlanner(BaseModel):
    """State tracking for planning steps."""
    current_plan: List[str] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    blocked_by: Optional[str] = None
    step_confidence: Dict[str, float] = Field(default_factory=dict)

class MissionBudget(BaseModel):
    """Budget and usage constraints to prevent infinite loops."""
    max_cost_usd: float = 5.0
    current_cost_usd: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    api_calls_count: int = 0
    search_calls_count: int = 0
    tool_calls_count: int = 0

class ScopedMemory(BaseModel):
    """Memory subdivided into scopes."""
    global_memory: Dict[str, Any] = Field(default_factory=dict)
    mission_memory: Dict[str, Any] = Field(default_factory=dict)
    agent_memory: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # agent_name -> memory dict
    tool_memory: Dict[str, Any] = Field(default_factory=dict)

class CitationItem(BaseModel):
    source_path: str
    line_range: Optional[str] = None
    checksum: Optional[str] = None
    confidence: float = 1.0

class MissionReferences(BaseModel):
    """Source-of-truth grounding references and dependency graph."""
    citations: Dict[str, CitationItem] = Field(default_factory=dict) # ref_id -> citation
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict) # file -> list of downstream files impacted

class MissionState(BaseModel):
    """The complete Zeniths Unified Mission State (Composite)."""
    metadata: MissionMetadata
    facts: MissionFacts
    planner: MissionPlanner
    budget: MissionBudget
    memory: ScopedMemory
    references: MissionReferences
    lifecycle: str = "READY" # READY, RUNNING, WAITING, BLOCKED, SUCCESS, FAILED
    active_entity_stack: List[Dict[str, Any]] = Field(default_factory=list)

class MissionEvent(BaseModel):
    """Event schema for Event Sourcing."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    payload: Dict[str, Any]
