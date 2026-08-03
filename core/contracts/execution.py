"""
JKAI ZENITH — CONTRACT KERNEL: EXECUTION INTENT, LEASE & GOVERNOR DECISION
File: core/contracts/execution.py

Pure semantic execution ABI contracts (ExecutionIntent, ExecutionLease, GovernorDecision, ExecutionResult).
Zero hardware flags (no gpu_layers, no vram_mb, no num_threads).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import uuid
from core.contracts.resource import ResourceIntent, ResourceAllocation


@dataclass
class ExecutionProfile:
    """Legacy profile compatibility shim."""
    model_name: str = "default_model"
    role_name: str = "PLANNER"
    context_window: int = 4096
    num_ctx: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9



@dataclass
class ExecutionIntent:
    """
    Pure semantic execution requirement from Cognitive Kernel & Governance.
    Describes WHAT execution quality/reasoning budget is required.
    """
    model_ref: str = "auto"
    role_name: str = "PLANNER"
    quality_target: str = "medium"      # "low" | "medium" | "high" | "highest"
    reasoning_budget: str = "medium"    # "low" | "medium" | "high"
    context_budget: int = 16384
    output_budget: int = 4096
    latency_target: str = "medium"      # "ultra_low" | "low" | "medium" | "relaxed"
    generation_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionLease:
    """
    Execution Lease granted by Governance to Runtime.
    Runtime MUST execute strictly within the bounds of the granted lease.
    """
    lease_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mission_id: str = ""
    task_id: str = ""
    execution_intent: ExecutionIntent = field(default_factory=ExecutionIntent)
    resource_allocation: Optional[ResourceAllocation] = None
    authority_scope: List[str] = field(default_factory=lambda: ["read", "write_draft"])
    budget_seconds: float = 60.0
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)


@dataclass
class GovernorDecision:
    """Comprehensive decision artifact emitted by Governance."""
    selected_model: str
    selected_runtime: str
    execution_profile: ExecutionProfile
    resource_intent: ResourceIntent
    decision_trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    policy_version: str = "v20.5"
    registry_version: str = "v1.0"
    selection_score: float = 0.95
    alternatives_considered: List[str] = field(default_factory=list)
    fallback_chain: List[str] = field(default_factory=list)
    rationale: str = "Metadata-driven dynamic capability scoring"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionResult:
    """Execution result returned from RuntimeAdapter."""
    status_code: int = 200
    content: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    model_name: str = ""
    backend: str = "ollama"
    metadata: Dict[str, Any] = field(default_factory=dict)
