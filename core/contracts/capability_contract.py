"""
JKAI ZENITH — KERNEL CONTRACT: CAPABILITY REQUIREMENT & EXECUTION PROFILE (v2.1)
File: core/contracts/capability_contract.py

Cầu nối giữa Planner ↔ Capability Broker ↔ AMG v2 Model Governor.
Planner phát CapabilityRequirement (không tự chọn tool hay model cụ thể).
CapabilityBroker và AMG v2 giải quyết thành ExecutionProfile.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class CapabilityRequirement:
    """
    Yêu cầu năng lực do Planner phát ra.
    Chưa bị bind cứng vào bất kỳ Tool hay LLM Model name nào.
    """
    capability: str                              # "spreadsheet_mutation", "web_search", "code_execution"
    complexity: str = "medium"                   # "low", "medium", "high", "extreme"
    latency: str = "normal"                      # "ultra_low", "normal", "batch"
    reasoning_depth: str = "moderate"            # "none", "moderate", "deep"
    verification_required: bool = True
    hardware_preference: Optional[str] = None    # "GPU", "CPU", None


@dataclass(frozen=True)
class ExecutionProfile:
    """
    Hồ sơ thực thi hoàn chỉnh do CapabilityBroker ↔ AMG v2 giải quyết từ CapabilityRequirement.
    """
    capability_name: str
    selected_tool: Optional[str]                 # "openpyxl", "tavily_search", "python_interpreter"
    selected_model_name: Optional[str]           # "qwen3.5:4b", "llama3.2:3b"
    selected_endpoint_url: Optional[str]         # "http://127.0.0.1:11434"
    max_context_length: int = 8192
    timeout_seconds: int = 120
    is_sandboxed: bool = True
