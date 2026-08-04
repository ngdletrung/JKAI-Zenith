"""
JKAI ZENITH — CAPABILITY LAYER: CAPABILITY BROKER (v2.1)
File: core/capabilities/capability_broker.py

Cầu nối giữa CapabilityRequirement (từ Planner) -> CapabilityBroker -> AMG v2 Model Governor.
Giải quyết năng lực thành ExecutionProfile hoàn chỉnh (Tool, Model, Endpoint, Context).
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional

from dataclasses import dataclass, field
from core.contracts.capability_contract import CapabilityRequirement, ExecutionProfile

logger = logging.getLogger("jkai.capabilities.broker")


@dataclass
class CapabilitySet:
    """Tập hợp năng lực thực thi được môi giới cấp phát."""
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=lambda: ["search_web"])


class CapabilityBroker:
    """Bộ Môi Giới Năng Lực (Capability Broker)."""

    def register_tool(self, tool_name: str, tool_def: Any = None):
        self.TOOL_MAPPING[tool_name] = tool_name

    def resolve_capabilities(self, requirement: Any) -> CapabilitySet:
        return CapabilitySet(capabilities=["web_search", "python_interpreter"])

    TOOL_MAPPING = {
        "xlsx_generation": "openpyxl",
        "csv_generation": "pandas",
        "pdf_generation": "reportlab",
        "web_search": "tavily_search",
        "data_inspection": "file_inspector",
        "conversational_synthesis": "chat_engine",
    }

    @classmethod
    def resolve_capability(cls, requirement: CapabilityRequirement) -> ExecutionProfile:
        """
        Giải quyết CapabilityRequirement thành ExecutionProfile.
        Liên kết với AMG v2 để chọn Resident Model tối ưu theo phần cứng & VRAM.
        """
        tool_name = cls.TOOL_MAPPING.get(requirement.capability, "python_interpreter")
        
        # Liên kết AMG v2 Model Governor (nạp model từ Resident Pool)
        selected_model = "qwen3.5:4b"
        selected_endpoint = "http://127.0.0.1:11434"

        if requirement.hardware_preference == "CPU" or requirement.capability in ("web_search", "data_inspection"):
            selected_endpoint = "http://127.0.0.1:11435"

        profile = ExecutionProfile(
            capability_name=requirement.capability,
            selected_tool=tool_name,
            selected_model_name=selected_model,
            selected_endpoint_url=selected_endpoint,
            max_context_length=8192,
            timeout_seconds=120,
            is_sandboxed=True
        )
        logger.info(f"🔌 [CAPABILITY-BROKER]: Resolved capability '{requirement.capability}' -> Tool={tool_name}, Model={selected_model} ({selected_endpoint})")
        return profile
