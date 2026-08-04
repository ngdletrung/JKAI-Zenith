"""
JKAI ZENITH — KERNEL CONTRACT: COGNITIVE RUNTIME CONTRACTS (v2.1)
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
class IdentityChain:
    """
    Chuỗi định danh 8 mắc xích bất biến cho tác chiến tự chủ.
    request_id -> mission_id -> plan_id -> task_id -> attempt_id -> execution_id -> observation_id -> verification_id
    """
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:10]}")
    mission_id: str = field(default_factory=lambda: f"mis_{uuid.uuid4().hex[:10]}")
    plan_id: str = field(default_factory=lambda: f"pln_{uuid.uuid4().hex[:10]}")
    task_id: str = field(default_factory=lambda: f"tsk_{uuid.uuid4().hex[:10]}")
    attempt_id: str = field(default_factory=lambda: f"att_{uuid.uuid4().hex[:10]}")
    execution_id: str = field(default_factory=lambda: f"exe_{uuid.uuid4().hex[:10]}")
    observation_id: str = field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:10]}")
    verification_id: str = field(default_factory=lambda: f"ver_{uuid.uuid4().hex[:10]}")


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
