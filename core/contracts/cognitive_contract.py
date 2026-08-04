"""
JKAI ZENITH — KERNEL CONTRACT: COGNITIVE RUNTIME CONTRACTS (v2.1)
File: core/contracts/cognitive_contract.py

Canonical owner for CognitiveRequest, DeliverableSpec, and MissionDefinition.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time
import uuid

from core.contracts.identity_contract import IdentityChain


class DeliverableType(str, Enum):
    TEXT = "TEXT"
    FILE_BINARY = "FILE_BINARY"
    FILE_CODE = "FILE_CODE"
    SYSTEM_MUTATION = "SYSTEM_MUTATION"


class RenderingHint(str, Enum):
    DOWNLOAD_LINK = "DOWNLOAD_LINK"
    EMBEDDED_ARTIFACT = "EMBEDDED_ARTIFACT"
    INLINE_CHAT = "INLINE_CHAT"


@dataclass(frozen=True)
class DeliverableSpec:
    """Quy cách sản phẩm đầu ra mong muốn."""
    type: DeliverableType = DeliverableType.TEXT
    format: str = "markdown"                    # "xlsx", "pdf", "csv", "png", "py", "markdown"
    target_path: Optional[str] = None
    rendering_hint: RenderingHint = RenderingHint.INLINE_CHAT


@dataclass(frozen=True)
class CognitiveRequest:
    """
    Cognitive Request Representation
    Được tạo ra bởi Universal Cognition Cortex từ User Goal + World State.
    Tách biệt hoàn toàn nhận thức với lập kế hoạch (execution_depth do Planner quyết định).
    """
    identity: IdentityChain = field(default_factory=IdentityChain)
    goal: str = ""
    intent: str = "GENERAL"
    deliverable: DeliverableSpec = field(default_factory=DeliverableSpec)
    constraints: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    risk_level: str = "LOW"                    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    success_criteria: List[str] = field(default_factory=list)
    authority_required: List[str] = field(default_factory=lambda: ["read"])
    confidence: float = 1.0


@dataclass(frozen=True)
class MissionDefinition:
    """
    Nguồn Sự Thật Duy Nhất (Single Source of Truth) của toàn bộ tác chiến.
    Không ai (Planner, LLM, Executor, Verifier) được tự ý sửa đổi objective gốc.
    """
    identity: IdentityChain = field(default_factory=IdentityChain)
    objective: str = ""
    constraints: List[str] = field(default_factory=list)
    resources_required: List[str] = field(default_factory=list)
    expected_output: DeliverableSpec = field(default_factory=DeliverableSpec)
    verification_criteria: List[str] = field(default_factory=list)
    authorization_scope: List[str] = field(default_factory=lambda: ["read"])
    risk_policy: str = "STRICT_DENY_FIRST"
