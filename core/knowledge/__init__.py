"""
JKAI ZENITH — KNOWLEDGE / WORLD PLANE (PLANE 3)
Directory: core/knowledge/

Responsibility:
    Epistemic foundation of JKAI: Memory Fabric, Qdrant Client, RAG,
    World Model, Entity Resolver, and Tool/Skill Registry.

Constitutional Invariant:
    Modules in core/knowledge provide context and tool definitions.
    They must NEVER depend on model routing or compute hardware details.
"""

from core.qdrant_client import QdrantClientWrapper, qdrant_client

__all__ = ["QdrantClientWrapper", "qdrant_client"]

