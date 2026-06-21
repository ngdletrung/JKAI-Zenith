---
type: python_file
file: utils/purge_vram.py
tags: []
---

# purge_vram

import httpx
import asyncio
import os

async def purge_ollama():
    url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧹 [PURGE] Đang rà soát các model đang nạp...")
        try:
            resp = await clien

## Links to
- [[httpx]]
- [[asyncio]]
- [[os]]
