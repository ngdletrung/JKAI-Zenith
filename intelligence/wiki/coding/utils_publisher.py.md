---
type: python_file
file: utils/publisher.py
tags: []
---

# publisher

import json
import time
from core.redis_client import redis_safe

class Publisher:
    """
    📡 [PUBLISHER]: Giao thức truyền tin nơ-ron.
    Đảm bảo mọi thông điệp từ AI Brain được phát tới Dashboard thời gian thực.
    """
    def publish(self, tag: str, msg: str, task_id: str = "syst

## Links to
- [[json]]
- [[time]]
- [[core.redis_client]]
