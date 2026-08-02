---
type: python_file
file: ai-brain/critic.py
tags: []
---

# critic

import os
import json
import time
from core.utils.engine import engine
from core.utils.knowledge_brain import knowledge_brain
from core.config import settings
from redis_client import redis_safe

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "st

## Links to
- [[os]]
- [[json]]
- [[time]]
- [[core.utils.engine]]
- [[core.utils.knowledge_brain]]
- [[core.config]]
- [[redis_client]]
- [[prompt_forge]]

## Linked by
- [[ai-brain/main.py]]
- [[ai-brain/planner.py]]
