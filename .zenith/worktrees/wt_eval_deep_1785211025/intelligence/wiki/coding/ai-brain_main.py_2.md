---
type: python_file
file: ai-brain/main.py
tags: []
---

# main

import os
import json
import time as _time
import asyncio
import httpx
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BRAIN')

sys.path.append(os.getcwd())
# 🌐 [PATH-ALIGNMENT]: Tìm đường dẫn gốc của project
project_root = os.path.abspath(o

## Links to
- [[os]]
- [[json]]
- [[time]]
- [[asyncio]]
- [[httpx]]
- [[sys]]
- [[logging]]
- [[fastapi]]
- [[fastapi.responses]]
- [[core.utils.engine]]
- [[core.qdrant_client]]
- [[core.utils.tracing]]
- [[core.utils.failure_memory]]
- [[redis_client]]
- [[planner]]
- [[critic]]
- [[receptionist]]
- [[dispatcher]]
- [[core.utils.knowledge_brain]]
- [[uvicorn]]
- [[core.utils.embed]]

## Linked by
- [[ai-control-plane/hitl_manager.py]]
