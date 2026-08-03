"""
JKAI ZENITH — KNOWLEDGE DOMAIN: REFERENCE RESOLVER
File: core/knowledge/reference_resolver.py

Resolves anaphora and contextual references ("nó", "cái đó", "model này", "server kia")
to canonical entities in conversation history.
"""

from typing import Dict, Any, Optional, List


class ReferenceResolver:
    """Anaphora and contextual reference resolver."""

    def resolve_reference(self, reference: str, history: List[Dict[str, Any]]) -> Optional[str]:
        """Resolves pronouns like 'nó', 'cái đó' to the last mentioned entity."""
        ref_lower = reference.lower().strip()
        pronouns = ["nó", "cái đó", "cái này", "file đó", "model đó", "server đó"]
        if ref_lower in pronouns and history:
            # Inspect last assistant/user message for mentioned entities
            for msg in reversed(history):
                content = msg.get("content", "")
                if content:
                    return content.split()[0] if content.split() else content
        return reference
