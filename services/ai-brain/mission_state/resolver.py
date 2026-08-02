# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/resolver.py
# - Role: Entity and Anaphora Resolver with Confidence Stack
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import re
import logging
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger("JKAI.EntityResolver")

class EntityResolver:
    """Resolves anaphora (e.g. "it", "that file", "this error") using active context stack."""
    def __init__(self):
        # Local heuristic rules for common pronouns
        self.pronoun_patterns = re.compile(
            r"\b(it|that file|the file|this file|the error|this error|nó|file đó|cái đó|lỗi đó|lỗi này|file này|đối tượng này|cái này)\b", 
            re.IGNORECASE
        )

    def resolve(self, text: str, entity_stack: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
        """
        Resolves entity reference from user utterance and the active entity stack.
        Returns:
            Tuple[ResolvedEntityName, ConfidenceScore]
        """
        match = self.pronoun_patterns.search(text)
        if not match:
            # Check if text directly mentions an entity in stack
            for entry in reversed(entity_stack):
                entity = entry.get("entity")
                if entity and entity.lower() in text.lower():
                    return entity, 1.0
            return None, 1.0 # No pronoun, no direct match

        pronoun = match.group(0).lower()
        if not entity_stack:
            logger.warning(f"🔍 [RESOLVER-WARN]: Pronoun '{pronoun}' found, but entity stack is empty.")
            return None, 0.0

        # Heuristics:
        # If user refers to "lỗi" (error), search stack for error entities
        # If user refers to "file", search stack for file entities
        is_file_ref = "file" in pronoun
        is_error_ref = "lỗi" in pronoun or "error" in pronoun

        for entry in reversed(entity_stack):
            entity = entry.get("entity", "")
            confidence = entry.get("confidence", 1.0)
            
            # Simple heuristic classification
            is_file = entity.endswith((".py", ".js", ".ts", ".json", ".txt", ".md", ".yml", ".yaml"))
            is_error = "error" in entity.lower() or "exception" in entity.lower() or "fail" in entity.lower()

            if is_file_ref and is_file:
                return entity, confidence * 0.95
            elif is_error_ref and is_error:
                return entity, confidence * 0.95
            elif not is_file_ref and not is_error_ref:
                # General pronoun "it" -> return the topmost entity
                return entity, confidence * 0.90

        # Fallback to topmost
        topmost = entity_stack[-1]
        return topmost.get("entity"), topmost.get("confidence", 1.0) * 0.70
