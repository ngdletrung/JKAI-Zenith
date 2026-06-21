---
type: python_file
file: test_run.py
tags: []
---

# test_run

import asyncio
import uuid
from datetime import datetime, timezone
import redis.asyncio as redis_async
from models.task import Task, TaskStatus

async def main():
    print("🚀 Bắt đầu giả lập hệ thống (End-to-End Test)...")
    
    # Kết nối đến Redis trong Docker
    redis = await redis_async.from

## Links to
- [[asyncio]]
- [[uuid]]
- [[datetime]]
- [[redis.asyncio]]
- [[models.task]]
