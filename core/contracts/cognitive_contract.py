"""
JKAI ZENITH — KERNEL CONTRACT: COGNITIVE RUNTIME & MISSION CONTRACTS (v2.0)
File: core/contracts/cognitive_contract.py

Chứa các Hợp đồng dữ liệu bất biến (Immutable Dataclass Contracts) định hình chuẩn giao tiếp
giữa Universal Cognition, Mission Builder, Planner, AMG Governor, Capability Broker, Verifier và Engram v2.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time
import uuid


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
    Được tạo ra bởi Universal Cognition Cortex từ User Goal.
    Không chỉ là classification đơn thuần, mà là bản đại diện đa chiều cho yêu cầu.
    """
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    intent: str = "GENERAL"
    deliverable: DeliverableSpec = field(default_factory=DeliverableSpec)
    constraints: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    execution_depth: str = "DEEP_PLANNING"     # "DIRECT_REFLEX", "DEEP_PLANNING", "MULTI_AGENT_DAG"
    risk_level: str = "LOW"                    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    success_criteria: List[str] = field(default_factory=list)
    authority_required: List[str] = field(default_factory=lambda: ["read"])
    confidence: float = 1.0


@dataclass(frozen=True)
class MissionSpecification:
    """
    Mission Contract do Mission Builder sinh ra từ CognitiveRequest.
    Là cơ sở cho Planner thiết lập DAG / Task Graph.
    """
    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request_id: str = ""
    objective: str = ""
    constraints: List[str] = field(default_factory=list)
    resources_required: List[str] = field(default_factory=list)
    expected_output: DeliverableSpec = field(default_factory=DeliverableSpec)
    verification_criteria: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationResult:
    """Kết quả thẩm định từ Verifier."""
    passed: bool
    score: float                               # 0.0 -> 1.0
    summary: str = ""
    missing_criteria: List[str] = field(default_factory=list)
    diagnostic_logs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperienceRecord:
    """
    Hồ sơ trải nghiệm đúc kết cho Engram v2.
    Lưu giữ cả trải nghiệm thành công lẫn bài học thất bại (Negative Memory).
    """
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_signature: str = ""
    context_summary: str = ""
    strategy_used: str = ""
    tools_used: List[str] = field(default_factory=list)
    model_profile_used: str = ""
    outcome: str = "SUCCESS"                    # "SUCCESS", "FAILED"
    failure_cause: Optional[str] = None
    recovery_action: Optional[str] = None
    verification_passed: bool = True
    negative_lessons: List[str] = field(default_factory=list)
    confidence_rating: float = 0.90
    timestamp: float = field(default_factory=time.time)
