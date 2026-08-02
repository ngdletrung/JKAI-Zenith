# [ZENITH FILE DIRECTIVE]
# - File: core/os/memory_state.py
# - Role: Memory State representation v1 (Layer 3)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0 (Integrated)

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class MemoryState(BaseModel):
    reflex_cache_hit: bool = False
    conversation_summary: str = ""
    learned_patterns: List[str] = Field(default_factory=list)
