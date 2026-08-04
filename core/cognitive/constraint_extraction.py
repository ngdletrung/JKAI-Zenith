"""
JKAI ZENITH — COGNITION LAYER: CONSTRAINT EXTRACTION ENGINE (v2.1)
File: core/cognitive/constraint_extraction.py

Rút trích các Ràng buộc (Constraints) bất biến từ User Goal.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger("jkai.cognition.constraint")


@dataclass(frozen=True)
class ConstraintExtractionResult:
    constraints: List[str] = field(default_factory=list)
    confidence: float = 0.95


class ConstraintExtractor:
    """Rút trích các ràng buộc kỹ thuật & quy tắc bắt buộc."""

    @classmethod
    def extract_constraints(cls, goal: str) -> ConstraintExtractionResult:
        g_lower = (goal or "").lower()
        constraints: List[str] = []

        if "giữ nguyên" in g_lower:
            constraints.append("PRESERVE_EXISTING_FORMAT")
        if "không dùng" in g_lower or "tránh" in g_lower:
            constraints.append("AVOID_SPECIFIED_DEPENDENCIES")
        if "ưu tiên" in g_lower or "hết hạn" in g_lower:
            constraints.append("PRIORITIZE_URGENT_ITEMS")

        return ConstraintExtractionResult(constraints=constraints, confidence=0.95)
