# -*- coding: utf-8 -*-
"""
🧠 SEMANTIC SKILL MANIFEST & SCHEMA DEFINITION (MCP COMPLIANT)
Chuẩn hoá mô tả kỹ năng cho AI Agent theo chuẩn Model Context Protocol (MCP) & SOTA AI Agents.

Mỗi kỹ năng phải định nghĩa tường minh:
- Năng lực cốt lõi (description)
- Khi nào NÊN dùng (when_to_use)
- Khi nào CẤM dùng (when_not_to_use)
- Schema tham số nghiêm ngặt (parameters_schema)
- Ví dụ thực tế (examples)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JKAI.SkillManifest")


class SkillDomain(str, Enum):
    GENERAL = "GENERAL"
    WEB_RESEARCH = "WEB_RESEARCH"
    FINANCE = "FINANCE"
    CODE_ENGINEERING = "CODE_ENGINEERING"
    DATA_SCIENCE = "DATA_SCIENCE"
    DEVOPS_SYS = "DEVOPS_SYS"
    OFFICE_DOCS = "OFFICE_DOCS"
    SECURITY = "SECURITY"


@dataclass
class SemanticSkillManifest:
    skill_id: str
    display_name: str
    domain: SkillDomain
    description: str
    when_to_use: List[str]
    when_not_to_use: List[str]
    parameters_schema: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_mcp_tool_def(self) -> Dict[str, Any]:
        """
        Chuyển đổi manifest sang định dạng tool definition chuẩn MCP / OpenAI-compatible
        để nạp trực tiếp vào tham số `tools` của LLM API.
        """
        # Xây dựng mô tả giàu ngữ cảnh (Rich Contextual Description)
        rich_description = (
            f"{self.description}\n\n"
            f"✅ [KHI NÀO NÊN DÙNG]:\n" + "\n".join(f"- {cond}" for cond in self.when_to_use) + "\n\n"
            f"⛔ [KHI NÀO TUYỆT ĐỐI KHÔNG DÙNG]:\n" + "\n".join(f"- {cond}" for cond in self.when_not_to_use)
        )

        return {
            "type": "function",
            "function": {
                "name": self.skill_id,
                "description": rich_description,
                "parameters": self.parameters_schema
            }
        }

    def validate_arguments(self, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Kiểm tra tính hợp lệ của tham số truyền vào so với schema."""
        if not isinstance(args, dict):
            return False, f"Tham số truyền vào phải là Dictionary/JSON object, nhận được: {type(args).__name__}"

        req_fields = self.parameters_schema.get("required", [])
        for field in req_fields:
            if field not in args or args[field] is None or (isinstance(args[field], str) and not args[field].strip()):
                return False, f"Thiếu tham số bắt buộc '{field}' cho công cụ '{self.skill_id}'."

        return True, None
