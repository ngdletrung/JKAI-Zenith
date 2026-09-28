# -*- coding: utf-8 -*-
"""
core/os/cognition/answer_quality_verifier.py
JKAI — Answer Quality Verifier (Answer Contract §8, base_soul.md)

3-dimensional quality check chạy song song với EpistemicAuditor.
Thuần rule-based, không gọi LLM, mục tiêu < 2ms.

Dimensions (từ Answer Contract Master chốt):
  DUNG  — Đúng   : không hallucinate, không lộ từ nội bộ
  TRUNG — Trúng  : trả lời đúng câu hỏi, không vòng vo / dump nội bộ
  DU    — Đủ     : có chào (khi phù hợp) + nội dung chính + bước tiếp (khi cần)

Hành động sửa tự động (chỉ khi an toàn):
  DU missing greeting  → tự thêm "Chào Master, "
  DUNG/TRUNG fail      → log cảnh báo, không tự sửa (escalate)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger("jkai.cognition.answer_quality")

# ---------------------------------------------------------------------------
# Từ nội bộ KHÔNG được lộ ra output gửi Master.
# SINGLE SOURCE OF TRUTH: core/governance/internal_vocabulary.py (Red Team Q3).
# Mọi token kỹ thuật mới chỉ đăng ký ở registry, không thêm lẻ tại đây.
# ---------------------------------------------------------------------------
from core.governance.internal_vocabulary import INTERNAL_LITERAL_TERMS, INTERNAL_PATTERNS

_INTERNAL_VOCAB_RE = re.compile(
    "|".join([re.escape(t) for t in INTERNAL_LITERAL_TERMS]
              + [p.pattern for p in INTERNAL_PATTERNS]),
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dấu hiệu hallucination rõ ràng
# ---------------------------------------------------------------------------
_HALLUCINATION_PATTERNS = [
    r"theo (?:các )?nghiên cứu(?! của| từ| năm| mới)",   # "theo nghiên cứu" không có nguồn
    r"thống kê (?:cho thấy|chứng minh)(?! rằng \d|\s+\d)", # stat không có số
    r"(?:chuyên gia|nhà khoa học) (?:cho rằng|khẳng định)(?! \w+\s*:)",  # trích không nguồn
]
_HALLUCINATION_RE = re.compile(
    "|".join(_HALLUCINATION_PATTERNS), re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Greeting patterns tiếng Việt + tiếng Anh
# ---------------------------------------------------------------------------
_GREETING_RE = re.compile(
    r"^(?:Chào|Kính chào|Xin chào|Dạ|Hello|Hi\b|Dear|Master\b|Thưa)",
    re.IGNORECASE | re.MULTILINE,
)

# Filler / lặp vô nghĩa
_FILLER_PATTERNS = [
    r"(?:Tóm lại|Nói tóm lại).{0,400}(?:Tóm lại|Nói tóm lại)",
    r"(?:Như đã (?:đề cập|nói) ở trên).{0,200}(?:Như đã (?:đề cập|nói))",
]
_FILLER_RE = re.compile("|".join(_FILLER_PATTERNS), re.IGNORECASE | re.DOTALL)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
class QualityDimension(str, Enum):
    DUNG = "DUNG"
    TRUNG = "TRUNG"
    DU = "DU"


@dataclass
class DimensionResult:
    dimension: QualityDimension
    passed: bool
    score: float          # 0.0 – 1.0
    issues: List[str] = field(default_factory=list)
    correction_applied: bool = False


@dataclass
class AnswerQualityReport:
    dung: DimensionResult
    trung: DimensionResult
    du: DimensionResult
    overall_passed: bool
    corrected_text: Optional[str]  # None nếu không cần / không thể sửa

    @property
    def overall_score(self) -> float:
        return round((self.dung.score + self.trung.score + self.du.score) / 3.0, 3)

    @property
    def needs_escalate(self) -> bool:
        """DUNG=False → có thể hallucinate → không tự sửa, báo lên."""
        return not self.dung.passed

    def summary(self) -> str:
        parts = []
        for dim in (self.dung, self.trung, self.du):
            icon = "✅" if dim.passed else "❌"
            parts.append(f"{icon}{dim.dimension.value}")
        status = "PASS" if self.overall_passed else "FAIL"
        return f"[AQV-{status}] {' | '.join(parts)} | score={self.overall_score:.2f}"


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------
class AnswerQualityVerifier:
    """
    3-dimensional answer quality verifier — channel-agnostic, < 2ms.

    Thiết kế:
    - Không gọi LLM
    - Không phụ thuộc vào database / Redis
    - Thread-safe (stateless singleton)
    - Tự sửa DU khi an toàn; DUNG/TRUNG thất bại → chỉ cảnh báo
    """

    # Response ngắn (< 60 ký tự) = factual reflex → không cần greeting
    _GREETING_MIN_LEN: int = 60
    # Response dài (> 600 ký tự) nhưng không đề cập từ khoá goal → nghi vấn TRUNG
    _VERBOSE_THRESHOLD: int = 600
    _GOAL_OVERLAP_MIN: int = 2    # tối thiểu 2 từ khoá goal phải có trong 200 ký tự đầu

    def verify(self, response_text: str, goal: str = "") -> AnswerQualityReport:
        text = (response_text or "").strip()

        dung = self._check_dung(text)
        trung = self._check_trung(text, goal)
        du_result = self._check_du(text, goal)

        corrected: Optional[str] = None

        # Tự sửa DU nếu chỉ thiếu greeting (an toàn, không thay đổi nội dung)
        if not du_result.passed and du_result.score >= 0.7:
            corrected, du_result = self._correct_du(text, du_result)

        overall_passed = dung.passed and trung.passed and du_result.passed

        report = AnswerQualityReport(
            dung=dung,
            trung=trung,
            du=du_result,
            overall_passed=overall_passed,
            corrected_text=corrected,
        )

        # Log
        if overall_passed:
            logger.debug("[AQV] %s", report.summary())
        else:
            logger.warning("[AQV] %s | Issues: DUNG=%s TRUNG=%s DU=%s",
                           report.summary(), dung.issues, trung.issues, du_result.issues)

        return report

    # ------------------------------------------------------------------
    # Dimension checks
    # ------------------------------------------------------------------

    def _check_dung(self, text: str) -> DimensionResult:
        """Đúng: không lộ từ nội bộ, không có dấu hiệu hallucination rõ ràng."""
        issues: List[str] = []

        internal_hits = list(set(_INTERNAL_VOCAB_RE.findall(text)))
        if internal_hits:
            issues.append(f"Lộ từ nội bộ: {internal_hits[:5]}")

        halluc_hits = _HALLUCINATION_RE.findall(text)
        if halluc_hits:
            issues.append(f"Dấu hiệu hallucination: {halluc_hits[:2]}")

        passed = not issues
        score = 1.0 if passed else max(0.1, 1.0 - 0.45 * len(issues))
        return DimensionResult(QualityDimension.DUNG, passed, score, issues)

    def _check_trung(self, text: str, goal: str) -> DimensionResult:
        """Trúng: trả lời đúng câu hỏi, không vòng vo / lặp vô nghĩa."""
        issues: List[str] = []

        # Kiểm tra overlap từ khoá goal trong 200 ký tự đầu
        if goal and len(text) > self._VERBOSE_THRESHOLD:
            goal_kws = set(w for w in re.findall(r"\w{3,}", goal.lower()) if len(w) > 3)
            head_words = set(re.findall(r"\w+", text[:200].lower()))
            overlap = goal_kws & head_words
            if len(goal_kws) >= 3 and len(overlap) < self._GOAL_OVERLAP_MIN:
                issues.append(
                    f"Response dài ({len(text)} ký tự) nhưng ít từ khoá goal trong 200 ký tự đầu"
                )

        # Kiểm tra filler / lặp vô nghĩa
        if _FILLER_RE.search(text):
            issues.append("Phát hiện filler / lặp nội dung vô nghĩa")

        passed = not issues
        score = 1.0 if passed else 0.6
        return DimensionResult(QualityDimension.TRUNG, passed, score, issues)

    def _check_du(self, text: str, goal: str) -> DimensionResult:
        """Đủ: có greeting (khi response đủ dài) + nội dung đủ."""
        issues: List[str] = []

        if len(text) < 5:
            issues.append("Response trống hoặc quá ngắn")
            return DimensionResult(QualityDimension.DU, False, 0.0, issues)

        # Greeting chỉ cần thiết với response dài (không phải factual reflex 1 dòng)
        if len(text) >= self._GREETING_MIN_LEN and not _GREETING_RE.search(text):
            issues.append("Thiếu greeting (Chào Master / Master)")

        passed = not issues
        # Thiếu greeting là lỗi nhỏ (0.75), thiếu nội dung là lỗi lớn (0.2)
        score = 1.0 if passed else (0.75 if "greeting" in str(issues) else 0.2)
        return DimensionResult(QualityDimension.DU, passed, score, issues)

    # ------------------------------------------------------------------
    # Auto-correction
    # ------------------------------------------------------------------

    def _correct_du(
        self, text: str, du: DimensionResult
    ) -> Tuple[str, DimensionResult]:
        """Tự thêm greeting nếu thiếu và an toàn (chỉ prepend, không thay đổi nội dung)."""
        if not any("greeting" in issue for issue in du.issues):
            return text, du  # Không biết sửa gì

        # Viết hoa ký tự đầu nếu đang thường
        if text and text[0].islower():
            first_char = text[0].upper()
            corrected = f"Chào Master, {first_char}{text[1:]}"
        else:
            corrected = f"Chào Master, {text}"

        new_du = DimensionResult(
            dimension=QualityDimension.DU,
            passed=True,
            score=0.9,
            issues=[],
            correction_applied=True,
        )
        logger.info("[AQV] DU auto-corrected: greeting prepended.")
        return corrected, new_du


# Singleton — import và dùng trực tiếp
answer_quality_verifier = AnswerQualityVerifier()
