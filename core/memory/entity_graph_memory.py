# -*- coding: utf-8 -*-
"""
🕸️ [GRAPH MEMORY & ENTITY-RELATIONSHIP ENGINE v1.0]
File: core/memory/entity_graph_memory.py

Hệ Thống Đồ Thị Nhận Thức & Mối Quan Hệ Thực Thể (Trụ Cột 10):
  1. Knowledge Graph Triplets: Lưu trữ bộ ba (Subject, Predicate, Object).
  2. Multi-Hop Graph Traversal: Truy vấn quan hệ lân cận (1-hop, 2-hop) để suy diễn logic.
  3. Graph-Augmented RAG Context: Bơm đồ thị tri thức trực tiếp vào ngữ cảnh suy luận.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Tuple

logger = logging.getLogger("JKAI.GraphMemory")


@dataclass
class EntityTriplet:
    subject: str
    predicate: str
    object_val: str
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)


class EntityRelationshipGraphMemory:
    """
    🕸️ Đồ Thị Tri Thức Quan Hệ Thực Thể Nhẹ
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
        # Danh sách triplets: subject -> list of (predicate, object)
        self.adjacency_list: Dict[str, List[Tuple[str, str]]] = {}
        # Inverted index: object -> list of (subject, predicate)
        self.reverse_adjacency_list: Dict[str, List[Tuple[str, str]]] = {}

    def add_relationship(self, subject: str, predicate: str, object_val: str) -> None:
        """Thêm một cạnh quan hệ vào đồ thị."""
        s = subject.strip().lower()
        p = predicate.strip().lower()
        o = object_val.strip().lower()

        if s not in self.adjacency_list:
            self.adjacency_list[s] = []
        if (p, o) not in self.adjacency_list[s]:
            self.adjacency_list[s].append((p, o))

        if o not in self.reverse_adjacency_list:
            self.reverse_adjacency_list[o] = []
        if (s, p) not in self.reverse_adjacency_list[o]:
            self.reverse_adjacency_list[o].append((s, p))

    def query_entity_relations(self, entity_name: str, max_hops: int = 2) -> List[str]:
        """
        Truy vấn toàn bộ các mối quan hệ trực tiếp (1-hop) và gián tiếp (2-hop) của thực thể.
        """
        target = entity_name.strip().lower()
        if target not in self.adjacency_list and target not in self.reverse_adjacency_list:
            return []

        insights: List[str] = []

        # 1-Hop: Forward relations
        for p, o in self.adjacency_list.get(target, []):
            insights.append(f"[{entity_name.capitalize()}] --({p})--> [{o.capitalize()}]")
            
            # 2-Hop: Traversal
            if max_hops >= 2:
                for p2, o2 in self.adjacency_list.get(o, []):
                    if o2 != target:
                        insights.append(f"└─ [{o.capitalize()}] --({p2})--> [{o2.capitalize()}]")

        # 1-Hop: Inverted relations
        for s, p in self.reverse_adjacency_list.get(target, []):
            insights.append(f"[{s.capitalize()}] --({p})--> [{entity_name.capitalize()}]")

        return insights

    def build_graph_context_for_prompt(self, query: str) -> str:
        """Tìm các thực thể trong câu hỏi và sinh đoạn ngữ cảnh đồ thị bổ trợ."""
        found_relations = []
        q_lower = query.lower()

        # Quét các thực thể đã biết trong câu hỏi
        known_entities = set(self.adjacency_list.keys()).union(set(self.reverse_adjacency_list.keys()))
        for entity in known_entities:
            if entity in q_lower:
                rels = self.query_entity_relations(entity, max_hops=2)
                found_relations.extend(rels)

        if not found_relations:
            return ""

        unique_rels = list(dict.fromkeys(found_relations))
        return (
            "\n[KNOWLEDGE GRAPH RELATIONS]:\n" +
            "\n".join(unique_rels[:8]) + "\n"
        )


graph_memory = EntityRelationshipGraphMemory()
