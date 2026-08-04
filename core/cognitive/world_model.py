"""
JKAI ZENITH v3 — ADAPTIVE COGNITION LAYER: WORLD MODEL (v3.0)
File: core/cognitive/world_model.py

Mô hình thế giới bền vững (Persistent World Model) duy trì trạng thái thực thể,
mối quan hệ, sự kiện và độ tin cậy giữa nhiều Mission.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time

logger = logging.getLogger("jkai.cognitive.world_model")


@dataclass
class EntityState:
    entity_id: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    provenance: str = "PERCEIVED"
    updated_at: float = field(default_factory=time.time)


@dataclass
class CausalEvent:
    event_id: str
    event_type: str
    description: str
    timestamp: float = field(default_factory=time.time)


class WorldModel:
    """Mô Hình Thế Giới Bền Vững (Persistent World Model)."""

    _entities: Dict[str, EntityState] = {}
    _event_log: List[CausalEvent] = []

    @classmethod
    def update_entity(cls, entity_id: str, entity_type: str, attributes: Dict[str, Any], provenance: str = "EXECUTION") -> EntityState:
        """
        Cập nhật hoặc khởi tạo trạng thái thực thể trong mô hình thế giới.
        """
        if entity_id in cls._entities:
            cls._entities[entity_id].attributes.update(attributes)
            cls._entities[entity_id].updated_at = time.time()
            cls._entities[entity_id].provenance = provenance
        else:
            cls._entities[entity_id] = EntityState(
                entity_id=entity_id,
                entity_type=entity_type,
                attributes=attributes,
                provenance=provenance
            )

        logger.info(f"🌐 [WORLD-MODEL]: Updated entity '{entity_id}' ({entity_type}) with attributes={attributes}")
        return cls._entities[entity_id]

    @classmethod
    def get_entity(cls, entity_id: str) -> Optional[EntityState]:
        """Truy vấn thực thể từ mô hình thế giới."""
        return cls._entities.get(entity_id)

    @classmethod
    def record_event(cls, event_type: str, description: str) -> CausalEvent:
        """Ghi nhận sự kiện làm thay đổi mô hình thế giới."""
        ev = CausalEvent(
            event_id=f"ev_{int(time.time()*1000)}",
            event_type=event_type,
            description=description
        )
        cls._event_log.append(ev)
        logger.info(f"📜 [WORLD-MODEL-EVENT]: {event_type} - {description}")
        return ev

    @classmethod
    def clear_state(cls):
        """Reset sạch World Model (phục vụ testing isolation)."""
        cls._entities.clear()
        cls._event_log.clear()
