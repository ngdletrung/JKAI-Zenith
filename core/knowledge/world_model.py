"""
JKAI ZENITH — KNOWLEDGE DOMAIN: WORLD MODEL
File: core/knowledge/world_model.py

World Model representing entities, states, relationships, and temporal provenance.
Ensures Cognitive Kernel maintains continuous state awareness across requests.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class EntityRelation:
    """Relationship between two entities in the World Model."""
    source_entity: str
    relation_type: str                   # "depends_on" | "has_component" | "currently_in_state" | "produced_by"
    target_entity: str
    confidence: float = 1.0
    provenance_event_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class WorldModel:
    """Centralized state & entity relationship world model."""

    def __init__(self):
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relations: List[EntityRelation] = []

    def set_entity_state(self, entity_id: str, state_data: Dict[str, Any]):
        """Record entity state in world model."""
        if entity_id not in self._entities:
            self._entities[entity_id] = {}
        self._entities[entity_id].update(state_data)
        self._entities[entity_id]["last_updated"] = time.time()

    def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity state."""
        return self._entities.get(entity_id)

    def add_relation(self, relation: EntityRelation):
        """Add relationship edge."""
        self._relations.append(relation)

    def get_relations_for_entity(self, entity_id: str) -> List[EntityRelation]:
        """Find all relations involving entity."""
        return [r for r in self._relations if r.source_entity == entity_id or r.target_entity == entity_id]
