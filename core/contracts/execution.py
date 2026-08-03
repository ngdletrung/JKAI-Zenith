"""
JKAI ZENITH — CONTRACT KERNEL: EXECUTION & GOVERNOR DECISION
File: core/contracts/execution.py

Contracts for ExecutionProfile, ExecutionIntent, ExecutionResult, and GovernorDecision.
Pure semantic contracts without runtime-specific parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid
from core.contracts.resource import ResourceIntent


@dataclass
class ExecutionIntent:
    """Semantic intent of an execution request before profile resolution."""
    task_id: str
    role_name: str
    quality_target: str = "medium"
    latency_target: str = "medium"


@dataclass
class ExecutionProfile:
    """
    Governance -> Runtime contract.
    Semantic execution ABI produced by AMG PortfolioGovernor.
    Pure semantic contract — runtime adapters convert this into specific payload flags.
    """
    model_name: str
    role_name: str
    backend: str = "GPU"                 # "GPU" | "HYBRID" | "CPU"
    memory_layout: str = "VRAM_ONLY"     # "VRAM_ONLY" | "VRAM_RAM_SPLIT" | "RAM_ONLY"
    num_gpu_layers: int = 32
    num_predict: int = 512
    num_ctx: int = 4096
    num_thread: int = 20
    temperature: float = 0.2
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    use_mmap: bool = True
    keep_alive: str = "-1"
    raw_options: Dict[str, Any] = field(default_factory=dict)
    resolved_via: str = "explicit"       # "explicit" | "auto" | "scoring" | "emergency_fallback"

    def to_ollama_options(self) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "num_gpu":      self.num_gpu_layers,
            "num_predict":  self.num_predict,
            "num_ctx":      self.num_ctx,
            "temperature":  self.temperature,
            "top_p":        self.top_p,
            "repeat_penalty": self.repeat_penalty,
            "use_mmap":     self.use_mmap,
        }
        if self.num_thread:
            opts["num_thread"] = self.num_thread
        opts.update(self.raw_options)
        return {k: v for k, v in opts.items() if v is not None}

    def to_ollama_payload(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "options": self.to_ollama_options(),
            "stream": stream,
            "keep_alive": self.keep_alive,
        }
        if messages is not None:
            payload["messages"] = messages
        return payload


@dataclass
class GovernorDecision:
    """
    Governance Decision Contract.
    Encapsulates selected model, execution profile, resource intent, and decision rationale
    for auditability, explainability, and replay.
    """
    selected_model: str
    selected_runtime: str = "ollama"
    execution_profile: Optional[ExecutionProfile] = None
    resource_intent: Optional[ResourceIntent] = None
    fallback_chain: List[str] = field(default_factory=list)
    confidence: float = 1.0
    rationale: str = ""
    decision_trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class ExecutionResult:
    """Result of an execution request."""
    status_code: int = 200
    content: str = ""
    model_used: str = ""
    latency_ms: float = 0.0
    tokens_generated: int = 0
    error: Optional[str] = None
