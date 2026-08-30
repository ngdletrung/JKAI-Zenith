# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — VERSIONED TOOL REGISTRY & GOVERNANCE v2.0        ║
║   Single Source of Truth cho Tool Metadata, Risk & Permissions   ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, List


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
    """Kho lưu trữ metadata của các Tool được phép thi hành (Versioned Tool Registry)."""
    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    def register(self, tool: ToolDefinition) -> None:
        key = f"{tool.name}@{tool.version}"
        self._tools[key] = tool
        # Default route to latest if requested without version
        self._tools[tool.name] = tool 

    def unregister(self, name: str) -> bool:
        existed = name in self._tools
        self._tools.pop(name, None)
        to_del = [k for k in self._tools if k.startswith(f"{name}@")]
        for k in to_del:
            self._tools.pop(k, None)
        return existed

    def resolve(self, name: str, version: Optional[str] = None) -> Optional[ToolDefinition]:
        if version:
            return self._tools.get(f"{name}@{version}")
        return self._tools.get(name)

    def list_tools(self, filter_risk: Optional[RiskLevel] = None) -> List[ToolDefinition]:
        unique = {v.name: v for k, v in self._tools.items() if "@" in k or k == v.name}
        tools = list(unique.values())
        if filter_risk:
            tools = [t for t in tools if t.risk == filter_risk]
        return tools

    def has_permission(self, tool_name: str, permission: str) -> bool:
        tool = self.resolve(tool_name)
        if not tool:
            return False
        return permission in tool.permissions


tool_registry = ToolRegistry.get_instance()
