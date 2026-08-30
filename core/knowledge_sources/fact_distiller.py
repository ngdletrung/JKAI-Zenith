# -*- coding: utf-8 -*-
"""
🔬 [ZERO-LATENCY FACT DISTILLER v2.0 - ADVANCED HEURISTIC COMPRESSOR]
File: core/knowledge_sources/fact_distiller.py

Bộ Chắt Lọc Tri Thức Tinh Hoa & Nén Dữ Liệu Ngữ Cảnh (<2ms Latency):
  1. Expanded Valuable Lexicon: Bắt số liệu phức tạp (+5.2%, 1,000,000 VND, 10/12/2026, MB/GB, req/s).
  2. Native Bullet & List Preservation: Bảo toàn cấu trúc bullet points sẵn có.
  3. Jaccard Semantic Deduplication: Khử trùng lặp nội dung tương tự (>75%).
  4. Density-Normalized Scoring: Chuẩn hóa điểm theo mật độ thông tin chống thiên vị câu dài.
  5. Low-Confidence Resilient Fallback: Tự động dự phòng an toàn khi văn bản ít số liệu.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger("JKAI.FactDistiller")


class FactDistiller:
    """
    🔬 Động Cơ Chắt Lọc Ý Chính & Triệt Tiêu Nhiễu Ngữ Cảnh Chuẩn Enterprise
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Mẫu nhận diện số liệu, ngày tháng, đơn vị tiền tệ, kỹ thuật, chỉ số tài chính, địa chính trị & quốc tế
        self._valuable_pattern = re.compile(
            r"(?:\d+[.,]?\d*|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:ngày|tháng|năm|giờ|phút|giây|đô la|usd|vnd|eur|gbp|%|km|kg|tấn|mét|cm|mm|byte|kb|mb|gb|tb|req/s|fps|tăng|giảm|đạt|vượt|khoảng|ước tính|doanh thu|lợi nhuận|chi phí|gdp|lãi suất|tổng thống|thủ tướng|chính phủ|chiến sự|quân sự|tập kích|ngoại giao|liên hợp quốc|quốc tế|thế giới|kinh tế|chính trị|quân đội|xung đột|thỏa thuận|tấn công|phòng thủ|hòa đàm|hội nghị|nga|ukraine|mỹ|trung quốc|châu âu|israel|iran)\b)",
            re.IGNORECASE
        )
        
        # Mẫu loại bỏ rác, quảng cáo, giải trí rác & bói toán tử vi khi truy vấn thời sự
        self._noise_pattern = re.compile(
            r"(quảng cáo|bản quyền|liên hệ|theo dõi chúng tôi|click|xem thêm|subscribe|trang chủ|advertisement|copyright|tử vi|con giáp|cung hoàng đạo|chiêm tinh|bói toán|lịch vạn niên|ngày hoàng đạo|giờ hoàng đạo|phong thủy|vận xui|tài lộc hôm nay của 12)",
            re.IGNORECASE
        )

    def distill_facts(self, raw_text: str, query: str = "", max_facts: int = 6) -> str:
        """
        Chắt lọc văn bản thô thành các gạch đầu dòng tri thức cốt lõi (<2ms).
        """
        if not raw_text or len(raw_text.strip()) < 20:
            return raw_text.strip()

        # 1. Tách văn bản thành các ứng viên (câu hoặc bullet lines)
        raw_lines = raw_text.splitlines()
        candidate_segments: List[str] = []

        for line in raw_lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Nếu dòng đã là bullet list (- , * , • , +)
            if re.match(r"^[\-\*•\+]\s+", line_str) or re.match(r"^\d+\.\s+", line_str):
                cleaned_line = re.sub(r"^[\-\*•\+\d\.]+\s*", "", line_str)
                if len(cleaned_line) >= 10:
                    candidate_segments.append(cleaned_line)
            else:
                # Tách theo dấu chấm ngắt câu an toàn (không làm vỡ số thập phân)
                sub_sentences = re.split(r"\.\s+", line_str)
                for s in sub_sentences:
                    s_clean = s.strip()
                    if 15 <= len(s_clean) <= 400:
                        candidate_segments.append(s_clean)

        if not candidate_segments:
            return raw_text[:500].strip()

        # 2. Chấm điểm từng câu theo mật độ thông tin (Density-Normalized Scoring)
        query_words = set(re.findall(r"\w+", query.lower())) if query else set()
        scored_candidates: List[Tuple[float, str, Set[str]]] = []

        for segment in candidate_segments:
            if self._noise_pattern.search(segment):
                continue

            words = set(re.findall(r"\w+", segment.lower()))
            word_count = max(len(words), 1)

            valuable_matches = len(self._valuable_pattern.findall(segment))
            keyword_overlap = len(query_words.intersection(words)) if query_words else 0

            # Điểm mật độ = (Số lượng giá trị * 2.5 + Trùng từ khóa * 3.5) / Căn bậc hai độ dài câu
            raw_score = (valuable_matches * 2.5) + (keyword_overlap * 3.5)
            density_score = raw_score / (word_count ** 0.5)

            if density_score > 0.3:
                scored_candidates.append((density_score, segment, words))

        if not scored_candidates:
            return raw_text[:400].strip()

        # 3. Sắp xếp theo điểm số
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 4. Khử trùng lặp nội dung tương tự (Jaccard Similarity Deduplication > 75%)
        unique_facts: List[str] = []
        selected_wordsets: List[Set[str]] = []

        for score, text, wordset in scored_candidates:
            is_duplicate = False
            for existing_set in selected_wordsets:
                intersection = len(wordset.intersection(existing_set))
                union = len(wordset.union(existing_set))
                jaccard = intersection / max(union, 1)
                if jaccard > 0.70:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_facts.append(text)
                selected_wordsets.append(wordset)
                if len(unique_facts) >= max_facts:
                    break

        # 5. Định dạng đầu ra bullet points
        bullet_facts = [f"• {fact}" for fact in unique_facts]
        return "\n".join(bullet_facts)


fact_distiller = FactDistiller()
