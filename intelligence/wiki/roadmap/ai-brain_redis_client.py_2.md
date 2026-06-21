---
type: python_file
file: ai-brain/redis_client.py
tags: []
---

# redis_client

import redis
import os
import json

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_host = os.getenv("REDIS_HOST")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_pass = os.getenv("REDIS_PASSWORD")
        if not redis

## Links to
- [[redis]]
- [[os]]
- [[json]]

## Linked by
- [[ai-brain/critic.py]]
- [[ai-brain/experience_distiller.py]]
- [[ai-brain/main.py]]
- [[ai-brain/planner.py]]
- [[ai-brain/receptionist.py]]
- [[ai-control-plane/hitl_manager.py]]
- [[ai-control-plane/main.py]]
- [[ai-control-plane/monologue.py]]
- [[ai-control-plane/pulse.py]]
- [[ai-control-plane/SOVEREIGN_CORE.py]]
- [[ai-control-plane/task_manager.py]]
- [[ai-executor/dag_executor.py]]
- [[ai-executor/executor.py]]
- [[ai-executor/tool_impls/sovereign.py]]
