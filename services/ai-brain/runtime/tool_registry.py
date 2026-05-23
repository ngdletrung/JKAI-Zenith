from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExecutionMode(Enum):
    SYNC = "SYNC"
    ASYNC = "ASYNC"
    STREAM = "STREAM"
    BACKGROUND = "BACKGROUND"

@dataclass(frozen=True)
class ToolDefinition:
    """
    🛠️ Lõi Đăng Ký Công Cụ (Versioned Single Source of Truth)
    Chỉ những công cụ khai báo tại đây mới được phép tồn tại trong Runtime.
    """
    name: str
    version: str
    description: str
    risk: RiskLevel
    permissions: Tuple[str, ...]
    timeout: int
    schema: dict
    deterministic: bool
    side_effects: bool
    idempotent: bool
    max_retries: int
    allowed_sources: Tuple[str, ...]
    execution_mode: ExecutionMode

class ToolRegistry:
    """Kho lưu trữ metadata của các Tool được phép thi hành."""
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        key = f"{tool.name}@{tool.version}"
        self._tools[key] = tool
        # Default route to latest if requested without version
        self._tools[tool.name] = tool 

    def resolve(self, name: str, version: Optional[str] = None) -> Optional[ToolDefinition]:
        if version:
            return self._tools.get(f"{name}@{version}")
        return self._tools.get(name)
