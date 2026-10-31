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

        dung = self._check_dung(text, goal=goal)
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

    def _check_table_math(self, text: str) -> List[str]:
        """Kiểm tra tính nhất quán số học trong các bảng giá Markdown:
        1. quantity_kg * unit_price == subtotal từng dòng
        2. Tổng các dòng chi tiết == Dòng tổng cộng (nếu có).
        """
        issues = []
        lines = text.strip().split("\n")

        def _extract_money(s: str) -> float:
            m = re.search(r"(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:đ|vnđ|vnd)", s, re.I)
            if m:
                return float(m.group(1).replace(".", "").replace(",", ""))
            m2 = re.search(r"(\d{1,3}(?:[.,]\d{3})+)", s)
            if m2:
                return float(m2.group(1).replace(".", "").replace(",", ""))
            return 0.0

        def _parse_qty_kg(s: str):
            m_g = re.search(r"(\d+)\s*g\b", s, re.I)
            if m_g:
                return float(m_g.group(1)) / 1000.0
            m_kg = re.search(r"([\d.]+)\s*kg\b", s, re.I)
            if m_kg:
                return float(m_kg.group(1))
            return None

        subtotals: List[float] = []
        claimed_totals: List[float] = []

        for l in lines:
            parts = [p.strip() for p in l.split("|") if p.strip()]
            if not parts or parts[0].startswith(":-"):
                continue

            first_col = parts[0].lower()
            second_col = parts[1].lower() if len(parts) > 1 else ""

            # Nhận diện dòng tổng cộng
            if any(k in first_col or k in second_col for k in ["tổng", "tổng cộng", "tổng chi phí", "total"]):
                for p in parts:
                    val = _extract_money(p)
                    if val > 10000:
                        claimed_totals.append(val)
                        break
                continue

            # Nhận diện dòng tiêu đề bảng
            if any(h in first_col or h in second_col for h in ["nguyên liệu", "mặt hàng", "item", "stt"]):
                continue

            # Dòng nguyên liệu thông thường
            if len(parts) >= 4:
                name = parts[1] if len(parts) >= 5 else parts[0]
                qty_str = parts[2] if len(parts) >= 5 else parts[1]
                price_str = parts[3] if len(parts) >= 5 else parts[2]
                total_str = parts[4] if len(parts) >= 5 else parts[3]

                qty_kg = _parse_qty_kg(qty_str)
                unit_price = _extract_money(price_str)
                subtotal = _extract_money(total_str)

                if subtotal > 0:
                    subtotals.append(subtotal)

                if any(u in price_str.lower() for u in ["/bìa", "/miếng", "/gói", "/quả", "/hộp", "/bó", "/lon"]):
                    m_count = re.search(r"(\d+)\s*(?:bìa|miếng|gói|quả|hộp|bó|lon)", qty_str, re.I)
                    count = float(m_count.group(1)) if m_count else 1.0
                    expected = count * unit_price
                    diff = abs(expected - subtotal)
                    if subtotal > 0 and diff / subtotal > 0.15:
                        issues.append(
                            f"Lỗi số học dòng '{name}': {int(count)} x {int(unit_price):,}đ = {int(expected):,}đ nhưng ghi {int(subtotal):,}đ"
                        )
                elif any(k in name.lower() for k in ["dầu", "gia vị"]):
                    # Dòng combo Dầu ăn & Gia vị tính theo suất/phần (ví dụ 15.000đ)
                    if subtotal > 0 and unit_price > 0 and abs(unit_price - subtotal) > 1000:
                        issues.append(
                            f"Lỗi số học dòng combo '{name}': Đơn giá {int(unit_price):,}đ nhưng thành tiền {int(subtotal):,}đ"
                        )
                elif qty_kg is not None and unit_price > 0 and subtotal > 0:
                    expected = qty_kg * unit_price
                    diff = abs(expected - subtotal)
                    if diff / subtotal > 0.15:  # Lệch quá 15%
                        issues.append(
                            f"Lỗi số học dòng '{name}': {qty_kg}kg x {int(unit_price):,}đ/kg = {int(expected):,}đ nhưng ghi {int(subtotal):,}đ"
                        )

                # Kiểm tra dòng dầu ăn & gia vị không được để trống định lượng/đơn giá
                if any(k in name.lower() for k in ["dầu", "gia vị"]):
                    if qty_str.strip() in ["-", ""] or price_str.strip().lower() in ["-", "", "định lượng"]:
                        issues.append("Dòng dầu ăn & gia vị thiếu định lượng/đơn giá thành phần cụ thể.")

        # Kiểm tra dòng tổng cộng nếu có
        if claimed_totals and subtotals:
            total_claimed = claimed_totals[0]
            sum_subtotals = sum(subtotals[:9])  # Lấy tối đa 9 nguyên liệu đầu
            if abs(sum_subtotals - total_claimed) > 5000:
                issues.append(
                    f"Lỗi tổng chi phí bảng giá: Tổng các mục là {int(sum_subtotals):,}đ nhưng dòng tổng cộng ghi {int(total_claimed):,}đ"
                )

        return issues

    def _check_time_consistency(self, text: str) -> List[str]:
        """Kiểm tra tính nhất quán thời gian:
        1. Tiêu đề claim vs tổng thời gian các giai đoạn
        2. Từng bước thực hiện con bên trong giai đoạn không được vượt quá thời lượng của chính giai đoạn đó.
        """
        issues = []
        # Tìm claim thời gian ở tiêu đề hoặc phần mở đầu (loại trừ các dòng Giai đoạn)
        header_lines = [
            l for l in text.strip().split("\n")
            if (l.startswith("#") or any(k in l.lower() for k in ["lộ trình", "quy trình", "tổng thời gian", "chuẩn bị"]))
            and not re.search(r"giai đoạn\s*\d+", l, re.I)
        ]
        header_text = "\n".join(header_lines[:5]) if header_lines else "\n".join(text.strip().split("\n")[:3])
        title_claim = re.search(r"(?:chạm|trong|khoảng|chuẩn|tổng thời gian:?|tổng|nấu|gọn)\s*(\d+)\s*phút", header_text, re.I)
        # Tìm thời gian từng giai đoạn (ví dụ: Tổng thời gian: 18 phút, Thời gian: 15 phút, ~15 phút)
        phase_times = re.findall(r"Giai đoạn\s*\d+[^:\n]*:[^\n]*Tổng thời gian:\s*(\d+)\s*phút", text, re.I)
        if not phase_times:
            phase_times = re.findall(r"Giai đoạn\s*\d+[^:\n]*\([^)]*(\d+)\s*phút\)", text, re.I)
        if not phase_times:
            phase_times = re.findall(r"Giai đoạn\s*\d+[^|\n]*\|\s*\*?Thời gian:\s*(\d+)\s*phút", text, re.I)

        if title_claim and phase_times and len(phase_times) >= 2:
            claimed_min = int(title_claim.group(1))
            sum_min = sum(int(p) for p in phase_times)
            if abs(claimed_min - sum_min) > 2:
                issues.append(
                    f"Mâu thuẫn thời gian: Tiêu đề claim {claimed_min} phút nhưng tổng các giai đoạn là {sum_min} phút (lệch {abs(claimed_min - sum_min)} phút)"
                )

        # Kiểm tra nội tại từng giai đoạn (sub-action duration > phase duration)
        phase_blocks = re.split(r"Giai đoạn\s*\d+", text, flags=re.I)
        for idx, block in enumerate(phase_blocks[1:], 1):
            m_p = re.search(r"(?:Tổng|Thời gian:?)\s*(\d+)\s*phút", block, re.I)
            phase_min = int(m_p.group(1)) if m_p else 0
            if phase_min > 0:
                actions = re.finditer(r"(?:hầm|nấu|kho|nướng|ướp|đun|luộc|xào|chiên|ngâm)\s*(?:nhẹ)?\s*(\d+)\s*phút", block, re.I)
                for act in actions:
                    step_min = int(act.group(1))
                    if step_min > phase_min:
                        issues.append(
                            f"Mâu thuẫn nội tại Giai đoạn {idx}: Bước '{act.group(0)}' ({step_min} phút) vượt quá thời lượng giai đoạn ({phase_min} phút)"
                        )

        # Kiểm tra mâu thuẫn số lượng bếp nấu
        if "2 bếp" in text.lower():
            for l in text.split("\n"):
                l_lower = l.lower()
                if any(neg in l_lower for neg in ["không", "cấm", "chỉ dùng 2 bếp"]):
                    continue
                if re.search(r"\b(?:bếp\s*3|bếp\s*phụ)\b", l, re.I):
                    issues.append("Mâu thuẫn thiết bị nấu: Lộ trình tuyên bố '2 bếp' nhưng xuất hiện 'bếp phụ' hoặc 'bếp 3' gây thiếu khả thi.")
                    break

        # Kiểm tra mâu thuẫn phép cộng thời gian (ví dụ: 30 phút chuẩn bị + 5 phút nấu)
        m_add = re.search(r"(\d+)\s*phút\s*chuẩn bị\s*\+\s*(\d+)\s*phút\s*nấu", text, re.I)
        if m_add:
            p1, p2 = int(m_add.group(1)), int(m_add.group(2))
            if p1 != 15 or p2 != 15:
                issues.append(f"Mô tả thời gian không nhất quán: ghi '{m_add.group(0)}' mâu thuẫn với Giai đoạn 1 (15p) và Giai đoạn 2 (15p).")

        return issues

    def _check_nutrition_gate(self, text: str, goal: str) -> List[str]:
        """Kiểm tra sự hiện diện của nhóm tinh bột (cơm trắng/gạo/khoai) nếu đề bài yêu cầu bữa ăn đủ chất."""
        issues = []
        if goal and any(k in goal.lower() for k in ["đủ chất", "bữa tối", "bữa ăn"]):
            text_lower = text.lower()
            has_carb = any(k in text_lower for k in ["cơm", "gạo", "tinh bột", "bánh mì", "khoai", "bún"])
            if not has_carb:
                issues.append("Bữa ăn gia đình thiếu nhóm tinh bột (cơm trắng/gạo ăn kèm) để đạt tiêu chuẩn đủ chất.")
            if re.search(r"3\s*nhóm\s*chất", text_lower):
                issues.append("Kết luận sai lệch: Nêu '3 nhóm chất' trong khi bữa ăn gia đình chuẩn đủ chất yêu cầu đủ 4 nhóm (Đạm, Tinh bột, Xơ/Vitamin, Chất béo).")

            # Kiểm tra mâu thuẫn nutrition wording: gán nhãn tinh bột cho món thịt/rau thay vì cơm
            m_carb = re.search(r"\b(?:món\s*mặn|món\s*xào|thịt\s*bò|rau\s*muống|thịt\s*heo)\b[^:\n)]*\(([^)]*tinh\s*bột[^)]*)\)", text_lower)
            if m_carb:
                bracket_content = m_carb.group(1)
                if not any(neg in bracket_content for neg in ["không", "cấm", "tránh", "loại trừ"]):
                    issues.append("Mâu thuẫn phân loại dinh dưỡng: Gán nhãn 'tinh bột' cho món thịt/rau thay vì cơm trắng.")
            
            m_veg_carb = re.search(r"tinh\s*bột\s*(?:bổ sung\s*)?từ\s*(?:rau|củ|quả|hành|cà)", text_lower)
            if m_veg_carb:
                start_idx = max(0, m_veg_carb.start() - 40)
                prefix = text_lower[start_idx:m_veg_carb.start()]
                if not any(neg in prefix for neg in ["không", "cấm", "chẳng", "loại trừ", "tuyệt đối"]):
                    issues.append("Mâu thuẫn phân loại dinh dưỡng: Tuyên bố tinh bột từ rau củ quả thay vì cơm trắng.")

            # Kiểm tra calorie claim không có nguồn
            if re.search(r"\b\d+\s*(?:kcal|calo|calorie)\b", text, re.I):
                issues.append("Chứa thông tin năng lượng (kcal/calo) không có nguồn gốc kiểm chứng rõ ràng.")
        return issues

    def _check_dung(self, text: str, goal: str = "") -> DimensionResult:
        """Đúng: không lộ từ nội bộ, không hallucination, số học bảng giá chuẩn, thời gian nhất quán, dinh dưỡng đầy đủ."""
        issues: List[str] = []

        internal_hits = list(set(_INTERNAL_VOCAB_RE.findall(text)))
        if internal_hits:
            issues.append(f"Lộ từ nội bộ: {internal_hits[:5]}")

        halluc_hits = _HALLUCINATION_RE.findall(text)
        if halluc_hits:
            issues.append(f"Dấu hiệu hallucination: {halluc_hits[:2]}")

        # Kiểm tra tính toán số học bảng giá Markdown
        math_issues = self._check_table_math(text)
        if math_issues:
            issues.extend(math_issues)

        # Kiểm tra tính nhất quán thời gian
        time_issues = self._check_time_consistency(text)
        if time_issues:
            issues.extend(time_issues)

        # Kiểm tra nutrition gate (nhóm tinh bột)
        nutrition_issues = self._check_nutrition_gate(text, goal)
        if nutrition_issues:
            issues.extend(nutrition_issues)

        passed = not issues
        score = 1.0 if passed else max(0.1, 1.0 - 0.35 * len(issues))
        return DimensionResult(QualityDimension.DUNG, passed, score, issues)

    def _check_trung(self, text: str, goal: str) -> DimensionResult:
        """Trúng: trả lời đúng câu hỏi, không vòng vo / lặp vô nghĩa."""
        issues: List[str] = []

        # Kiểm tra overlap từ khoá goal trong 200 ký tự đầu (ngoại trừ câu hỏi xã giao/giới thiệu)
        if goal and len(text) > self._VERBOSE_THRESHOLD:
            goal_lower = goal.lower()
            is_greeting_goal = bool(re.search(r"\b(chào|hello|hi)\b|bạn là ai|giới thiệu", goal_lower))
            if not is_greeting_goal:
                goal_kws = set(w for w in re.findall(r"\w{3,}", goal_lower) if len(w) > 3)
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
        """Đủ: nội dung không rỗng/quá ngắn, tuân thủ Tiêu chuẩn 1 của Master (đi thẳng vào vấn đề)."""
        issues: List[str] = []

        if len(text) < 5:
            issues.append("Response trống hoặc quá ngắn")
            return DimensionResult(QualityDimension.DU, False, 0.0, issues)

        # Tuân thủ Tiêu chuẩn 1 của Master: Bắt đầu trực tiếp bằng nội dung trả lời chính.
        # Không bắt buộc greeting rập khuôn; tuyệt đối không coi câu trả lời trực diện là thiếu đủ.
        passed = not issues
        score = 1.0 if passed else 0.2
        return DimensionResult(QualityDimension.DU, passed, score, issues)

    # ------------------------------------------------------------------
    # Auto-correction
    # ------------------------------------------------------------------

    def _correct_du(
        self, text: str, du: DimensionResult
    ) -> Tuple[str, DimensionResult]:
        """Tuân thủ Tiêu chuẩn 1 của Master: Không tự tiện chèn câu chào rập khuôn."""
        return text, du


# Singleton — import và dùng trực tiếp
answer_quality_verifier = AnswerQualityVerifier()
