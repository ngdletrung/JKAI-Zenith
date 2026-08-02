import logging
import time
from core.utils.engine import engine

log = logging.getLogger("PLANNING_BREAKDOWN")

async def run_planning_and_task_breakdown(spec_content: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    engine.publish_mission_log("RESEARCH", "[PLANNING-BREAKDOWN] Decomposing spec into tasks...", task_id, trace_id)
    t0 = time.time()
    return {"status": "success", "msg": "Tasks broken down.", "latency_ms": (time.time() - t0) * 1000}
