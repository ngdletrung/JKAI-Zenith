# -*- coding: utf-8 -*-
"""
core/os/cognition/entity_stack.py
JKAI DEMS v1.0 — Multi-Turn Epistemic Entity Stack & Coreference Engine.

Provides ultra-fast (< 1ms) LIFO Entity resolution with turn-decay expiry.
Resolves ambiguous pronouns ("nó", "đó", "nước đó", "cuộc chiến đó", "vấn đề này",...)
directly to the active salient entity from prior conversational turns without LLM calls.
"""

from __future__ import annotations
import re
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JKAI.DEMS.EntityStack")


@dataclass
class StackEntity:
    name: str
    category: str = "GENERAL"
    turn: int = 0
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


class EntityStack:
    """
    🧠 Epistemic Entity Stack (LIFO with Turn Decay)
    - Quản lý các thực thể đàm thoại trọng tâm theo thứ tự LIFO.
    - Hỗ trợ giải quyết tham chiếu đại từ (Coreference Resolution).
    - Tự động thoái lui (Decay/Expiry) sau MAX_TURNS_EXPIRY (3 turns) nếu không được nhắc lại.
    """

    PRONOUN_PATTERNS = [
        (r"\b(hậu quả|tác động|ảnh hưởng|kết quả) của (nó|đó|cái đó|việc đó)\b", r"\1 của {entity}"),
        (r"\b(ở|tại|đối với|cho) (nước đó|quốc gia đó|bên đó)\b", r"\1 {entity}"),
        (r"\b(cuộc chiến|chiến sự|xung đột) (đó|này|ấy)\b", r"{entity}"),
        (r"\b(vấn đề|việc|chuyện|tình hình) (này|đó|ấy)\b", r"{entity}"),
        (r"\b(cái đó|việc đó|điều đó)\b", r"{entity}"),
        (r"\b(nó|chúng nó)\b", r"{entity}"),
    ]

    MAX_TURNS_EXPIRY = 3

    def __init__(self, max_size: int = 12):
        self.stack: deque[StackEntity] = deque(maxlen=max_size)
        self.current_turn: int = 0

    def add_entity(self, name: str, category: str = "GENERAL", confidence: float = 1.0) -> None:
        """Thêm một thực thể vào stack."""
        clean_name = name.strip()
        if not clean_name or len(clean_name) < 2:
            return
        
        self._clean_expired()
        
        # Nếu entity đã có trong stack, đưa lên đỉnh và cập nhật turn
        existing = [e for e in self.stack if e.name.lower() == clean_name.lower()]
        if existing:
            self.stack.remove(existing[0])
            
        entity = StackEntity(
            name=clean_name,
            category=category,
            turn=self.current_turn,
            confidence=confidence,
            timestamp=time.time()
        )
        self.stack.append(entity)
        logger.debug(f"[ENTITY-STACK] Added: '{clean_name}' [{category}] (Turn={self.current_turn})")

    def get_latest_entity(self, min_confidence: float = 0.5) -> Optional[StackEntity]:
        """Lấy thực thể gần nhất (LIFO) có độ tin cậy thỏa mãn."""
        self._clean_expired()
        valid = [e for e in self.stack if e.confidence >= min_confidence]
        return valid[-1] if valid else None

    def _clean_expired(self) -> None:
        """Xóa các thực thể quá cũ sau MAX_TURNS_EXPIRY turns."""
        cutoff_turn = self.current_turn - self.MAX_TURNS_EXPIRY
        self.stack = deque(
            [e for e in self.stack if e.turn >= cutoff_turn],
            maxlen=self.stack.maxlen
        )

    def resolve_coreference(self, text: str) -> str:
        """Thay thế đại từ mơ hồ trong câu hỏi bằng thực thể LIFO gần nhất."""
        if not text or len(text.strip()) < 3:
            return text

        latest_entity = self.get_latest_entity(min_confidence=0.6)
        if not latest_entity:
            return text

        resolved = text
        for pattern, template in self.PRONOUN_PATTERNS:
            replacement = template.format(entity=latest_entity.name)
            resolved = re.sub(pattern, replacement, resolved, flags=re.IGNORECASE)

        if resolved != text:
            logger.debug(f"[ENTITY-STACK] Coreference Resolved: '{text}' -> '{resolved}'")
        return resolved

    def advance_turn(self) -> None:
        """Chuyển sang turn kế tiếp."""
        self.current_turn += 1
        self._clean_expired()

    def clear(self) -> None:
        self.stack.clear()
        self.current_turn = 0


_global_entity_stack: Optional[EntityStack] = None


def get_entity_stack() -> EntityStack:
    global _global_entity_stack
    if _global_entity_stack is None:
        _global_entity_stack = EntityStack()
    return _global_entity_stack


def reset_entity_stack() -> None:
    global _global_entity_stack
    if _global_entity_stack is not None:
        _global_entity_stack.clear()
        _global_entity_stack = None
