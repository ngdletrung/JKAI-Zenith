"""
JKAI ZENITH — UNIVERSAL COGNITION CORTEX (v2.0)
File: core/cognitive/universal_cognition.py

Thay thế nhận diện cứng bằng Tầng Nhận Thức Đa Chiều (Universal Cognition Layer).
Chuyển đổi User Goal thành `CognitiveRequest` đại diện cho toàn bộ bối cảnh tác chiến.
Tích hợp trực tiếp với AMG v2 Model Governor thông qua Capability Requirements.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

from core.contracts.cognitive_contract import (
    CognitiveRequest,
    DeliverableSpec,
    DeliverableType,
    RenderingHint,
)

logger = logging.getLogger("jkai.cognitive.cortex")


class UniversalCognitionCortex:
    """
    Universal Cognition Cortex.
    Tạo ra CognitiveRequest representation (Goal, Target, Constraints, Risk, Success Criteria, Deliverable).
    """

    FILE_FORMAT_MAP = {
        "excel": "xlsx",
        "xlsx": "xlsx",
        "csv": "csv",
        "pdf": "pdf",
        "word": "docx",
        "docx": "docx",
        "python": "py",
        "script": "py",
        "image": "png",
        "sơ đồ": "svg",
        "diagram": "svg",
    }

    @classmethod
    def perceive(cls, goal: str, kwargs: Optional[Dict[str, Any]] = None) -> CognitiveRequest:
        """
        Nhận thức mục tiêu người dùng và đóng gói thành CognitiveRequest.
        """
        g = (goal or "").strip()
        g_lower = g.lower()
        opts = kwargs or {}

        # 1. Nhận diện Deliverable Spec
        target_fmt = "markdown"
        deliv_type = DeliverableType.TEXT
        rendering = RenderingHint.INLINE_CHAT
        requires_file = False

        for keyword, fmt in cls.FILE_FORMAT_MAP.items():
            if keyword in g_lower:
                requires_file = True
                target_fmt = fmt
                break

        if any(v in g_lower for v in ["tạo file", "xuất file", "tải file", "build file", "generate file"]):
            requires_file = True

        if requires_file:
            if target_fmt in ["xlsx", "pdf", "docx", "png"]:
                deliv_type = DeliverableType.FILE_BINARY
                rendering = RenderingHint.DOWNLOAD_LINK
            elif target_fmt in ["py", "sh", "js"]:
                deliv_type = DeliverableType.FILE_CODE
                rendering = RenderingHint.EMBEDDED_ARTIFACT
            else:
                deliv_type = DeliverableType.FILE_BINARY
                rendering = RenderingHint.DOWNLOAD_LINK

        # 2. Rút trích Ràng buộc (Constraints) & Đối tượng (Entities)
        constraints: List[str] = []
        if "giữ nguyên" in g_lower:
            constraints.append("PRESERVE_EXISTING_FORMAT")
        if "không dùng" in g_lower or "tránh" in g_lower:
            constraints.append("AVOID_SPECIFIED_DEPENDENCIES")
        if "ưu tiên" in g_lower or "hết hạn" in g_lower:
            constraints.append("PRIORITIZE_URGENT_ITEMS")
        if target_fmt != "markdown":
            constraints.append(f"MUST_OUTPUT_VALID_{target_fmt.upper()}_FILE")

        entities: List[str] = []
        if "team" in g_lower or "đội" in g_lower or "nhóm" in g_lower:
            entities.append("TEAM_WORKLOAD")
        if "báo cáo" in g_lower or "tiến độ" in g_lower:
            entities.append("PROGRESS_REPORT")
        if "hợp đồng" in g_lower or "contract" in g_lower:
            entities.append("CONTRACT_DOCUMENTS")
        if "bất thường" in g_lower or "anomaly" in g_lower:
            entities.append("ANOMALY_DETECTION")

        # 3. Tiêu chí thành công (Success Criteria)
        success_criteria: List[str] = []
        if deliv_type in (DeliverableType.FILE_BINARY, DeliverableType.FILE_CODE):
            success_criteria.append(f"PHYSICAL_FILE_EXISTS_{target_fmt.upper()}")
            success_criteria.append("FILE_SIZE_GREATER_THAN_ZERO")
            success_criteria.append("SYNTAX_AND_INTEGRITY_VALIDATED")
        else:
            success_criteria.append("DIRECT_CONVERSATIONAL_RESPONSE")

        # 4. Xác định độ sâu thực thi (Execution Depth)
        exec_depth = "DEEP_PLANNING" if requires_file or len(g) > 80 else "DIRECT_REFLEX"
        risk_lvl = "MEDIUM" if requires_file else "LOW"

        deliverable_spec = DeliverableSpec(
            type=deliv_type,
            format=target_fmt,
            target_path=f"exports/zenith_output.{target_fmt}" if requires_file else None,
            rendering_hint=rendering
        )

        request = CognitiveRequest(
            goal=g,
            intent="BUILD_ARTIFACT" if requires_file else "GENERAL_KNOWLEDGE",
            deliverable=deliverable_spec,
            constraints=constraints,
            entities=entities,
            risk_level=risk_lvl,
            success_criteria=success_criteria,
            authority_required=["read", "write_file"] if requires_file else ["read"],
            confidence=0.98
        )

        logger.info(
            f"🧠 [UNIVERSAL-COGNITION-CORTEX]: Perceived Goal='{g[:40]}...' -> "
            f"Type={request.deliverable.type.value}, Format={request.deliverable.format}"
        )
        return request
