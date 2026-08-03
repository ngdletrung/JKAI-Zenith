"""
JKAI ZENITH — KNOWLEDGE DOMAIN: ENTITY & REFERENCE RESOLVER
File: core/knowledge/entity_resolver.py

Resolves named entities, servers, files, and domain concepts from user prompts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ResolvedEntity:
    entity_name: str
    entity_type: str                   # "server" | "model" | "file" | "service" | "concept"
    canonical_id: str
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


class EntityResolver:
    """Resolves entities from natural language context."""

    def __init__(self):
        self._registry: Dict[str, ResolvedEntity] = {}

    def register(self, alias: str, entity: ResolvedEntity):
        self._registry[alias.lower()] = entity

    def resolve(self, mention: str) -> Optional[ResolvedEntity]:
        return self._registry.get(mention.lower().strip())
