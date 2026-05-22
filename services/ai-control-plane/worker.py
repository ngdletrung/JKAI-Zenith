"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH v4.1 — COGNITIVE WORKER ENGINE                     ║
║   Autonomous Background Task Execution & Orchestration           ║
║   Dedicated Queue Processor for ai_task_queue                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import json
import logging
from redis_client import get_redis, get_async_redis
from router import ServiceRouter
from hitl_manager import HITLManager
from task_manager import TaskManager
from core.utils.failure_memory import init_failure_memory
from core.utils.engine import engine

# 🛡️ [SYSTEM-LOGGING]
logger = logging.getLogger("Worker")
logging.basicConfig(level=logging.INFO)

async def start_worker():
    """🚀 [ZENITH-WORKER]: Khoi chay nơ-ron thuc thi độc lập."""
    logger.info("🏛️ [JKAI-ZENITH] v4.1 Cognitive Worker Engine Online.")
    
    # 💎 [RESOURCE-INIT]: Khoi tao cac tuyen synapse
    router = ServiceRouter()
    hitl = HITLManager(None)
    
    # Khoi tao TaskManager
    task_manager = TaskManager(redis_conn=get_redis(), async_redis_conn=None, router=router, hitl=hitl)
    
    # Ket noi Async Redis
    async_r = await get_async_redis()
    task_manager.async_redis = async_r
    hitl.redis = async_r
    
    # Khoi tao Failure Memory
    init_failure_memory(redis_client=get_redis())
    
    # 🚀 [WARMUP]: Khoi dong no-ron tinh nang
    try:
        await engine.warmup_all_models()
    except Exception as e:
        logger.warning(f"⚠️ [WARMUP-WARN]: {e}")

    # 🔗 [TASK-LOOP]: Bat dau vong lap hap thu nhiem vu
    await task_manager.start()

if __name__ == "__main__":
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("🛑 [WORKER]: Master da ngat mach. Dang tat he thong thưa Ngai.")
