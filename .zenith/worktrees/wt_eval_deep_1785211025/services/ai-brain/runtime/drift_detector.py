# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/drift_detector.py
# - Role: Intent Drift Prevention (Sovereign Runtime)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Thiet ke bo tinh toan Cosine Distance dua tren TF-IDF thuan tuy cuc ky nhe va nhanh (0ms logic delay) de phat hien su lech huong y do (Semantic Drift).

import math
import re
from typing import List

class DriftDetector:
    """
    Canh Sat Sai Lech (Intent Drift Prevention)
    Ngan chan Planner/Executor tu y bien tau yeu cau ban dau.
    """
    def __init__(self):
        # Stopwords co ban de loc nhieu, tang do chinh xac so khop tu vung
        self.stopwords = {
            "hay", "lam", "cho", "toi", "de", "voi", "va", "cua", "la", "trong", "tren", "duoi", "duoc", "bi", "ra", "vao",
            "the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in", "on", "at", "for", "with", "by", "about"
        }

    def validate_proposal(self, parent_manifest_hash: str, current_manifest_hash: str):
        """Khoa Intent. De xuat cua Planner phai dua tren Manifest do Dispatcher goc sinh ra."""
        if parent_manifest_hash != current_manifest_hash:
            raise ValueError("[DRIFT-DETECTED]: Planner da co gang thay doi Intent hoac Risk cua Dispatcher!")

    def _tokenize(self, text: str) -> List[str]:
        """Tach tu, lam sach van ban, chuyen sang chu thuong."""
        text = text.lower()
        # Loai bo ky tu dac biet, chi giu lai chu cai, so va khoang trang
        cleaned = re.sub(r"[^\w\s]", " ", text)
        tokens = cleaned.split()
        # Loc stopwords va tu qua ngan
        return [t for t in tokens if t not in self.stopwords and len(t) > 1]

    def detect_semantic_drift(self, original_intent: str, proposed_tool: str) -> float:
        """
        Do do lech chuan Semantic giua Intent goc va Tool duoc chon bang khoang cach Cosine tu TF-IDF.
        Tra ve Drift Score tu 0.0 (Giong het ngu nghia) den 1.0 (Lech hoan toan).
        """
        if not original_intent or not proposed_tool:
            return 1.0

        tokens_intent = self._tokenize(original_intent)
        tokens_tool = self._tokenize(proposed_tool)

        if not tokens_intent or not tokens_tool:
            if original_intent.strip().lower() == proposed_tool.strip().lower():
                return 0.0
            return 1.0

        # Tap hop tat ca cac tu duy nhat
        vocabulary = list(set(tokens_intent + tokens_tool))

        # Tinh toan tan suat xuat hien (Term Frequency)
        tf_intent = {}
        tf_tool = {}
        for word in vocabulary:
            tf_intent[word] = tokens_intent.count(word) / len(tokens_intent)
            tf_tool[word] = tokens_tool.count(word) / len(tokens_tool)

        # Tinh IDF gia dinh dua tren 2 tai lieu nay
        idf = {}
        for word in vocabulary:
            doc_count = 0
            if word in tokens_intent:
                doc_count += 1
            if word in tokens_tool:
                doc_count += 1
            idf[word] = math.log(1 + (2 / doc_count))

        # Tinh toan vector TF-IDF
        vec_intent = []
        vec_tool = []
        for word in vocabulary:
            vec_intent.append(tf_intent[word] * idf[word])
            vec_tool.append(tf_tool[word] * idf[word])

        # Tinh Cosine Similarity
        dot_product = sum(a * b for a, b in zip(vec_intent, vec_tool))
        magnitude_intent = math.sqrt(sum(a * a for a in vec_intent))
        magnitude_tool = math.sqrt(sum(b * b for b in vec_tool))

        if magnitude_intent == 0 or magnitude_tool == 0:
            return 1.0

        similarity = dot_product / (magnitude_intent * magnitude_tool)
        
        # Drift Score = 1.0 - Cosine Similarity (Cosine Distance)
        drift_score = 1.0 - similarity
        
        return max(0.0, min(1.0, drift_score))
