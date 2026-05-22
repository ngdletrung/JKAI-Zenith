from fastapi import FastAPI
import asyncio
import os
import json
import time
from task_manager import TaskManager
from router import ServiceRouter
from hitl_manager import HITLManager
from redis_client import redis_safe, get_redis
from SOVEREIGN_CORE import SovereignCore
import logging
import re
import unicodedata

# 🛡️ [SYSTEM-LOGGING]: Centralized system logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

VALID_MODES = {"fast", "deep", "agentic", "auto"}

app = FastAPI(title="JKAI ZENITH SINGULARITY v1.0 Elite (since 01/05/2026)", version="v1.0")

# Global instances
router = ServiceRouter()
hitl = HITLManager(None)
# Initialize TaskManager with placeholder
task_manager = TaskManager(redis_conn=get_redis(), async_redis_conn=None, router=router, hitl=hitl)
sovereign = SovereignCore(task_manager)

@app.on_event("startup")
async def startup():
    # 💎 [NEURAL-PATHWAY-INIT]: Asynchronous synapse configuration
    from redis_client import get_async_redis
    async_r = await get_async_redis()
    task_manager.async_redis = async_r
    hitl.redis = async_r
    
    # 🔗 [WORKER-DECOUPLING]: Task Manager operationalized via worker.py
    # asyncio.create_task(task_manager.start())
    
    from pulse import start_pulse
    asyncio.create_task(start_pulse())
    
    from monologue import start_monologue_loop
    asyncio.create_task(start_monologue_loop())
    
    # 🚀 [NEURAL WARMUP]: Activating resident neural clusters
    try:
        import sys
        # 🌐 [PATH-ALIGNMENT]: Project root resolution
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if project_root not in sys.path:
            sys.path.append(project_root)
        
        from core.utils.engine import engine
        from core.utils.failure_memory import init_failure_memory
        init_failure_memory(redis_client=get_redis())
        # ⏳ [GUARDIAN-GRACE-PERIOD]: Stabilizing network infrastructure (30s)
        async def delayed_warmup():
            await asyncio.sleep(30)
            await engine.warmup_all_models()
        asyncio.create_task(delayed_warmup())
    except Exception as e:
        print(f"⚠️ [WARMUP ERROR]: {str(e)}")

    # 🔐 [HARDWARE-INTEGRITY-CHECK]: Hardware fingerprint verification
    hw_status = sovereign.check_hardware_integrity()
    if hw_status != "MATCH":
        sovereign.is_boot_locked = True
        msg = f"🚨 [SYSTEM-LOCK]: UNKNOWN DEVICE DETECTED ({hw_status}). SYSTEM ENFORCED LOCKDOWN.\n\nPlease provide administrative authorization code."
    else:
        msg = "🏛️ [JKAI ZENITH SINGULARITY v1.0 Elite (since 01/05/2026)] 🏛️\n\nOperational status: Optimal. Sovereign autonomy initialized."
        
        # 🧹 [BOOT-PERSISTENCE]: Historical trace preservation
        # try:
        #     sovereign._flush_all_history()
        # except: pass

    tg_token = os.getenv("TELEGRAM_TOKEN")
    master_id = os.getenv("MASTER_ID")
    if tg_token and master_id:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={
                    "chat_id": master_id,
                    "text": msg
                })
        except: pass
    
    # Synchronize startup signal to Dashboard
    task_manager._log("SYSTEM", msg.replace("\n\n", " "), stealth=True)
    
@app.post("/commander/cancel")
@app.post("/commander/stop")
async def commander_stop_or_cancel():
    """🛑 EMERGENCY STOP PROTOCOL"""
    return await sovereign.emergency_cancel()

@app.post("/commander/ready")
async def commander_ready():
    """🔓 READY PROTOCOL: Clearing inhibit signals for new session."""
    def _clear(r):
        r.delete("agent:stop_signal")
    redis_safe(_clear)
    return {"status": "ok", "msg": "System Ready"}

@app.post("/commander/flush")
async def commander_flush():
    """🧹 SYSTEM INITIALIZATION PROTOCOL."""
    sovereign._flush_all_history()
    return {"status": "ok", "msg": "System Initialization Complete"}


@app.post("/commander/shutdown")
async def commander_shutdown(payload: dict):
    """🔌 SUPREME SHUTDOWN PROTOCOL"""
    return await sovereign.supreme_shutdown(payload.get("code"))

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/submit_task")
@app.post("/submit")
async def submit_task(payload: dict):
    """
    [GATEWAY-INGESTION]: Ingesting and initializing neural runtime.
    """
    from core.utils.reflex_gate import ReflexGate
    
    goal_raw = payload.get("goal", "")
    # 🔍 [DEBUG-GATE]: Xem Master đang gửi gì
    logger.info(f"🔍 [GATE-IN]: Raw Goal: '{goal_raw}'")
    
    # 🚀 [STEP-0]: ABSOLUTE ROOT REFLEX (Chặn đứng tại Gốc)
    if ReflexGate.is_social(goal_raw):
        # Tạo Task ID ảo để Dashboard nhận diện
        fake_tid = f"reflex_{int(time.time())}"
        ans = ReflexGate.get_response(goal_raw)
        
        # 👑 [MASTER-ECHO]: Luôn publish tin nhắn Master trước khi trả lời
        source = payload.get("source", "WEB")
        master_tag = "MASTER_TELE" if source == "TELEGRAM" else "MASTER_WEB" if source == "WEB" else "MASTER"
        
        master_payload = json.dumps({"id": f"reflex_m_{fake_tid}", "tag": master_tag, "msg": goal_raw, "ts": time.time(), "task_id": fake_tid, "type": "user"})
        redis_safe(lambda r: r.publish("monitor:log_channel", master_payload))
        
        # Bắn log thẳng vào Redis để Dashboard hiển thị
        msg_payload = json.dumps({"id": f"reflex_j_{fake_tid}", "tag": "JKAI", "msg": ans, "ts": time.time(), "task_id": fake_tid})
        redis_safe(lambda r: r.publish("monitor:log_channel", msg_payload))
        
        logger.info(f"⚡ [REFLEX-HIT]: Dashboard notified for '{goal_raw}'")
        return {
            "status": "success", 
            "task_id": fake_tid,
            "answer": ans, 
            "is_social": True
        }
    
    logger.info(f"🏛️ [MISSION-PATH]: Proceeding with mission for '{goal_raw}'")

    raw_tid = payload.get("task_id")
    if raw_tid and str(raw_tid).startswith("default_"):
        raw_tid = str(raw_tid).replace("default_", "ZENITH_", 1)
        payload["task_id"] = raw_tid

    task_id = str(raw_tid) if raw_tid and str(raw_tid) not in ["null", "undefined", "None"] else f"task_{int(time.time())}"
    
    raw_trid = payload.get("trace_id")
    trace_id = str(raw_trid) if raw_trid and str(raw_trid) not in ["null", "undefined", "None"] else f"gen_{int(time.time())}"
    
    mode = str(payload.get("mode", "fast")).lower()

    # 🛡️ [MODE-VALIDATION]: Intent mode verification
    if mode not in VALID_MODES:
        logger.warning(f"⚠️ [ILLEGAL-MODE]: Agent rejected cognitive mode '{mode}'.")
        return {"status": "error", "msg": f"Invalid mode: {mode}"}

    # 🔐 [IDEMPOTENCY-CHECK]: Task duplicate prevention
    def _check_duplicate(r):
        key = f"trace_lock:{trace_id}"
        if r.set(key, "locked", ex=3600, nx=True):
            return True
        return False
    
    if not redis_safe(_check_duplicate):
        logger.info(f"♻️ [IDEMPOTENCY]: Mission {trace_id} previously accepted.")
        return {"status": "queued", "task_id": task_id, "note": "idempotent_hit"}

    # 🧹 [ZENITH-PURGE]: Clearing inhibit flags (Stop/Pause)
    def _clear_blockers(r):
        r.delete("agent:stop_signal")
        r.delete(f"agent:stop_signal:{task_id}")
        r.delete("agent:paused")
        r.set("agent_status", "busy")
    redis_safe(_clear_blockers)
    
    # Enqueue task
    from core.utils.engine import engine
    payload["trace_id"] = trace_id 
    payload["session_id"] = payload.get("session_id") or trace_id
    redis_safe(lambda r: r.lpush("ai_task_queue", json.dumps(payload)))
    
    msg = f"📥 [GATEWAY] Mission `{task_id}` initialized | Trace: `{trace_id}`. Runtime ready."
    logger.info(msg)
    
    # 🏛️ [SOVEREIGN-LOG]: Logging mission intent at gateway
    goal = payload.get("goal", "Undefined task")
    source = payload.get("source", "WEB")
    master_tag = "MASTER_TELE" if source == "TELEGRAM" else "MASTER_WEB" if source == "WEB" else "MASTER"
    engine.publish_mission_log(master_tag, goal, task_id, trace_id)
    engine.publish_mission_log("GATEWAY", msg, task_id, trace_id)
    
    return {"status": "queued", "task_id": task_id, "trace_id": trace_id}

@app.post("/api/commander/stop")
async def stop_gateway(payload: dict = None):
    """
    [SUPREME-STOP]: Centralized kill switch.
    Purging all queues and terminating runtime.
    """
    task_id = (payload or {}).get("task_id")
    
    def _purge(r):
        if task_id and task_id != 'all':
            r.set(f"agent:stop_signal:{task_id}", "true", ex=3600)
            msg = f"🛑 [STOP] Mission `{task_id}` terminated via administrative override."
        else:
            r.delete("ai_task_queue", "user_request_queue", "exec_queue")
            r.set("agent:stop_signal", "true", ex=3600)
            r.set("agent_status", "idle")
            r.delete("hitl_pending")
            msg = "🛑 [STOP] Global system termination and queue purge complete."
        return msg

    msg = redis_safe(_purge, "Error connecting to Redis")
    return {"status": "ok", "msg": msg}

@app.post("/api/stream")
async def stream_gateway(payload: dict):
    """💎 [STREAM-GATEWAY]: Forwarding cognitive stream from Brain."""
    import httpx
    from fastapi.responses import StreamingResponse
    
    async def generate():
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", f"{router.brain_url}/stream", json=payload) as resp:
                async for chunk in resp.aiter_raw():
                    yield chunk
                    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/gpu/request")
async def request_gpu(payload: dict):
    service = payload.get("service")
    model = payload.get("model")
    success = await steward.get_gpu_permission(service, model)
    return {"status": "granted" if success else "denied"}

@app.post("/gpu/release")
async def release_gpu(payload: dict):
    service = payload.get("service")
    await steward.report_completion(service)
    return {"status": "acknowledged"}

# 👁️ [VISION-GATEWAY]: Vision analysis interface
@app.post("/api/vision")
async def vision_gateway(payload: dict):
    """Forwarding vision analysis request to ai-browser."""
    import httpx
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{router.browser_url}/vision", json=payload)
        return resp.json()

# 📡 [LOG-GATEWAY]: Unified logging interface
@app.post("/api/log")
async def log_gateway(payload: dict):
    tag = payload.get("tag", "SYSTEM")
    msg = payload.get("msg", "")
    task_id = payload.get("task_id", "system")
    # Synchronizing signal to Dashboard
    task_manager._log(tag, msg, tid=task_id, trid=payload.get("trace_id", "system"))
    return {"status": "logged"}

# 📂 [SYSTEM-GATEWAY]: File retrieval interface
@app.get("/api/system/read_file")
async def read_file_gateway(path: str):
    from pathlib import Path
    from fastapi import HTTPException
    
    # 🛡️ [SECURITY-SANDBOX]: Access restricted to workspace boundaries
    BASE_DIR = Path("/workspace").resolve()
    try:
        # Resolve path
        requested_path = Path(path).resolve()
        
        # Enforce sandbox boundaries
        if not str(requested_path).startswith(str(BASE_DIR)) and not path.startswith('d:\\'):
             if not path.startswith('d:\\Docker\\N8N'):
                raise HTTPException(status_code=403, detail="🚨 [ACCESS-DENIED]: External access blocked.")

        with open(path, 'r', encoding='utf-8') as f:
            return {"content": f.read(), "path": path, "ok": True}
    except HTTPException as he:
        raise he
    except Exception as e:
        return {"error": str(e), "ok": False}

@app.get("/hitl_pending")
async def get_hitl_pending():
    """Retrieve proposals awaiting administrative approval."""
    def _get(r):
        data = r.hgetall("hitl_pending")
        return {k.decode(): json.loads(v) for k, v in data.items()}
    return redis_safe(_get, {})

@app.post("/hitl_approve")
async def approve_hitl(payload: dict):
    """
    🔒 MULTI-LEVEL APPROVAL PROTOCOL v1.1
    Separation of standard approval and supreme verification.
    """
    task_id = payload.get("task_id")
    master_code = payload.get("code")

    def _pre_check(r):
        # Assess proposal security level
        proposal_raw = r.hget("hitl_pending", task_id)
        if not proposal_raw: return {"type": "APPROVE"} # Default to Plan approval
        return json.loads(proposal_raw)

    proposal = redis_safe(_pre_check, {"type": "APPROVE"})
    requires_nuclear = (proposal.get("type") == "CODE")

    # SECURITY VERIFICATION
    if requires_nuclear or sovereign.is_boot_locked:
        if not sovereign.verify_key(master_code):
            return {"status": "denied", "msg": "❌ ACCESS DENIED: INVALID AUTHORIZATION CODE."}
    
    # Device registration if boot locked
    if sovereign.is_boot_locked:
        reg_res = await sovereign.register_current_device(master_code)
        if reg_res["ok"]:
            sovereign.is_boot_locked = False
            return {"status": "approved", "msg": reg_res["msg"]}
        return {"status": "denied", "msg": reg_res["msg"]}

    def _approve(r):
        proposal_raw = r.hget("hitl_pending", task_id)
        
        # 📡 [SIGNALING-PROTOCOL]: Signal broadcasting to waiting agents
        if task_id.startswith(("diag_", "distill_", "fix_")):
            r.set(f"hitl_approve:{task_id}", "true")
            r.hdel("hitl_pending", task_id)
            return {"status": "approved", "msg": f"🔱 [SOVEREIGN-SEAL]: Command activated for `{task_id}`."}

        if not proposal_raw:
            # 📜 [DEEP-MODE-PLAN]: Action plan approval
            r.set(f"hitl_approve:{task_id}", "true")
            return {"status": "approved", "msg": "Action plan approved."}
        
        proposal = json.loads(proposal_raw)
        
        # ⚔️ [LEGACY-WARRIOR-COMPAT]: Compatibility layer
        if task_id.startswith("warrior_"):
            metadata_raw = r.hget("warrior:healing_metadata", task_id)
            if metadata_raw:
                meta = json.loads(metadata_raw)
                new_task = {
                    "task_id": f"exec_{task_id}",
                    "goal": f"RECOVERY PROTOCOL: Resolving issue at `{meta['service']}`",
                    "steps": [{"tool": "skill_self_healing", "args": {"service_name": meta['service'], "auto_repair": True}}],
                    "mode": "fast",
                    "source": "ZENITH_WARRIOR",
                    "ts": time.time()
                }
                r.rpush("ai_task_queue", json.dumps(new_task))
                r.hdel("hitl_pending", task_id)
                return {"status": "dispatched", "msg": "Zenith Warrior initialized system repair."}

        # 🚀 [GENERAL-PROPOSAL]: Task generation from AI proposal
        new_task = {
            "task_id": f"exec_{task_id}",
            "goal": proposal.get('message', 'Task approved by administrator'),
            "mode": "deep",
            "source": "ADMIN_HITL_APPROVAL",
            "ts": time.time()
        }
        # 🛡️ [SUBMIT-MISSION]: Enqueue for execution
        r.rpush("ai_task_queue", json.dumps(new_task))
        
        # 4. Cleanup HITL registry
        r.hdel("hitl_pending", task_id)
        
        return {"status": "dispatched", "task_id": new_task["task_id"]}

    return redis_safe(_approve, {"status": "error", "msg": "Redis infrastructure unresponsive."})

@app.post("/hitl_reject")
async def reject_hitl(payload: dict):
    """Reject AI proposal and enforce persistence to prevent recurrence."""
    task_id = payload.get("task_id")
    def _reject(r):
        # ENFORCE REJECTION PERSISTENCE
        proposal_raw = r.hget("hitl_pending", task_id)
        if proposal_raw:
            proposal = json.loads(proposal_raw)
            msg_content = proposal.get("message", "")
            # Add to Blacklist to prevent re-proposal
            r.sadd("monologue:blacklist", msg_content)
            # Log rejection history
            r.lpush("monologue:rejection_history", json.dumps({
                "task_id": task_id,
                "content": msg_content,
                "ts": time.time()
            }, ensure_ascii=False))

        r.hdel("hitl_pending", task_id)
        r.set(f"hitl_approve:{task_id}", "false")
        return {"status": "rejected", "msg": "Proposal rejected and blacklisted."}
    return redis_safe(_reject)

@app.post("/action")
async def handle_action(payload: dict):
    """
    🎮 STRATEGIC CONTROL PROTOCOL (Quick Action)
    """
    action = payload.get("action")
    if action == "apply_strategy":
        # Search for latest ZIM proposal
        def _find_and_approve(r):
            pending = r.hgetall("hitl_pending")
            for tid, data_raw in pending.items():
                data = json.loads(data_raw)
                if data.get("source") == "ZIM_INTERNAL":
                    # Internal approval routing
                    r.rpush("ai_task_queue", json.dumps({
                        "task_id": f"exec_{tid.decode()}",
                        "goal": f"STRATEGY IMPLEMENTATION: {data.get('message', '')}",
                        "mode": "deep",
                        "source": "ADMIN_QUICK_ACTION",
                        "ts": time.time()
                    }))
                    r.hdel("hitl_pending", tid)
                    return {"status": "approved", "msg": "Chiến lược đã được đưa vào hàng đợi thực thi!"}
            return {"status": "error", "msg": "Không tìm thấy đề xuất chiến lược nào đang chờ."}
        
        return redis_safe(_find_and_approve)

    return {"status": "error", "msg": "Hành động không xác định."}

@app.post("/execute")
async def execute_task(payload: dict):
    # Thực thi trực tiếp và trả kết quả ngay (Dùng cho Telegram/API)
    if sovereign.is_boot_locked:
        return {"status": "locked", "msg": "🚨 Hệ thống đang bị KHÓA. Vui lòng xác thực thiết bị!"}
    
    # 💎 [SOVEREIGN-ID-ELEVATION]: Nâng cấp ID default_ thành ZENITH_
    raw_tid = payload.get("task_id")
    if raw_tid and str(raw_tid).startswith("default_"):
        payload["task_id"] = str(raw_tid).replace("default_", "ZENITH_", 1)

    try:
        # Gọi thẳng process_task của task_manager
        result = await task_manager.process_task(payload)
        return result or {"status": "completed", "msg": "Nhiệm vụ đã hoàn tất."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
