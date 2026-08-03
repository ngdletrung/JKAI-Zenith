"""
JKAI ZENITH — CONTRACT KERNEL: RESOURCE
File: core/contracts/resource.py

Contracts for ResourceIntent and ResourceAllocation.
Separates abstract resource intent (Governance) from concrete resource allocation (Infrastructure).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BackendType(str, Enum):
    GPU = "GPU"
    CPU = "CPU"
    HYBRID = "HYBRID"


@dataclass
class ResourceIntent:
    """Governance -> ResourceGovernor abstract resource intent."""
    compute_class: str = "BALANCED"      # "FAST" | "BALANCED" | "HEAVY"
    acceleration: str = "PREFERRED_GPU"  # "PREFERRED_GPU" | "HYBRID_ALLOWED" | "CPU_ALLOWED"
    memory_class: str = "MEDIUM"         # "LOW" | "MEDIUM" | "HIGH"
    latency_target: str = "MEDIUM"       # "LOW" | "MEDIUM" | "HIGH"


@dataclass
class ResourceAllocation:
    """ResourceGovernor -> HardwareScheduler concrete allocation contract."""
    backend: BackendType = BackendType.GPU
    gpu_memory_mb: float = 0.0
    ram_memory_mb: float = 0.0
    gpu_layers: int = 32
    concurrency: int = 1

    @property
    def is_gpu_bound(self) -> bool:
        return self.backend in (BackendType.GPU, BackendType.HYBRID) or self.gpu_layers > 0

    @property
    def is_cpu_bound(self) -> bool:
        return self.backend == BackendType.CPU and self.gpu_layers == 0


# ResourceRequest alias for backward compatibility with M0b/M4
ResourceRequest = ResourceAllocation
