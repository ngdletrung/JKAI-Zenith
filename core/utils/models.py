from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field as dc_field



class ModelOptions(BaseModel):
    num_ctx: Optional[int] = None
    num_gpu: Optional[int] = None
    temperature: Optional[float] = None
    repeat_penalty: Optional[float] = None
    top_p: float = 0.9
    top_k: int = 40


class NeuralProfile(BaseModel):
    num_ctx: int = 4096
    num_gpu: int = 0
    temperature: float = 0.7
    repeat_penalty: float = 1.1


class RoleConfig(BaseModel):
    model: str
    options: ModelOptions = Field(default_factory=ModelOptions)
    keep_alive: str = "5m"
    hardware: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "options": self.options.model_dump(exclude_none=True),
            "keep_alive": self.keep_alive,
            "hardware": self.hardware,
        }


class SkillInput(BaseModel):
    """Typed contract cho tool input."""
    task_id: Optional[str] = None
    goal: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)


class SkillOutput(BaseModel):
    """Typed contract cho tool output."""
    output: str = ""
    status: str = "success"
    error: Optional[str] = None
    attachments: Optional[list] = None


class TaskBudget(BaseModel):
    """Cost Governor: ngân sách cho mỗi task."""
    max_retries: int = 3
    max_local_tokens: int = 50000
    max_cloud_calls: int = 2
    max_cloud_cost_usd: float = 0.20
    max_total_duration_sec: float = 300.0


class BudgetLedger(BaseModel):
    """Sổ cái theo dõi chi tiêu cho một task."""
    task_id: str
    local_tokens_used: int = 0
    cloud_calls_made: int = 0
    estimated_cost_usd: float = 0.0
    retries_used: int = 0
    exceeded: bool = False


class Permission(str, Enum):
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    FILESYSTEM_DELETE = "filesystem:delete"
    SHELL_EXEC = "shell:exec"
    NETWORK_HTTP = "network:http"
    DOCKER_MANAGE = "docker:manage"
    DOCKER_INSPECT = "docker:inspect"
    REDIS_ACCESS = "redis:access"
    LLM_CALL = "llm:call"
    SKILL_MANAGE = "skill:manage"
    SOVEREIGN = "sovereign:all"


SKILL_CATEGORY_PERMISSIONS: Dict[str, list[Permission]] = {
    "CORE": [Permission.SOVEREIGN],
    "SECURITY": [Permission.FILESYSTEM_READ, Permission.FILESYSTEM_WRITE, Permission.SHELL_EXEC, Permission.NETWORK_HTTP, Permission.DOCKER_INSPECT],
    "DEVOPS": [Permission.FILESYSTEM_READ, Permission.FILESYSTEM_WRITE, Permission.SHELL_EXEC, Permission.DOCKER_INSPECT, Permission.DOCKER_MANAGE, Permission.NETWORK_HTTP],
    "CODING": [Permission.FILESYSTEM_READ, Permission.FILESYSTEM_WRITE, Permission.LLM_CALL],
    "RESEARCH": [Permission.FILESYSTEM_READ, Permission.NETWORK_HTTP, Permission.LLM_CALL],
    "DATA_SCIENCE": [Permission.FILESYSTEM_READ, Permission.NETWORK_HTTP, Permission.LLM_CALL],
    "BUSINESS": [Permission.FILESYSTEM_READ, Permission.LLM_CALL],
    "COMMANDS": [Permission.SHELL_EXEC, Permission.FILESYSTEM_READ],
}


# ---------------------------------------------------------------------------
# Resource Contract — M4: HardwareScheduler ResourceRequest API
# ---------------------------------------------------------------------------

class BackendType(str, Enum):
    """
    Compute backend for a task execution.
    Replaces the raw string "GPU" / "CPU" / "HYBRID" previously passed
    to HardwareScheduler.acquire_gpu_lock(model_name, model_size_gb).

    This enum is the single authority on backend naming across:
        ExecutionProfile.backend → ResourceRequest.backend → HardwareScheduler.acquire()
    """
    GPU    = "GPU"     # All layers on GPU VRAM
    CPU    = "CPU"     # All layers in RAM (no GPU)
    HYBRID = "HYBRID"  # Layers split: N on GPU, rest in RAM


@dataclass
class ResourceRequest:
    """
    Hardware resource contract produced by ExecutionProfile.to_resource_request().
    Consumed by HardwareScheduler.acquire(task_id, resource_request).

    Design invariant:
        HardwareScheduler must NEVER inspect model_name.
        It only sees: backend, gpu_memory_mb, ram_memory_mb, gpu_layers, concurrency.

    Usage:
        profile = amg.resolve(role="PLANNER", ...)
        req = profile.to_resource_request()
        acquired = await scheduler.acquire(task_id, req)

    Field semantics:
        gpu_memory_mb : VRAM reservation in MiB (0 for CPU-only)
        ram_memory_mb : RAM reservation in MiB (can be 0 if pure GPU)
        gpu_layers    : Expected GPU layer count (informational for scheduling)
        concurrency   : Number of parallel decode slots this execution occupies
    """
    backend: BackendType = BackendType.CPU
    gpu_memory_mb: float = 0.0          # VRAM footprint in MiB
    ram_memory_mb: float = 0.0          # RAM footprint in MiB
    gpu_layers: int = 0                  # GPU layer count (informational)
    concurrency: int = 1                 # Parallel request slots needed

    def __post_init__(self):
        # Validate backend enum (allow string construction)
        if isinstance(self.backend, str):
            self.backend = BackendType(self.backend.upper())

    @property
    def is_gpu_bound(self) -> bool:
        return self.backend in (BackendType.GPU, BackendType.HYBRID) and self.gpu_memory_mb > 0

    @property
    def is_cpu_bound(self) -> bool:
        return self.backend == BackendType.CPU

    def __repr__(self) -> str:
        return (
            f"ResourceRequest(backend={self.backend.value}, "
            f"gpu={self.gpu_memory_mb:.0f}MB, ram={self.ram_memory_mb:.0f}MB, "
            f"layers={self.gpu_layers}, concurrency={self.concurrency})"
        )

