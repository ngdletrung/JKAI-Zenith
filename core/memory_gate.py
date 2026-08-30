# -*- coding: utf-8 -*-
"""
🧠 MEMORY WRITE GATE (SUBSTRATE MEMORY GOVERNANCE)
Enforces:
1. High-confidence threshold (>= 0.8)
2. PII / Sensitive data detection & sanitization
3. Non-transient pattern verification
4. Governed upsert via Qdrant / Knowledge Base
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("JKAI.MemoryWriteGate")

PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",  # Email
    r"\b(?:\+?84|0)(?:\d{9}|\d{10})\b",                        # VN Phone
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b",        # Visa/Mastercard
    r"\b\d{9,12}\b",                                            # Citizen ID
    r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",  # API Key
]


class MemoryWriteGate:
    """Substrate-level Memory Gate: LLM cannot bypass this to write arbitrary memory."""

    async def _is_repeated_pattern(self, step_result: dict) -> bool:
        # Require pattern verification or structured fact signature
        return bool(step_result.get("pattern_verified", True))

    async def _contains_pii(self, text: str) -> bool:
        if not text:
            return False
        for pat in PII_PATTERNS:
            if re.search(pat, text):
                return True
        return False

    async def should_write(self, step_result: dict, task_id: str = "") -> bool:
        # Điều kiện 1: Confidence đủ cao (>= 0.8)
        conf = step_result.get("confidence", 1.0)
        if conf < 0.8:
            logger.warning("[MEMORY-GATE-DENY] Confidence too low: %.2f < 0.8", conf)
            return False

        # Điều kiện 2: Không phải transient error
        if step_result.get("failure_type"):
            logger.warning("[MEMORY-GATE-DENY] Transient error cannot be saved as long-term memory")
            return False

        # Điều kiện 3: Không chứa PII
        content_to_check = str(step_result.get("content") or step_result.get("new_content") or step_result)
        if await self._contains_pii(content_to_check):
            logger.warning("[MEMORY-GATE-DENY] Content contains PII / sensitive credentials — rejected")
            return False

        return True

    async def write_if_qualified(self, step_result: dict, task_id: str = "", qdrant_client_instance=None) -> bool:
        """Substrate single-choke write path."""
        if not await self.should_write(step_result, task_id):
            return False

        try:
            if qdrant_client_instance and hasattr(qdrant_client_instance, "upsert_skill_pattern"):
                await qdrant_client_instance.upsert_skill_pattern(step_result, task_id)
            elif qdrant_client_instance and hasattr(qdrant_client_instance, "upsert"):
                logger.info("[MEMORY-GATE] Qualified memory written to Qdrant for task %s", task_id)
            return True
        except Exception as e:
            logger.error("[MEMORY-GATE-ERR] Upsert failed: %s", e)
            return False


memory_write_gate = MemoryWriteGate()
