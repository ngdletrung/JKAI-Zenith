"""
🏛️ JKAI ZENITH — RUNTIME ADAPTER ABSTRACTION (Layer 4)
File: core/runtime/base_adapter.py

Purpose:
    Abstract interface between ExecutionProfile (Layer 3 output) and
    any concrete model runtime (Ollama, llama.cpp, vLLM, MLX, etc.).

    JKAI's cognitive and governance layers never import Ollama, llama.cpp,
    or any runtime-specific library. They only produce ExecutionProfile,
    which is passed to a RuntimeAdapter implementation.

Architectural Invariant:
    Swapping runtimes (Ollama → vLLM, or Ollama → llama.cpp) requires:
    - Adding a new RuntimeAdapter implementation
    - Updating runtime registration
    - Zero changes to cognitive/governance layers
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any

# Deferred import to avoid circular dependency (model_capabilities → runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.governor.model_capabilities import ExecutionProfile


# ---------------------------------------------------------------------------
# Runtime Health & Model Info Contracts
# ---------------------------------------------------------------------------

@dataclass
class RuntimeModelInfo:
    """
    Minimal model metadata returned by a runtime adapter's inspect call.
    Used by ModelInspector — adapter-agnostic.
    """
    model_name: str
    model_info: Dict[str, Any] = field(default_factory=dict)   # architecture, params, etc.
    details: Dict[str, Any] = field(default_factory=dict)       # family, quantization
    capabilities: List[str] = field(default_factory=list)       # ["completion", "tools", "vision"]
    template: str = ""                                           # Chat template string
    digest: str = ""                                             # For cache invalidation
    size_gb: float = 0.0                                         # File size from manifest


@dataclass
class RuntimeHealth:
    """Health status of a runtime adapter."""
    is_alive: bool = False
    host: str = ""
    version: str = ""
    error: str = ""
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Abstract RuntimeAdapter
# ---------------------------------------------------------------------------

class RuntimeAdapter(ABC):
    """
    Abstract interface for a model execution runtime.

    All concrete runtimes (Ollama, llama.cpp, vLLM, MLX) must implement
    this interface. The JKAI engine speaks only this language.

    Contract:
        Input:  ExecutionProfile (model-agnostic, pre-computed by AMG)
        Output: str | AsyncIterator[str]
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        profile: "ExecutionProfile",
        task_id: str = "system",
    ) -> str:
        """
        Non-streaming generation.
        Returns the complete response string.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        profile: "ExecutionProfile",
        task_id: str = "system",
    ) -> AsyncIterator[str]:
        """
        Streaming generation.
        Yields text chunks as they are produced by the runtime.
        """
        ...

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        Returns list of available model names on this runtime.
        Used by ModelRegistry.discover().
        """
        ...

    @abstractmethod
    async def inspect_model(self, model_name: str) -> Optional[RuntimeModelInfo]:
        """
        Returns detailed metadata for a specific model.
        Used by ModelInspector.
        Returns None if model not found.
        """
        ...

    @abstractmethod
    async def health_check(self) -> RuntimeHealth:
        """
        Returns current health status of the runtime.
        Used by HardwareMonitor and PortfolioGovernor.
        """
        ...

    @property
    @abstractmethod
    def runtime_id(self) -> str:
        """
        Unique identifier for this runtime instance.
        Example: "ollama-gpu:11434", "ollama-cpu:11435", "llamacpp:8080"
        """
        ...

    @property
    @abstractmethod
    def supports_gpu(self) -> bool:
        """Whether this runtime instance has GPU access."""
        ...
