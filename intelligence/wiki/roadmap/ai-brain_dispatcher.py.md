---
type: python_file
file: ai-brain/dispatcher.py
tags: []
---

# dispatcher

import asyncio
import logging
import json
import re

from core.utils.engine import engine

logger = logging.getLogger(__name__)

def _get_fallback() -> dict:
    return {"skill": "skill_Hueic_tao_skill_de_xuat_theo_form", "id": "Hueic", "mode": "deep"}


class Dispatcher:
    """
    Điều phối nhiệm

## Links to
- [[asyncio]]
- [[logging]]
- [[json]]
- [[re]]
- [[core.utils.engine]]
- [[core.utils.knowledge_manager]]
- [[intent_classifier]]
- [[core.qdrant_client]]
- [[core.utils.embed]]

## Linked by
- [[ai-brain/main.py]]
- [[ai-brain/planner.py]]
- [[ai-brain/receptionist.py]]
