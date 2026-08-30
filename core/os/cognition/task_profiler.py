"""
JKAI ZENITH AI OS — TASK PROFILER (v2.0)
File: core/os/cognition/task_profiler.py

Computes multi-dimensional TaskProfile from input goal, history, and context.
Separates Task Complexity from Execution Topology.

v2.0: Extended with EEC v2.0 fields so EvidenceGateAuditor does not need
to re-derive mission intent from scratch (avoids architectural duplication).
  - evidence_policy: EvidencePolicy enum (not just str)
  - evidence_requirements: List[EvidenceRequirement] from PropositionRegistry
  - capability_dimensions: List[CapabilityDimension] relevant to this task
  - completion_policy: str (STRICT | LENIENT | ABSTAIN_ON_INSUFFICIENT)
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional


@dataclass
class TaskProfile:
    """Multi-dimensional profile of a user request (v2.0)."""
    complexity: float = 0.0        # Estimated cognitive demand (0.0 to 1.0)
    risk: float = 0.0              # Safety and system risk (0.0 to 1.0)
    uncertainty: float = 0.0       # Ambiguity and knowledge gap (0.0 to 1.0)
    confidence_score: float = 0.9  # Confidence level of initial hypothesis (0.0 to 1.0)
    side_effects: bool = False     # Causes system/environment side-effects
    statefulness: bool = False     # Requires state tracking across steps
    mutation_scope: str = "NONE"   # NONE, SINGLE_FILE, MULTI_FILE, SYSTEM_STATE
    tool_breadth: int = 0          # Estimated number of tool types needed
    verification_need: str = "LOW" # LOW, MEDIUM, HIGH, CRITICAL
    target_entity: str = "SYSTEM"  # AI_SELF, USER, SYSTEM (Self-Identity & Target Alignment)
    is_self_eval: bool = False     # AI self-evaluation & testing requested
    evidence_policy: str = "OPTIONAL" # OPTIONAL, REQUIRED, REQUIRED_INDEPENDENT, REQUIRED_MULTI_SOURCE
    reason_codes: List[str] = field(default_factory=list)

    # ── EEC v2.0 fields (prevent EvidenceGateAuditor from re-deriving intent) ──
    # List of EvidenceRequirement objects for this task (from PropositionRegistry)
    evidence_requirements: List[Any] = field(default_factory=list)
    # Which CapabilityDimensions are relevant
    capability_dimensions: List[Any] = field(default_factory=list)
    # Completion policy: STRICT (any fail=blocked), LENIENT (low_confidence OK), ABSTAIN_ON_INSUFFICIENT
    completion_policy: str = "STRICT"


def profile_task(goal: str, history: Optional[List] = None, kwargs: Optional[Dict[str, Any]] = None) -> TaskProfile:
    """
    Computes a multi-dimensional TaskProfile from goal text and context signals.
    """
    g = (goal or "").strip().lower()
    kw = kwargs or {}
    profile = TaskProfile()

    # 0. Self-Evaluation & AI Self-Testing (High Priority Target Identity Guard)
    self_eval_pattern = re.search(
        r"\b(tự\s+(?:thực\s+hiện|kiểm\s+tra|làm|đánh\s+giá|test|chứng\s+minh)|chứng\s+minh\s+năng\s+lực|test\s+(?:bản\s+thân|chính\s+mình|năng\s+lực\s+của\s+bạn)|năng\s+lực\s+của\s+bạn|khả\s+năng\s+của\s+bạn|bài\s+test\s+của\s+bạn)\b",
        g, re.I
    )
    if self_eval_pattern:
        profile.target_entity = "AI_SELF"
        profile.is_self_eval = True
        profile.evidence_policy = "REQUIRED"
        profile.complexity = 0.7
        profile.uncertainty = 0.3
        profile.verification_need = "HIGH"
        profile.confidence_score = 0.8
        profile.completion_policy = "STRICT"
        profile.reason_codes.append("SELF_EVALUATION_ACTION_ENFORCED")
        # Populate EEC v2.0 fields from PropositionRegistry
        try:
            from core.os.cognition.proposition_registry import PropositionRegistry
            from core.os.cognition.evidence_execution_contract import CapabilityDimension
            profile.capability_dimensions = [
                CapabilityDimension.SELF_EVALUATION,
                CapabilityDimension.TOOL_FILE_ACTUATION,
                CapabilityDimension.REASONING_LOGIC,
            ]
            profile.evidence_requirements = PropositionRegistry.to_requirements(
                CapabilityDimension.SELF_EVALUATION
            )
        except ImportError:
            pass  # Graceful degradation if EEC not installed

    # 1. Check Capability Acknowledgement / Greeting / Math (REFLEX signals)
    from core.utils.jkai_capabilities import goal_is_capabilities_inquiry
    if goal_is_capabilities_inquiry(goal):
        profile.reason_codes.append("CAPABILITY_QUERY")
        profile.verification_need = "LOW"
        profile.confidence_score = 1.0
        return profile

    social_greeting_pattern = re.search(
        r"\b(xin\s+chào|chào|hello|hi|cảm\s+ơn|thanks|tạm\s+biệt|bye|bạn\s+thế\s+nào|thế\s+nào|khỏe\s+không|bạn\s+khỏe|hôm\s+nay\s+thế\s+nào|cảm\s+thấy\s+thế\s+nào|how\s+are\s+you|bạn\s+là\s+ai|bạn\s+tên\s+gì)\b",
        g, re.I
    )
    if social_greeting_pattern:
        profile.reason_codes.append("GREETING_SOCIAL")
        profile.verification_need = "LOW"
        profile.confidence_score = 1.0
        return profile

    # 2. Risk & Mutation Scope Analysis (Unicode Safe)
    high_risk_patterns = [
        r"xóa", r"drop", r"rm\s+-rf", r"truncate", r"systemctl\s+stop", 
        r"flush\s+iptables", r"delete\s+database", r"format\s+disk"
    ]
    if any(re.search(pat, g, re.I) for pat in high_risk_patterns):
        profile.risk = 1.0
        profile.side_effects = True
        profile.mutation_scope = "SYSTEM_STATE"
        profile.verification_need = "CRITICAL"
        profile.confidence_score = 0.95
        profile.reason_codes.append("HIGH_RISK_DESTRUCTIVE_COMMAND")
        return profile

    # 3. Multi-file & Architectural Audit & Deep Debug Analysis (High Priority)
    audit_debug_pattern = re.search(
        r"\b(tái\ thiết\ kế|microservice|toàn\ bộ|tất\ cả|chuẩn\ hóa|refactor|workspace|nhiều\ file|tất\ cả\ file|phân\ tích|rà\ soát|mô\ hình|nguyên\ nhân|root\ cause|debug|giải\ mã|execution\ path)\b",
        g, re.I
    )
    if audit_debug_pattern:
        profile.complexity = 0.8
        profile.uncertainty = 0.5
        profile.mutation_scope = "MULTI_FILE"
        profile.verification_need = "HIGH"
        profile.confidence_score = 0.75  # Lower initial confidence -> encourages observation
        if re.search(r"\b(tái\ thiết\ kế|microservice|toàn\ bộ|tất\ cả|chuẩn\ hóa|refactor|workspace|nhiều\ file)\b", g):
            profile.reason_codes.append("MULTI_FILE_AUDIT_ACTION")
        else:
            profile.reason_codes.append("DEBUG_ANALYSIS_ACTION")
        profile.evidence_policy = "REQUIRED"
    elif re.search(r"\b(sửa|fix|update|tạo|create|viết|write)\b", g):
        profile.complexity = 0.4
        profile.mutation_scope = "SINGLE_FILE"
        profile.verification_need = "MEDIUM"
        profile.confidence_score = 0.85
        profile.evidence_policy = "REQUIRED"
        profile.reason_codes.append("SINGLE_FILE_ACTION")
    elif re.search(r"\b(xem|đọc|read|check|kiểm\ tra|quét|scan)\b", g):
        profile.complexity = 0.2
        profile.mutation_scope = "NONE"
        profile.verification_need = "LOW"
        profile.confidence_score = 0.9
        profile.reason_codes.append("READ_ONLY_INSPECTION")

    # 4. Dynamic upgrade: nếu goal sau khi enrich rõ ràng chạm nhiều file thì nâng scope
    if ("SINGLE_FILE_ACTION" in profile.reason_codes or "READ_ONLY_INSPECTION" in profile.reason_codes):
        multi_hint = re.search(
            r"(nhiều\s*file|và\s*file|file\s+và|workspace|module|dependencies|liên\ quan|các\s+file|toàn\ bộ\s+file)",
            g, re.I
        )
        if multi_hint:
            profile.complexity = max(profile.complexity, 0.7)
            profile.mutation_scope = "MULTI_FILE"
            profile.verification_need = "HIGH"
            profile.evidence_policy = "REQUIRED"
            profile.reason_codes.append("UPGRADED_MULTI_FILE_SCOPE")

    return profile


def update_profile_from_observation(profile: TaskProfile, observation: Dict[str, Any]) -> TaskProfile:
    """
    Belief Revision Primitive: Dynamically mutates TaskProfile based on runtime tool observations.
    """
    modified_files = observation.get("modified_files", [])
    inspected_files = observation.get("inspected_files", [])
    has_error = observation.get("status") in ("INVALID_INPUT", "TOOL_ERROR")

    if len(modified_files) > 1 or len(inspected_files) > 3:
        profile.mutation_scope = "MULTI_FILE"
        profile.complexity = max(profile.complexity, 0.75)
        if "REVISED_MULTI_FILE_OBSERVATION" not in profile.reason_codes:
            profile.reason_codes.append("REVISED_MULTI_FILE_OBSERVATION")

    if has_error:
        profile.uncertainty = min(1.0, profile.uncertainty + 0.2)
        profile.confidence_score = max(0.1, profile.confidence_score - 0.15)
        if "OBSERVED_TOOL_ERROR" not in profile.reason_codes:
            profile.reason_codes.append("OBSERVED_TOOL_ERROR")

    return profile

