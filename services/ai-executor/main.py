from fastapi import FastAPI
import os
from executor import Executor

app = FastAPI(title="JKAI Executor Service", version="31.0")
executor = Executor()

from core.utils.engine import engine
from core.utils.hlc import hlc, HlcTimestamp

def sync_hlc_from_payload(payload: dict):
    """
    Đồng bộ đồng hồ lai (HLC) từ payload nhận được thưa Tổng Giám Đốc.
    """
    if not payload or not isinstance(payload, dict):
        return
    hlc_str = payload.get("hlc")
    if hlc_str:
        try:
            received_ts = HlcTimestamp.from_str(hlc_str)
            hlc.update(received_ts)
        except Exception as e:
            import logging
            logging.getLogger('EXECUTOR').error(f"❌ [HLC-SYNC-ERR]: {e}")

# 👑 [ELITE-IDENTITY]: Khẳng định đây là Lõi Thực thi & Tư duy mạnh nhất thưa Master
engine.is_brain_service = True
engine.current_service_url = engine.executor_url

@app.post("/execute")
async def execute_task(payload: dict):
    sync_hlc_from_payload(payload)
    task_id = payload.get("task_id", "unknown")
    steps = payload.get("steps", [])
    return await executor.run_steps(steps, task_id)

@app.post("/chat")
async def chat_endpoint(payload: dict):
    """🧠 [HIGH-POWER REASONING]: Cung cấp khả năng tư duy mạnh nhất thưa Master."""
    sync_hlc_from_payload(payload)
    role_type = os.getenv("EXECUTOR_ROLE", "ALPHA")
    return {
        "answer": await engine.call_chat(
            messages=payload.get("messages", []),
            role=payload.get("role", f"EXECUTOR_{role_type}"),
            model=payload.get("model"),
            json_mode=payload.get("json_mode", False),
            schema=payload.get("schema"),
            options=payload.get("options"),
            profile=payload.get("profile"),
            keep_alive=payload.get("keep_alive"),
            task_id=payload.get("task_id", "unknown"),
            images=payload.get("images"),
            lock_timeout=payload.get("lock_timeout", 60)
        )
    }

@app.post("/call_tool")
async def call_single_tool(payload: dict):
    sync_hlc_from_payload(payload)
    name = payload.get("name")
    args = payload.get("args", {})
    task_id = payload.get("task_id", "unknown")
    return await executor.call_tool(name, args, task_id)

@app.get("/health")
def health():
    return {"status": "healthy"}

