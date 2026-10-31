"""
JKAI ZENITH — CANONICAL CONTRACT & FSM KERNEL (PHASE R1)
File: core/contracts/canonical_contract.py
Ownership: Master LeeTrung (User Authority)
Architecture: Evidence-Governed Small-Model Agent Operating System (Antigravity & Opencode)

SSoT Principles:
1. Model output = Proposal != Decision != Authority != Completion
2. Tool success != Mission completed
3. Single FSM State Machine strictly governed by Policy & Verification Kernel
4. 5 Canonical Objects: Mission, PlanProposal, AuthorizedAction, ExecutionReceipt, VerificationVerdict
"""

from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ── 1. ENUMS & POLICY DECISION ─────────────────────────────────────────────

class PolicyDecision(str, Enum):
    """Quyết định quyền lực tối cao duy nhất của Kernel."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class CanonicalState(str, Enum):
    """
    FSM State Machine duy nhất của toàn hệ thống JKAI.
    Chỉ duy nhất Kernel có thẩm quyền thay đổi trạng thái này.
    """
    # Tuyến tiến trình chuẩn (Forward Path)
    RECEIVED = "RECEIVED"
    PLANNED = "PLANNED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"

    # Tuyến sự cố / Dừng (Terminal / Exception Path)
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class VerificationLevel(str, Enum):
    """Bốn cấp kiểm chứng bằng chứng độc lập."""
    L1_PHYSICAL = "L1_PHYSICAL"     # File, tiến trình, artifact vật lý tồn tại
    L2_SYNTACTIC = "L2_SYNTACTIC"   # JSON, YAML, AST hợp lệ, không lỗi cú pháp
    L3_STRUCTURAL = "L3_STRUCTURAL" # Đủ class, function, export, schema yêu cầu
    L4_SEMANTIC = "L4_SEMANTIC"     # Đạt acceptance criteria và kiểm thử nghiệp vụ


class VerificationStatus(str, Enum):
    """Kết luận thẩm định kiểm chứng độc lập."""
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"


# ── 2. NĂM ĐỐI TƯỢNG HỢP ĐỒNG CHUẨN (CANONICAL OBJECTS) ────────────────────

@dataclass
class Mission:
    """
    Hợp đồng nhiệm vụ gốc (Source of Truth).
    Chứa định danh, ý định, ràng buộc, phạm vi thẩm quyền và trạng thái FSM hiện tại.
    """
    mission_id: str = field(default_factory=lambda: f"m_{uuid.uuid4().hex[:8]}")
    intent: str = ""
    constraints: List[str] = field(default_factory=list)
    required_outputs: List[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    authority_scope: List[str] = field(default_factory=lambda: ["read", "write_workspace"])
    state: CanonicalState = CanonicalState.RECEIVED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "intent": self.intent,
            "constraints": self.constraints,
            "required_outputs": self.required_outputs,
            "risk_level": self.risk_level,
            "authority_scope": self.authority_scope,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class PlanProposal:
    """
    Đề xuất kế hoạch hành động do Model Adapter sinh ra.
    QUY TẮC: Proposal thuần túy suy luận xác suất, KHÔNG CÓ THẨM QUYỀN VÀ KHÔNG PHẢI QUYẾT ĐỊNH.
    """
    proposal_id: str = field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    mission_id: str = ""
    proposed_by: str = field(default_factory=lambda: os.getenv("JKAI_DEFAULT_SLM", "dynamic_slm"))
    strategy: str = "STEPWISE_VERIFIED"  # DIRECT_REASONING, RETRIEVAL_FIRST, STEPWISE_VERIFIED, CLARIFY_OR_REFUSE_FIRST
    steps: List[Dict[str, Any]] = field(default_factory=list)
    proposed_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "mission_id": self.mission_id,
            "proposed_by": self.proposed_by,
            "strategy": self.strategy,
            "steps": self.steps,
            "proposed_tool_calls": self.proposed_tool_calls,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }


@dataclass
class AuthorizedAction:
    """
    Hành động cụ thể đã được Policy & Verification Kernel cấp phép.
    Chỉ những hành động có PolicyDecision.ALLOW mới được Capability Runtime thực thi.
    """
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    mission_id: str = ""
    proposal_id: str = ""
    decision: PolicyDecision = PolicyDecision.REQUIRE_APPROVAL
    authorized_by: str = "KERNEL_POLICY_GATE"
    allowed_tool: str = ""
    allowed_args: Dict[str, Any] = field(default_factory=dict)
    resource_ceiling: Dict[str, Any] = field(default_factory=lambda: {"max_time_sec": 30.0, "max_memory_mb": 512})
    timestamp: float = field(default_factory=time.time)

    def is_executable(self) -> bool:
        return self.decision == PolicyDecision.ALLOW


@dataclass
class ExecutionReceipt:
    """
    Biên lai thực thi vật lý từ Capability Runtime.
    Chứng minh công cụ đã chạy thành công, KHÔNG CHỨNG MINH NHIỆM VỤ ĐÃ HOÀN TẤT.
    """
    receipt_id: str = field(default_factory=lambda: f"rcpt_{uuid.uuid4().hex[:8]}")
    action_id: str = ""
    mission_id: str = ""
    tool_name: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = field(default_factory=time.time)
    exit_code: int = 0
    stdout_sha256: str = ""
    output_summary: str = ""
    artifacts: List[str] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @classmethod
    def create(cls, action: AuthorizedAction, tool_name: str, exit_code: int, output_text: str, artifacts: List[str] = None, raw_data: Dict[str, Any] = None, error_message: str = None) -> ExecutionReceipt:
        now = time.time()
        sha = hashlib.sha256(output_text.encode('utf-8', errors='replace')).hexdigest()
        summary = output_text[:200] if output_text else ""
        return cls(
            action_id=action.action_id,
            mission_id=action.mission_id,
            tool_name=tool_name,
            started_at=action.timestamp,
            finished_at=now,
            exit_code=exit_code,
            stdout_sha256=sha,
            output_summary=summary,
            artifacts=artifacts or [],
            raw_data=raw_data,
            error_message=error_message
        )


@dataclass
class VerificationVerdict:
    """
    Phán quyết kiểm chứng độc lập (Independent Verifier).
    Chỉ khi all_required_criteria == True và safety_checks == passed mới được công nhận COMPLETE.
    """
    verdict_id: str = field(default_factory=lambda: f"vrd_{uuid.uuid4().hex[:8]}")
    mission_id: str = ""
    receipt_refs: List[str] = field(default_factory=list)
    status: VerificationStatus = VerificationStatus.INCOMPLETE
    levels_passed: Dict[str, bool] = field(default_factory=lambda: {
        VerificationLevel.L1_PHYSICAL.value: False,
        VerificationLevel.L2_SYNTACTIC.value: False,
        VerificationLevel.L3_STRUCTURAL.value: False,
        VerificationLevel.L4_SEMANTIC.value: False,
    })
    criteria_results: Dict[str, bool] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    verified_by: str = "INDEPENDENT_VERIFIER"
    verified_at: float = field(default_factory=time.time)

    def is_verified_complete(self) -> bool:
        """Kiểm chứng toàn diện 4 tầng và mọi tiêu chí đạt 100%."""
        if self.status != VerificationStatus.COMPLETE:
            return False
        if not all(self.levels_passed.values()):
            return False
        if self.criteria_results and not all(self.criteria_results.values()):
            return False
        return True


# ── 3. CANONICAL FSM ENGINE (CHỈ KERNEL ĐIỀU KHIỂN) ─────────────────────────

class IllegalStateTransitionError(Exception):
    """Ngoại lệ khi vi phạm đồ thị chuyển đổi trạng thái FSM."""
    pass


class CanonicalFSM:
    """
    Bộ máy trạng thái hữu hạn chuẩn hóa duy nhất của JKAI.
    Quy tắc:
    - Model, Controller, Tool TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý gọi set_state.
    - Mọi bước chuyển phải tuân thủ nghiêm ngặt đồ thị chuyển đổi hợp lệ.
    """

    VALID_TRANSITIONS: Dict[CanonicalState, Set[CanonicalState]] = {
        CanonicalState.RECEIVED: {
            CanonicalState.PLANNED,
            CanonicalState.BLOCKED,
            CanonicalState.FAILED
        },
        CanonicalState.PLANNED: {
            CanonicalState.AUTHORIZED,
            CanonicalState.BLOCKED,
            CanonicalState.FAILED
        },
        CanonicalState.AUTHORIZED: {
            CanonicalState.EXECUTING,
            CanonicalState.BLOCKED,
            CanonicalState.FAILED
        },
        CanonicalState.EXECUTING: {
            CanonicalState.VERIFYING,
            CanonicalState.FAILED,
            CanonicalState.ROLLED_BACK
        },
        CanonicalState.VERIFYING: {
            CanonicalState.COMPLETE,
            CanonicalState.INCOMPLETE,
            CanonicalState.BLOCKED,
            CanonicalState.FAILED,
            CanonicalState.ROLLED_BACK
        },
        # Trạng thái kết thúc (Terminal) - có thể reset khi Re-plan được Kernel phê chuẩn
        CanonicalState.INCOMPLETE: {
            CanonicalState.PLANNED,
            CanonicalState.FAILED
        },
        CanonicalState.BLOCKED: {
            CanonicalState.PLANNED,
            CanonicalState.FAILED
        },
        CanonicalState.COMPLETE: set(),
        CanonicalState.FAILED: {CanonicalState.ROLLED_BACK},
        CanonicalState.ROLLED_BACK: set(),
    }

    def __init__(self, mission: Mission):
        self.mission = mission
        self.history: List[Dict[str, Any]] = [
            {
                "from_state": None,
                "to_state": mission.state.value,
                "actor": "INIT",
                "timestamp": mission.created_at,
                "evidence": "Mission initialization"
            }
        ]

    @property
    def current_state(self) -> CanonicalState:
        return self.mission.state

    def transition(self, to_state: CanonicalState, actor: str, evidence: str = "") -> CanonicalState:
        """
        Thực hiện chuyển trạng thái FSM với cơ chế kiểm tra tính hợp lệ nghiêm ngặt.
        Chỉ kernel actors (KERNEL, VERIFIER) được phép chuyển sang COMPLETE/AUTHORIZED.
        """
        from_state = self.mission.state

        # 1. Kiểm tra đồ thị chuyển đổi
        allowed_targets = self.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed_targets:
            raise IllegalStateTransitionError(
                f"[FSM-BREACH] Không thể chuyển trạng thái từ '{from_state.value}' sang '{to_state.value}'. "
                f"Các trạng thái hợp lệ: {[s.value for s in allowed_targets]}"
            )

        # 2. Rào chắn thẩm quyền (Authority Gate)
        # Model không bao giờ được phép làm actor chuyển trạng thái
        if actor.upper() in ["MODEL", "LLM", "SLM", "ASSISTANT", "PROPOSAL"]:
            raise PermissionError(f"[INVARIANT-VIOLATION] Model '{actor}' không có quyền thay đổi trạng thái FSM.")

        # Chỉ Verifier hoặc Kernel mới được kết luận COMPLETE
        if to_state == CanonicalState.COMPLETE and not actor.upper().startswith(("KERNEL", "VERIFIER")):
            raise PermissionError(f"[INVARIANT-VIOLATION] Actor '{actor}' không có thẩm quyền chứng nhận COMPLETE.")

        # 3. Chuyển đổi và lưu vết kiểm toán (Audit Trail)
        now = time.time()
        self.mission.state = to_state
        self.mission.updated_at = now
        self.history.append({
            "from_state": from_state.value,
            "to_state": to_state.value,
            "actor": actor,
            "timestamp": now,
            "evidence": evidence
        })

        return to_state
