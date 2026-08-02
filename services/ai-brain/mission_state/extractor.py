# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/extractor.py
# - Role: Fact Extraction & Truth Maintenance System (TMS)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import logging
from datetime import datetime
from typing import List, Dict, Any
from .schema import MissionFacts, FactItem

logger = logging.getLogger("JKAI.FactManager")

class FactManager:
    """Manages system beliefs & maintains logical consistency via a Truth Maintenance System (TMS)."""
    
    def add_fact(self, facts: MissionFacts, fact_id: str, content: str, dependencies: List[str] = None, confidence: float = 1.0):
        """Adds a new fact with potential dependencies on existing facts."""
        deps = dependencies or []
        
        # Verify if all dependencies are currently valid
        valid = True
        for dep in deps:
            if dep not in facts.facts_db or not facts.facts_db[dep].valid:
                valid = False
                logger.warning(f"⚠️ [TMS-WARN]: Fact '{fact_id}' depends on invalid/missing Fact '{dep}'. Initializing as invalid.")
                break

        item = FactItem(
            content=content,
            dependencies=deps,
            confidence=confidence,
            valid=valid,
            updated_at=datetime.utcnow()
        )
        facts.facts_db[fact_id] = item
        logger.info(f"📌 [FACT-ADDED]: {fact_id} -> '{content}' (valid={valid}, confidence={confidence})")

    def invalidate_fact(self, facts: MissionFacts, fact_id: str, reason: str = "Explicit retraction"):
        """Invalidates a fact and recursively invalidates all downstream dependent facts (TMS)."""
        if fact_id not in facts.facts_db:
            return

        item = facts.facts_db[fact_id]
        if not item.valid:
            return # Already invalid

        item.valid = False
        item.updated_at = datetime.utcnow()
        logger.info(f"🚫 [TMS-INVALIDATED]: {fact_id} due to: {reason}")

        # Find downstream dependent facts
        for fid, fitem in facts.facts_db.items():
            if fact_id in fitem.dependencies and fitem.valid:
                # Invalidate recursively
                self.invalidate_fact(facts, fid, reason=f"Dependency '{fact_id}' became invalid.")

    def get_valid_facts(self, facts: MissionFacts) -> Dict[str, str]:
        """Returns all facts that are currently logically valid."""
        return {fid: fitem.content for fid, fitem in facts.facts_db.items() if fitem.valid}
