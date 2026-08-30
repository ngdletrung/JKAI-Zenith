# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ACTIVE LEARNING INTENT ENGINE v1.0               ║
║   Động Cơ Tự Học Từ Vựng Thực Tế & Đề Xuất Bổ Sung Lexicons     ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tiến Hóa Hệ Thần Kinh Ngôn Ngữ JKAI. 🧬🧠📚*
"""

import os
import re
import yaml
import logging
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("JKAI.ActiveLearner")


class ActiveLearningIntentEngine:
    """
    🧬 Động cơ Tự Học Ý Định:
    1. Ghi nhận các câu hỏi thực tế của Master khi độ tin cậy thấp hoặc rơi vào GENERAL.
    2. Rút trích cụm từ N-gram có tần suất cao.
    3. Đề xuất bổ sung từ khóa mới vào lexicon YAML hoặc tự động nạp.
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
        self.recorded_queries: List[Dict[str, Any]] = []
        self.lexicon_dir = os.path.join(os.path.dirname(__file__), "lexicons")

    def record_query(self, goal: str, mode: str, confidence: float, tags: List[str]):
        """Ghi nhận câu hỏi vào nhật ký học tập chủ động."""
        if not goal or len(goal.strip()) < 5:
            return
        self.recorded_queries.append({
            "goal": goal.strip(),
            "mode": mode,
            "confidence": confidence,
            "tags": tags
        })
        # Giới hạn bộ đệm 1000 câu gần nhất
        if len(self.recorded_queries) > 1000:
            self.recorded_queries.pop(0)

    def extract_candidate_keywords(self, target_category: str = "office", min_freq: int = 2) -> List[str]:
        """Trích xuất các cụm từ (2-3 words) xuất hiện lặp lại trong các câu hỏi thuộc category."""
        category_queries = [
            q["goal"].lower() for q in self.recorded_queries
            if q["mode"] == target_category.upper() or target_category.upper() in q["tags"]
        ]
        if not category_queries:
            return []

        # Rút trích bi-grams và tri-grams
        ngram_counter = Counter()
        for q in category_queries:
            words = re.findall(r"\w+", q)
            # Bi-grams
            for i in range(len(words) - 1):
                bg = f"{words[i]} {words[i+1]}"
                if len(bg) >= 6:
                    ngram_counter[bg] += 1
            # Tri-grams
            for i in range(len(words) - 2):
                tg = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(tg) >= 9:
                    ngram_counter[tg] += 1

        candidates = [phrase for phrase, count in ngram_counter.items() if count >= min_freq]
        return candidates

    def append_keyword_to_lexicon(self, category: str, new_keyword: str) -> bool:
        """Bổ sung từ khóa mới vào file YAML tương ứng."""
        yaml_path = os.path.join(self.lexicon_dir, f"{category.lower()}.yaml")
        if not os.path.exists(yaml_path):
            return False

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            keywords = data.get("keywords", [])
            clean_kw = new_keyword.strip().lower()
            if clean_kw not in [k.lower() for k in keywords]:
                keywords.append(clean_kw)
                data["keywords"] = keywords
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"🧬 [ACTIVE-LEARNER]: Appended '{clean_kw}' to {category}.yaml")
                return True
        except Exception as e:
            logger.error(f"[ACTIVE-LEARNER] Lỗi ghi lexicon {category}.yaml: {e}")
        return False


active_learning_engine = ActiveLearningIntentEngine()
active_learner = active_learning_engine
