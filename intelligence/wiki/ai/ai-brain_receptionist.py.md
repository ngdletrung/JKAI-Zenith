---
type: python_file
file: ai-brain/receptionist.py
tags: []
---

# receptionist

import os
import json
import re
import asyncio
import time
import httpx
import redis
from core.utils.engine import engine
from core.utils.knowledge_brain import knowledge_brain
from core.config import settings
from dispatcher import Dispatcher
from enum import Enum
from pydantic import BaseModel, Fi

## Links to
- [[os]]
- [[json]]
- [[re]]
- [[asyncio]]
- [[time]]
- [[httpx]]
- [[redis]]
- [[core.utils.engine]]
- [[core.utils.knowledge_brain]]
- [[core.config]]
- [[dispatcher]]
- [[enum]]
- [[pydantic]]
- [[typing]]
- [[intent_classifier]]
- [[hashlib]]
- [[hmac]]
- [[redis_client]]
- [[core.utils.knowledge_manager]]
- [[semantic_memory]]

## Linked by
- [[ai-brain/main.py]]
