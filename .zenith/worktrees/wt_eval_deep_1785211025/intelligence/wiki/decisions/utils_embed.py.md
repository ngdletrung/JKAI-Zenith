---
type: python_file
file: utils/embed.py
tags: []
---

# embed

import os
import httpx
import re
import asyncio
from typing import List, Optional

class Embedder:
    _instance = None
    _async_client = None
    _sync_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
        

## Links to
- [[os]]
- [[httpx]]
- [[re]]
- [[asyncio]]
- [[typing]]
- [[core.config]]

## Linked by
- [[qdrant_client.py - QdrantClientWrapper.qrank_select_agent]]
- [[qdrant_client.py - QdrantClientWrapper.qrank_select_skill]]
- [[utils/knowledge_manager.py - JKAIKnowledgeOrchestrator.smart_retrieve]]
- [[utils/reasoning_bank.py - ReasoningBank.memorize]]
- [[utils/reasoning_bank.py - ReasoningBank.recall]]
