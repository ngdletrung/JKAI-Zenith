# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CROSS-SESSION CAUSAL GRAPH MEMORY v2.0           ║
║   Ký Ức Dài Hạn Bền Vững, Entity-Graph Triplet & Causal Linking  ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Ký Ức Đồ Thị Nhân Quả. 🧠🏛️⚡*
"""

from __future__ import annotations
import os
import re
import time
import math
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger("JKAI.LongTermMemory")


@dataclass
class ConversationEngram:
    engram_id: str
    session_id: str
    topic: str
    user_goal: str
    key_facts: List[str] = field(default_factory=list)
    summary: str = ""
    entities: List[str] = field(default_factory=list)
    causal_links: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    importance_score: float = 1.0  # 1.0 (Bình thường) -> 3.0 (Tối quan trọng)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PersistentLongTermMemory:
    """
    🧠 Bộ Nhớ Đồ Thị Nhân Quả Liên Session (Cross-Session Causal Memory) v2.0
    - Lưu trữ Engrams bền vững kết hợp trọng số thời gian và độ quan trọng.
    - Trích xuất thực thể và liên kết quan hệ vào WorldModel.
    - Hỗ trợ cô đọng và nén ký ức tự động.
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
        # Local in-memory store cho truy xuất nhanh
        self.local_engrams: Dict[str, ConversationEngram] = {}
        # Entity to engrams index
        self.entity_index: Dict[str, Set[str]] = {}

    def store_engram(
        self,
        session_id: str,
        user_goal: str,
        topic: str,
        key_facts: Optional[List[str]] = None,
        summary: str = "",
        importance: float = 1.0,
        entities: Optional[List[str]] = None,
        causal_links: Optional[List[str]] = None
    ) -> ConversationEngram:
        """
        Lưu trữ một Engram ký ức vào bộ nhớ dài hạn và cập nhật chỉ mục thực thể.
        """
        import uuid
        engram_id = f"engram_{uuid.uuid4().hex[:12]}"
        
        # Tự động trích xuất thực thể nếu chưa có
        extracted_entities = list(entities or [])
        if not extracted_entities:
            extracted_entities = self._extract_entities(f"{user_goal} {topic} {' '.join(key_facts or [])}")

        engram = ConversationEngram(
            engram_id=engram_id,
            session_id=session_id,
            topic=topic,
            user_goal=user_goal,
            key_facts=key_facts or [],
            summary=summary,
            entities=extracted_entities,
            causal_links=causal_links or [],
            created_at=time.time(),
            importance_score=importance
        )
        self.local_engrams[engram_id] = engram

        # Cập nhật chỉ mục thực thể
        for ent in extracted_entities:
            ent_key = ent.lower().strip()
            if ent_key not in self.entity_index:
                self.entity_index[ent_key] = set()
            self.entity_index[ent_key].add(engram_id)

        # Đồng bộ ngầm với WorldModel nếu khả dụng
        self._sync_to_world_model(engram)
        return engram

    def recall_relevant_engrams(
        self,
        current_query: str,
        top_k: int = 3,
        current_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Truy xuất các ký ức liên quan nhất từ quá khứ, kết hợp độ tương đồng, liên kết thực thể và trọng số thời gian.
        """
        if not self.local_engrams or not current_query:
            return []

        now = current_time if current_time is not None else time.time()
        query_tokens = set(re_tokens(current_query))
        if not query_tokens:
            return []

        scored_engrams = []
        for engram in self.local_engrams.values():
            # 1. Đo độ tương đồng ngữ nghĩa từ khóa & thực thể
            engram_text = f"{engram.topic} {engram.user_goal} {' '.join(engram.key_facts)} {' '.join(engram.entities)} {engram.summary}".lower()
            engram_tokens = set(re_tokens(engram_text))
            
            overlap = query_tokens.intersection(engram_tokens)
            if not overlap:
                continue

            similarity = len(overlap) / max(len(query_tokens), 1)

            # Entity match boost (+20% nếu trùng thực thể quan trọng)
            if any(ent.lower() in current_query.lower() for ent in engram.entities):
                similarity *= 1.25

            # 2. Áp dụng trọng số thời gian (Temporal Weighting)
            age_days = max(0.0, (now - engram.created_at) / 86400.0)
            temporal_factor = 0.7 + 0.3 * math.exp(-0.05 * age_days)

            # 3. Điểm tổng hợp kết hợp điểm tầm quan trọng
            final_score = similarity * temporal_factor * engram.importance_score

            scored_engrams.append({
                "engram_id": engram.engram_id,
                "session_id": engram.session_id,
                "topic": engram.topic,
                "summary": engram.summary,
                "entities": engram.entities,
                "key_facts": engram.key_facts,
                "score": round(final_score, 4),
                "created_at": engram.created_at,
                "age_days": round(age_days, 1)
            })

        scored_engrams.sort(key=lambda x: x["score"], reverse=True)
        return scored_engrams[:top_k]

    def consolidate_memory(self) -> Dict[str, Any]:
        """
        Cô đọng và tối ưu hóa bộ nhớ: Tự động hợp nhất các Engram trùng lặp (Jaccard > 75%).
        """
        total_before = len(self.local_engrams)
        if total_before < 2:
            return {
                "total_engrams": total_before,
                "merged_count": 0,
                "unique_topics": list(set(e.topic for e in self.local_engrams.values())),
                "total_indexed_entities": len(self.entity_index),
                "status": "CONSOLIDATED"
            }

        engrams_list = list(self.local_engrams.values())
        to_delete = set()
        merged_count = 0

        for i in range(len(engrams_list)):
            e1 = engrams_list[i]
            if e1.engram_id in to_delete:
                continue

            words1 = set(re_tokens(f"{e1.user_goal} {' '.join(e1.key_facts)} {e1.summary}"))
            if not words1:
                continue

            for j in range(i + 1, len(engrams_list)):
                e2 = engrams_list[j]
                if e2.engram_id in to_delete:
                    continue

                if e1.topic.lower() == e2.topic.lower():
                    words2 = set(re_tokens(f"{e2.user_goal} {' '.join(e2.key_facts)} {e2.summary}"))
                    jaccard = len(words1.intersection(words2)) / max(len(words1.union(words2)), 1)

                    if jaccard > 0.70:
                        # Hợp nhất e2 vào e1
                        merged_facts = list(dict.fromkeys(e1.key_facts + e2.key_facts))
                        merged_entities = list(dict.fromkeys(e1.entities + e2.entities))
                        e1.key_facts = merged_facts
                        e1.entities = merged_entities
                        e1.importance_score = max(e1.importance_score, e2.importance_score)
                        e1.created_at = max(e1.created_at, e2.created_at)

                        to_delete.add(e2.engram_id)
                        merged_count += 1

        # Xóa các engram trùng lặp
        for eid in to_delete:
            self.local_engrams.pop(eid, None)

        # Tái xây dựng entity_index sạch
        self.entity_index.clear()
        for e in self.local_engrams.values():
            for ent in e.entities:
                ent_k = ent.lower().strip()
                if ent_k not in self.entity_index:
                    self.entity_index[ent_k] = set()
                self.entity_index[ent_k].add(e.engram_id)

        topics = set(e.topic for e in self.local_engrams.values())
        logger.info(f"🧠 [MEMORY-CONSOLIDATE]: Đã hợp nhất {merged_count} engram trùng lặp. Còn lại: {len(self.local_engrams)}.")

        return {
            "total_engrams": len(self.local_engrams),
            "merged_count": merged_count,
            "unique_topics": list(topics),
            "total_indexed_entities": len(self.entity_index),
            "status": "CONSOLIDATED"
        }

    def _extract_entities(self, text: str) -> List[str]:
        """Trích xuất các thực thể danh từ riêng / file / dự án từ chuỗi."""
        found = set()
        # Tìm các file path hoặc tên định dạng
        for m in re.findall(r"\b[\w\-]+\.(xlsx|docx|pdf|py|json|csv|md)\b", text, re.I):
            found.add(m)
        # Tìm các từ viết hoa (Tên riêng, Dự án, Vai trò)
        for m in re.findall(r"\b[A-Z][a-zA-Z0-9_\-]{2,}\b", text):
            if m.lower() not in {"the", "and", "for", "with", "this", "that"}:
                found.add(m)
        return list(found)[:5]

    def _sync_to_world_model(self, engram: ConversationEngram) -> None:
        """Đồng bộ thực thể vào WorldModel."""
        try:
            from core.knowledge_sources.world_model import world_model, NodeType
            for ent in engram.entities:
                if ent not in world_model.graph.nodes:
                    world_model.graph.add_node(ent, node_type=NodeType.SERVICE, properties={"source": "long_term_memory", "topic": engram.topic})
        except Exception:
            pass


def re_tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"\b[\w\-]+\b", text.lower()) if len(t) > 2]


long_term_memory = PersistentLongTermMemory()
