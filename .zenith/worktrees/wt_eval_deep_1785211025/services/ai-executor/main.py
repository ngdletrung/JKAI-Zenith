import os
import json
import time
from fastapi import FastAPI, Request
from executor import Executor

app = FastAPI(title="JKAI Executor Service", version="31.0")
executor = Executor()

from core.utils.engine import engine
from core.utils.hlc import hlc, HlcTimestamp

# 🏛️ [RULES-INGESTION]: Tự động nạp API Keys từ rules_software.md thưa Master
engine.load_software_rules()

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

@app.post("/v1/chat/completions")
async def openai_completions(request: Request):
    """
    🌉 [OPENAI-PROXY]: Giao diện tương thích OpenAI cho các đặc vụ ngoại vi (như OpenHands).
    Tuân thủ nguyên tắc: Không set cứng model, gọi theo Role EXECUTOR.
    Tận dụng Smart Fallback của engine.py thưa Master.
    """
    payload = await request.json()
    role_type = os.getenv("EXECUTOR_ROLE", "ALPHA")
    role = f"EXECUTOR_{role_type}"
    
    messages = payload.get("messages", [])
    model_name = payload.get("model", "executor")
    
    # 🧠 Gọi engine để xử lý thông minh (bao gồm fallback và hardware affinity)
    response_text = await engine.call_chat(
        messages=messages,
        role=role,
        task_id=payload.get("user", "openhands_internal")
    )
    
    # 📝 Trả về định dạng chuẩn OpenAI
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }

@app.post("/call_tool")
async def call_single_tool(payload: dict):
    sync_hlc_from_payload(payload)
    name = payload.get("name")
    args = payload.get("args", {})
    task_id = payload.get("task_id", "unknown")
    trace_id = payload.get("trace_id", "system")
    return await executor.call_tool(name, args, task_id, trace_id=trace_id)

@app.post("/invalidate_cache")
async def invalidate_cache_endpoint():
    """Xóa module cache sau khi sửa skill/repo trên disk."""
    executor.router.invalidate_cache()
    return {"status": "success", "msg": "Module cache invalidated"}


@app.get("/health")
def health():
    return {"status": "healthy"}
