"""
JKAI ZENITH — KERNEL CONTRACT: VERIFICATION & FAILURE CLASSIFICATION (v2.1)
File: core/contracts/verification_contract.py

Chứa các Hợp đồng dữ liệu bất biến cho Verifier, Phân loại Thất bại (Failure Classification)
và Hồ sơ Trải nghiệm Engram v2 (bao gồm Bài học Tiêu cực - Negative Memory).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time
import uuid

from core.contracts.identity_contract import IdentityChain


class RuntimeState(str, Enum):
    """Trạng thái máy máy tác chiến (State Machine Coordinator)."""
    # Non-Terminal States
    RECEIVED = "RECEIVED"
    COGNIZED = "COGNIZED"
    MISSIONED = "MISSIONED"
    PLANNED = "PLANNED"
    RESOLVED = "RESOLVED"
    EXECUTING = "EXECUTING"
    OBSERVED = "OBSERVED"
    VERIFYING = "VERIFYING"
    RETRYING = "RETRYING"
    SUBSTITUTING = "SUBSTITUTING"
    CHANGING_MODEL = "CHANGING_MODEL"
    REPLANNING = "REPLANNING"
    DIAGNOSING = "DIAGNOSING"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    # Terminal States (Tuyệt đối không transition ra khỏi 2 trạng thái này)
    DELIVERED = "DELIVERED"
    ABORTED = "ABORTED"


class FailureClassification(str, Enum):
    NONE = "NONE"                               # PASS
    TRANSIENT = "TRANSIENT"                     # Thất bại tạm thời -> RETRY
    TOOL_FAILURE = "TOOL_FAILURE"               # Lỗi thư viện/tool -> SUBSTITUTE_CAPABILITY
    MODEL_FAILURE = "MODEL_FAILURE"             # Lỗi LLM hallucination/format -> CHANGE_MODEL
    PLAN_FAILURE = "PLAN_FAILURE"               # Task graph rỗng/thiếu bước -> REPLAN
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"# Tool chạy thành công nhưng output không đúng mission -> DIAGNOSE/REPAIR
    INPUT_FAILURE = "INPUT_FAILURE"             # Yêu cầu mâu thuẫn/rỗng -> CLARIFICATION_REQUIRED
    POLICY_FAILURE = "POLICY_FAILURE"           # Vi phạm bảo mật Zero-Trust -> ABORTED


class RecoveryStrategy(str, Enum):
    NONE = "NONE"
    RETRY = "RETRY"
    SUBSTITUTE_CAPABILITY = "SUBSTITUTE_CAPABILITY"
    CHANGE_MODEL = "CHANGE_MODEL"
    REPLAN = "REPLAN"
    DIAGNOSE_AND_REPAIR = "DIAGNOSE_AND_REPAIR"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    ABORT = "ABORT"


@dataclass(frozen=True)
class VerificationResult:
    """Kết quả thẩm định từ Verifier."""
    identity: IdentityChain = field(default_factory=IdentityChain)
    passed: bool = True
    score: float = 1.0                          # 0.0 -> 1.0
    failure_classification: FailureClassification = FailureClassification.NONE
    recommended_recovery: RecoveryStrategy = RecoveryStrategy.NONE
    summary: str = ""
    missing_criteria: List[str] = field(default_factory=list)
    diagnostic_logs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperienceRecord:
    """
    Hồ sơ trải nghiệm đúc kết cho Engram v2 (Causal Experience & Semantic Transfer).
    Lưu giữ cả trải nghiệm thành công lẫn bài học thất bại (Negative Memory qua từng Attempt).
    """
    identity: IdentityChain = field(default_factory=IdentityChain)
    task_signature: str = ""
    context_summary: str = ""
    strategy_used: str = ""
    tools_used: List[str] = field(default_factory=list)
    model_profile_used: str = ""
    outcome: str = "SUCCESS"                    # "SUCCESS", "FAILED"
    failure_classification: FailureClassification = FailureClassification.NONE
    failure_cause: Optional[str] = None
    causal_explanation: Optional[str] = None    # Causal Reason: WHY it failed
    context_conditions: Dict[str, Any] = field(default_factory=dict) # WHEN & THEN conditions
    recovery_action: Optional[str] = None
    negative_lessons: List[str] = field(default_factory=list)
    confidence_rating: float = 0.90
    timestamp: float = field(default_factory=time.time)
