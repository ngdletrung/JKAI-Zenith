# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — SEMANTIC INTENT FALLBACK ENGINE v1.0             ║
║   Định Tuyến Ngữ Nghĩa Bằng Trọng Số Vector & Cosine Similarity   ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Triệt Tiêu Nhược Điểm Của Từ Khóa Tĩnh. 🔍🧠⚡*
"""

import math
import re
from typing import Dict, List, Optional, Tuple

# Vector đặc trưng ngữ nghĩa cho từng Intent Mode (Semantic Prototypes)
_INTENT_PROTOTYPES: Dict[str, List[str]] = {
    "OFFICE": [
        "tạo bảng tính", "xuất tài liệu", "lập trang tính", "tính toán lương",
        "vẽ biểu đồ", "soạn thảo công văn", "lập hợp đồng", "xuất tệp tin",
        "bảng lương nhân viên", "trang trình bày", "báo cáo tài chính",
        "sửa đổi tệp tin", "định dạng văn bản", "bảng biểu doanh thu"
    ],
    "CODING": [
        "xây dựng chương trình", "thuật toán sắp xếp", "lập trình hệ thống",
        "giao diện api", "kết nối cơ sở dữ liệu", "sửa lỗi cú pháp",
        "tối ưu mã nguồn", "viết kịch bản tự động", "cấu hình máy chủ",
        "kiểm thử phần mềm", "docker compose container", "hàm xử lý logic"
    ],
    "REALTIME": [
        "tình hình thời tiết", "thông tin báo chí", "biến động giá cả",
        "thị trường tiền tệ", "kết quả bóng đá", "giá vàng thế giới",
        "sự kiện quốc tế", "nhiệt độ hiện tại", "chỉ số chứng khoán"
    ],
    "INTERNAL": [
        "tìm kiếm trong bộ nhớ", "lịch sử trao đổi trước", "tài liệu đã lưu",
        "hồ sơ cá nhân", "bản ghi nhớ", "thông tin hệ thống nội bộ"
    ],
    "REASONING": [
        "đánh giá ưu nhược điểm", "so sánh chi tiết", "lập kế hoạch dài hạn",
        "nghiên cứu sâu sắc", "tìm nguyên nhân gốc rễ", "phân tích kiến trúc",
        "dự báo xu hướng", "định hướng chiến lược", "phản biện logic"
    ],
    "SOCIAL": [
        "chúc một ngày tốt lành", "tâm sự trò chuyện", "bạn cảm thấy thế nào",
        "lời chào thân mật", "thăm hỏi sức khỏe", "cảm ơn sự giúp đỡ"
    ]
}


class SemanticFallbackEngine:
    """
    🔍 Động Cơ Định Tuyến Ngữ Nghĩa Siêu Tốc (Zero-GPU Lightweight Embeddings / TF-IDF Cosine).
    Hoạt động trong <1ms khi bộ từ khóa tĩnh không bắt được từ chính xác.
    """

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    @classmethod
    def _compute_tfidf_vector(cls, text: str, vocabulary: Dict[str, int]) -> List[float]:
        tokens = cls._tokenize(text)
        vec = [0.0] * len(vocabulary)
        for t in tokens:
            if t in vocabulary:
                vec[vocabulary[t]] += 1.0
        # Chuẩn hóa độ dài Euclidean
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @classmethod
    def classify_semantic(cls, text: str, threshold: float = 0.30) -> Optional[Tuple[str, float]]:
        """
        Tính độ tương đồng ngữ nghĩa giữa text đầu vào và các Intent Prototypes.
        Trả về (intent_name, confidence_score) hoặc None nếu không đủ ngưỡng.
        """
        if not text or len(text.strip()) < 5:
            return None

        # 1. Xây dựng bộ từ vựng chung
        vocab: Dict[str, int] = {}
        all_corpus = [text]
        for mode, prototypes in _INTENT_PROTOTYPES.items():
            all_corpus.extend(prototypes)

        idx = 0
        for doc in all_corpus:
            for word in cls._tokenize(doc):
                if word not in vocab:
                    vocab[word] = idx
                    idx += 1

        # 2. Vectorize text đầu vào
        input_vec = cls._compute_tfidf_vector(text, vocab)

        # 3. Tính Cosine Similarity với từng Intent Mode
        best_mode = None
        best_score = 0.0

        for mode, prototypes in _INTENT_PROTOTYPES.items():
            # Lấy trung bình cộng vector của các câu mẫu trong intent
            mode_vec = [0.0] * len(vocab)
            for proto in prototypes:
                p_vec = cls._compute_tfidf_vector(proto, vocab)
                for i in range(len(vocab)):
                    mode_vec[i] += p_vec[i]
            
            # Chuẩn hóa vector mode
            m_norm = math.sqrt(sum(v * v for v in mode_vec))
            if m_norm > 0:
                mode_vec = [v / m_norm for v in mode_vec]

            # Tính tích vô hướng Dot Product (Cosine Similarity)
            dot_product = sum(input_vec[i] * mode_vec[i] for i in range(len(vocab)))
            if dot_product > best_score:
                best_score = dot_product
                best_mode = mode

        if best_mode and best_score >= threshold:
            return best_mode, best_score

        return None


semantic_fallback_engine = SemanticFallbackEngine()
