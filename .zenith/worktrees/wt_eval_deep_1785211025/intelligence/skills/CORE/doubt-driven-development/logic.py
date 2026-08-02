import logging
import time
from core.utils.engine import engine

log = logging.getLogger("DOUBT_DRIVEN")

async def run_doubt_driven_development(claim: str, contract: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    engine.publish_mission_log("D3", f"[DOUBT-DRIVEN] Running D3 review on claim: {claim}", task_id, trace_id)
    t0 = time.time()
    # Call critic logic directly
    from critic import Critic
    critic = Critic()
    review = await critic.review_plan(claim, [{"tool": "doubt_driven", "args": {"claim": claim, "contract": contract}}])
    return {"status": "success", "review": review, "latency_ms": (time.time() - t0) * 1000}
