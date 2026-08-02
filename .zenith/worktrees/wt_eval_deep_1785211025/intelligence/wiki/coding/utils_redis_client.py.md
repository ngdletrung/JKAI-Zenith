---
type: python_file
file: utils/redis_client.py
tags: []
---

# redis_client

"""
🧠 Redis Client V4 — Singleton + Safe Connection
- Singleton pattern để tránh tạo nhiều connection
- Auto-reconnect
- Logging và health check
"""

import os
import json
import logging
import time
from typing import Optional

import redis

logger = logging.getLogger("redis_client_v4")

_redis_inst

## Links to
- [[os]]
- [[json]]
- [[logging]]
- [[time]]
- [[typing]]
- [[redis]]

## Linked by
- [[utils/claim_manager.py]]
- [[utils/converter.py]]
- [[utils/crdt_engine.py]]
- [[utils/knowledge_brain.py]]
- [[utils/sovereign_guard.py]]
