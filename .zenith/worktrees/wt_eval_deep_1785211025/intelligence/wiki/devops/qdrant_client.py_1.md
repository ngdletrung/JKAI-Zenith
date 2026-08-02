---
type: python_file
file: qdrant_client.py
tags: []
---

# qdrant_client

import os
import httpx
import json
import uuid
import logging
import time
from typing import Any, List, Dict, Optional

logger = logging.getLogger("QdrantClient")

class QdrantClientWrapper:
    def __init__(self):
        from core.config import IS_DOCKER
        env_url = os.getenv("QDRANT_URL", "

## Links to
- [[os]]
- [[httpx]]
- [[json]]
- [[uuid]]
- [[logging]]
- [[time]]
- [[typing]]
- [[core.config]]
- [[core.utils.embed]]
