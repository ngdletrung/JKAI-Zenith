import logging
import time
from core.utils.engine import engine

log = logging.getLogger("DOCUMENTATION_ADR")

async def run_documentation_and_adrs(decision: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    engine.publish_mission_log("RESEARCH", f"[ADR] Ghi nhận quyết định kiến trúc: {decision}", task_id, trace_id)
    t0 = time.time()
    return {"status": "success", "msg": "ADR recorded.", "latency_ms": (time.time() - t0) * 1000}
