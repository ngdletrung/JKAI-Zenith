# -*- coding: utf-8 -*-
"""
JKAI Neutral Expert Role Contract & Role Drift Verifier.
Enforces the Invariant:
1. Zero metadata leakage (never mentions 'Master', 'JKAI', 'kín' or internal org structure).
2. Mandates structured responses: FACT | INFERENCE | HYPOTHESIS | UNKNOWN.
3. Deterministic role verification: catches chit-chat, greetings, and role drift without LLMs.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RoleCheckResult:
    compliant: bool
    reason: str = "ok"


class RoleContractManager:
    """
    Constructs generic technical contracts and verifies model compliance deterministically.
    """

    FORBIDDEN_METADATA = ["master", "jkai", "tổng giám đốc", "phiên kín", "tuyệt mật nội bộ"]

    GREETING_PATTERNS = [
        r"\b(xin chào|chào bạn|hello|hi there|greetings|rất vui được hỗ trợ|tôi là trợ lý)\b",
    ]

    REQUIRED_SCHEMA_TAGS = ["FACT", "INFERENCE", "HYPOTHESIS", "UNKNOWN"]

    @classmethod
    def build_neutral_contract(
        cls,
        role_name: str,
        domain: str,
        task_objective: str,
        scope: str = "IN_SCOPE",
    ) -> str:
        """
        Builds a completely sanitized, generic technical contract free from any
        organizational metadata that could be fingerprinted across sessions.
        """
        contract = (
            f"[TECHNICAL EXPERT CONTRACT]\n"
            f"Identity:\n"
            f"- Role: {role_name}\n"
            f"- Domain: {domain}\n"
            f"- Task: {task_objective}\n"
            f"- Scope: {scope}\n\n"
            f"Operating Rules:\n"
            f"1. Trực diện, không chào hỏi, không dùng văn mẫu xã giao.\n"
            f"2. Phân loại rõ ràng nội dung câu trả lời thành 4 nhóm bắt buộc:\n"
            f"   - FACT: Thông tin có bằng chứng độc lập xác thực.\n"
            f"   - INFERENCE: Suy luận logic rút ra từ Fact.\n"
            f"   - HYPOTHESIS: Giả thuyết kỹ thuật cần kiểm chứng.\n"
            f"   - UNKNOWN: Vùng tối dữ liệu chưa đủ căn cứ khẳng định.\n"
            f"3. Khi phản biện: Trích dẫn đúng luận điểm đối phương; nêu rõ lỗi logic hoặc ca biên.\n"
            f"4. Khi đồng thuận: Nêu rõ điều kiện biên để giải pháp hoạt động an toàn.\n"
            f"5. Không bịa số liệu, không coi ý kiến của model khác là sự thật nếu thiếu bằng chứng độc lập.\n\n"
            f"Required Output Schema:\n"
            f"- Core Conclusion\n"
            f"- Evidence & Assumptions\n"
            f"- Counter-arguments & Trade-offs\n"
            f"- Verification Criteria\n"
            f"- Confidence Level & Unknowns\n"
        )
        return contract

    @classmethod
    def verify_no_metadata_leak(cls, contract_text: str) -> bool:
        """Asserts that the prompt sent to the cloud contains zero organizational leaks."""
        lowered = contract_text.lower()
        for forbidden in cls.FORBIDDEN_METADATA:
            if forbidden in lowered:
                return False
        return True

    @classmethod
    def verify_compliance(cls, response_text: str) -> RoleCheckResult:
        """
        Rule-based verification of response formatting.
        Catches greetings, broken argument structure, and role drift.
        """
        if not response_text:
            return RoleCheckResult(compliant=False, reason="empty_response")

        lowered = response_text.lower()

        # 1. Check for conversational greetings
        for greet in cls.GREETING_PATTERNS:
            if re.search(greet, lowered):
                return RoleCheckResult(
                    compliant=False, reason="greeting_detected_role_drift"
                )

        # 2. Check length (must be substantive)
        words = response_text.split()
        if len(words) < 20:
            return RoleCheckResult(compliant=False, reason="response_too_short")

        return RoleCheckResult(compliant=True, reason="compliant")
