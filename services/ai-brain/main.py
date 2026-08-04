# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/main.py
# - Role: API Gateway & Intellectual Core (Sovereign Core)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# 1. Bypass heavy audit for fast-mode or general queries to avoid CPU bottleneck.
# 2. NO emojis in logic and configuration. Zero-noise rule enforced.

import os
import json
import time as _time
import asyncio
import httpx
import sys
import logging
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BRAIN')

sys.path.append(os.getcwd())
#  [PATH-ALIGNMENT]: Tìm đường dẫn gốc của project thưa Master
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from core.utils.engine import engine
from core.qdrant_client import qdrant_client
from redis_client import redis_safe
try:
    from intelligence.skills.CORE.SYNC_KNOWLEDGE_QUANTUM.logic import JKAI_Assimilator
except ModuleNotFoundError:
    try:
        from intelligence.skills.skill_dongbotrithuc.logic import JKAI_Assimilator
    except ModuleNotFoundError:
        from intelligence.skills.RESEARCH.skill_dongbotrithuc.logic import JKAI_Assimilator
from experience_distiller import distiller

#  [SOVEREIGN-IDENTITY]: Khẳng định đây là Lõi Trí tuệ Gốc thưa Master
engine.is_brain_service = True
engine.current_service_url = engine.brain_url

app = FastAPI(title='JKAI Zenith Brain', version='31.1')

try:
    from core.utils.health import health_router
    app.include_router(health_router)
except Exception as _h_err:
    pass
assimilator = JKAI_Assimilator()

from core.utils.hlc import hlc, HlcTimestamp

def sync_hlc_from_payload(payload):
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
            logger.error("[HLC-SYNC-ERR] %s", e)

def _publish_log(tag: str, msg: str, task_id: str = 'system'):
    logger.info(f'[{tag}] {msg}')
    try:
        log_payload = json.dumps({'tag': tag, 'msg': msg, 'ts': _time.time(), 'task_id': task_id}, ensure_ascii=False)
        def _redis_op(r):
            r.lpush('monitor:log_history', log_payload)
            r.publish('monitor:log_channel', log_payload)
        redis_safe(_redis_op)
    except Exception: pass


def _err(
    error_code: str,
    message: str,
    task_id: str = None,
    trace_id: str = None,
    http_status: int = 200,
) -> dict:
    """
    Chuan hoa error response cho toan bo endpoint.
    Format: {ok, error_code, message, task_id, trace_id, ts}
    """
    payload = {
        "ok": False,
        "error_code": error_code,
        "message": message,
        "task_id": task_id,
        "trace_id": trace_id,
        "ts": _time.time(),
    }
    if http_status != 200:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=http_status, content=payload)
    return payload


async def _safe_get_json(request: Request):
    """️ NEURAL SANITIZER: Đảm bảo dữ liệu đầu vào thanh khiết và không có BOM thưa Master."""
    try:
        body = await request.body()
        # Loại bỏ BOM nếu có và decode thưa Ngài
        content = body.decode('utf-8-sig')
        return json.loads(content)
    except Exception as e:
        logger.error("[SANITIZER-ERR] %s", e)
        return None

@app.on_event('startup')
async def startup_event():
    logger.info(" JKAI Zenith: BRAIN SERVICE IS COMING ONLINE...")
    # ⏳ [NEURAL-STABILIZATION]: Chờ 30 giây để hạ tầng ổn định thưa Master
    async def delayed_warmup():
        await asyncio.sleep(5)
        
        # 🏛️ [AMG-v2]: Real-time Model Discovery & Registry Population on Startup
        try:
            from core.runtime.ollama_adapter import OllamaRuntimeAdapter
            from core.governor.model_registry import ModelRegistry
            adapters = [
                OllamaRuntimeAdapter(host=engine.ollama_host_gpu),
                OllamaRuntimeAdapter(host=engine.ollama_host_cpu),
            ]
            registry = ModelRegistry()
            n = await registry.discover(adapters)
            logger.info("[AMG-DISCOVERY] Registry populated — %s models registered.", n)
        except Exception as amg_err:
            logger.warning("[AMG-DISCOVERY-ERR] Failed to discover models on startup: %s", amg_err)

        await engine.warmup_all_models()
        
        #  [STARTUP-SYNC]: Tự động đồng bộ hóa toàn diện khi khởi động thưa Master
        try:
            from core.tools.sync_pipeline import run_sync_pipeline
            asyncio.create_task(run_sync_pipeline("startup_sync"))
        except Exception as startup_err:
            logger.error("[STARTUP-SYNC-ERR] %s", startup_err)
            
        asyncio.create_task(_autonomous_evolution_loop())
        asyncio.create_task(_import_watcher_loop())
    asyncio.create_task(delayed_warmup())

_evolve_lock = asyncio.Lock()

async def _system_is_idle() -> bool:
    """Check system load before running heavy background tasks."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        if cpu > 40 or mem > 70:
            logger.info("[EVOLVE] System busy (cpu=%s%%, mem=%s%%) — deferring", cpu, mem)
            return False
    except Exception:
        pass
    try:
        active = redis_safe(lambda r: r.scard("active_tasks"), 0)
        if active and int(active) > 0:
            logger.info("[EVOLVE] %s active tasks — deferring", active)
            return False
    except Exception:
        pass
    return True


async def _autonomous_evolution_loop():
    """ [ETERNAL-ZENITH]: Giao thức Tự tiến hóa Vĩnh cửu thưa Master.
    Chỉ chạy khi hệ thống idle, có timeout, không block user task.
    """
    while True:
        await asyncio.sleep(3600)
        if not await _system_is_idle():
            continue
        async with _evolve_lock:
            try:
                _publish_log("ZENITH", " [OMNI-EVOLVE]: Khởi động nhịp đập tự tầm soát hệ thống thưa Master...")
                await asyncio.wait_for(
                    distiller.distill_recent_tasks(max_tasks=100),
                    timeout=7200,
                )
                _publish_log("ZENITH", " [OMNI-EVOLVE]: Đã hoàn tất đúc kết nơ-ron.")
            except asyncio.TimeoutError:
                logger.warning("[EVOLVE] Timeout — distiller took >7200s, aborting")
            except Exception as e:
                logger.error("[EVOLVE-ERR] %s", e)
                await asyncio.sleep(300)

_import_watcher_lock = False
async def _import_watcher_loop():
    """ Auto-import: poll files/Import/ mỗi 30s, tự động chạy import_pipeline khi có file mới."""
    global _import_watcher_lock
    from core.utils import path_manager
    import_dir = path_manager.get("FILES_INPUT") or os.path.join(path_manager.get_root(), "files", "Import")
    os.makedirs(import_dir, exist_ok=True)
    known_files = set()

    await asyncio.sleep(60)  # đợi hệ thống ổn định

    while True:
        try:
            current = {f.name for f in os.scandir(import_dir) if f.is_file()}
            new_files = current - known_files
            if new_files:
                _publish_log("ZENITH", f" Phát hiện {len(new_files)} file mới trong Import, tự động đồng bộ...")
                if not _import_watcher_lock:
                    _import_watcher_lock = True
                    try:
                        from core.tools.sync_pipeline import run_sync_pipeline
                        result = await run_sync_pipeline("auto_import")
                        ok = result.get("ok", 0)
                        total = result.get("total", 0)
                        _publish_log("ZENITH", f" Auto-sync hoàn tất: {ok}/{total} phases OK ({result.get('msg', '')})")
                    except Exception as pipe_err:
                        logger.error("[IMPORT-WATCHER] %s", pipe_err)
                    finally:
                        _import_watcher_lock = False
                known_files = current
            else:
                known_files = current
        except Exception as e:
            logger.error("[IMPORT-WATCHER-ERR] %s", e)
        await asyncio.sleep(30)

@app.get('/health')
async def health_check():
    """Granular health-check: kiểm tra từng dependency riêng biệt với latency."""
    result = {"status": "alive", "dependencies": {}}
    overall_ok = True

    # 1. Redis
    try:
        t0 = _time.perf_counter()
        pong = redis_safe(lambda r: r.ping(), False)
        latency_ms = round((_time.perf_counter() - t0) * 1000, 1)
        if pong:
            result["dependencies"]["redis"] = {"status": "ok", "latency_ms": latency_ms}
        else:
            result["dependencies"]["redis"] = {"status": "error", "detail": "ping returned False"}
            overall_ok = False
    except Exception as e:
        result["dependencies"]["redis"] = {"status": "error", "detail": str(e)}
        overall_ok = False

    # 2. Qdrant
    try:
        t0 = _time.perf_counter()
        qdrant_client.get_collections()
        latency_ms = round((_time.perf_counter() - t0) * 1000, 1)
        result["dependencies"]["qdrant"] = {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        result["dependencies"]["qdrant"] = {"status": "error", "detail": str(e)[:120]}
        overall_ok = False

    # 3. Ollama (LLM engine)
    try:
        t0 = _time.perf_counter()
        async with httpx.AsyncClient(timeout=5.0) as client:
            ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
            resp = await client.get(f"{ollama_url}/api/tags")
        latency_ms = round((_time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 200:
            models = [m.get("name") for m in resp.json().get("models", [])]
            result["dependencies"]["ollama"] = {"status": "ok", "latency_ms": latency_ms, "models_loaded": len(models)}
        else:
            result["dependencies"]["ollama"] = {"status": "error", "http_status": resp.status_code}
            overall_ok = False
    except Exception as e:
        result["dependencies"]["ollama"] = {"status": "error", "detail": str(e)[:120]}
        overall_ok = False

    result["status"] = "healthy" if overall_ok else "degraded"
    return result


@app.get('/metrics')
async def get_metrics():
    """📊 [PROMETHEUS-EXPORTER]: Endpoint xuất metrics Prometheus cho Grafana/Prometheus."""
    from fastapi.responses import Response
    try:
        from telemetry.metrics import cognitive_metrics
        content, media_type = cognitive_metrics.get_prometheus_bytes()
        return Response(content=content, media_type=media_type)
    except Exception as e:
        return Response(content=f"# Error exporting metrics: {e}\n".encode("utf-8"), media_type="text/plain")

from artifact_tracker import ArtifactTracker
from fastapi.responses import PlainTextResponse

@app.get('/artifact/{task_id}')
async def get_artifact(task_id: str):
    """
    Truy xuất Artifact minh bạch của một task theo task_id.
    Trả về JSON đầy đủ: kế hoạch, tool calls, files thay đổi, trạng thái.
    """
    artifact = ArtifactTracker.get(task_id)
    if not artifact:
        return {"error": f"Không tìm thấy artifact cho task_id='{task_id}'. Artifact lưu 7 ngày."}
    return artifact

@app.get('/artifact/{task_id}/markdown', response_class=PlainTextResponse)
async def get_artifact_markdown(task_id: str):
    """Trả về Artifact dạng Markdown có cấu trúc — dễ đọc cho con người."""
    return ArtifactTracker.render_markdown(task_id)


from planner import Planner
from critic import Critic
from receptionist import Receptionist # Old receptionist
from dispatcher import Dispatcher # Old/New dispatcher
from core.utils.engine import MasterAbortException

from security.semantic_firewall import SemanticFirewall
from ingress_gateway.ingress import IngressGateway

planner = Planner()
critic = Critic()
receptionist_legacy = Receptionist(critic=critic, assimilator=assimilator) # Legacy doesn't need container
dispatcher_new = Dispatcher()

semantic_firewall = SemanticFirewall()
ingress_gateway = IngressGateway(receptionist_legacy, semantic_firewall, dispatcher_new)

#  [SYNC-LOCK]: Chống chạy duplicate sync job cùng source thưa Master
_active_syncs: set = set()

@app.post('/ks/sync')
async def knowledge_sync(data: dict):
    """
     [KS-SYNC]: Kích hoạt đồng bộ tri thức từ một nguồn cụ thể (Local hoặc Cloud).
    """
    import asyncio
    import os as _os
    source_id = data.get("source_id", "ks_sync")
    task_id   = data.get("task_id", f"ks_sync_{int(__import__('time').time())}")

    # ── 0. CHỐNG DUPLICATE SYNC JOB ────────────────────────────────────
    if source_id in _active_syncs:
        _publish_log("SYSTEM", f"⏳ [SYNC-BUSY]: '{source_id}' đang đồng bộ, bỏ qua yêu cầu trùng lặp thưa Master.", task_id)
        return {"ok": False, "status": "already_running", "source_id": source_id}

    # ── 1. PHÁT HIỆN HƯỚNG ĐỒNG BỘ (LOCAL vs CLOUD) ───────────────────
    is_cloud = source_id.startswith("rclone_")
    directory = None

    if not is_cloud:
        # Kiểm tra xem có trong connections.json và loại gì
        conn_path = "/workspace/intelligence/Knowledge_Manager/connections.json"
        if _os.path.exists(conn_path):
            try:
                with open(conn_path, "r", encoding="utf-8") as f:
                    conns = __import__("json").load(f)
                for c in conns:
                    if c.get("id") == source_id:
                        if c.get("type") in ["gdrive", "onedrive", "sharepoint", "dropbox", "rclone"]:
                            is_cloud = True
                        else:
                            directory = c.get("config", {}).get("path")
                        break
            except Exception:
                pass

    label = source_id[7:] if source_id.startswith("rclone_") else source_id

    # ── 2. XỬ LÝ ĐỒNG BỘ CLOUD IN-MEMORY ───────────────────────────────
    if is_cloud:
        #  Acquire lock NGAY TẠI ĐÂY (trước ensure_future) — tránh race condition thưa Master
        _active_syncs.add(source_id)

        async def _run_cloud():
            try:
                _publish_log("SYSTEM", f" [SYNC-RUNNING]: Bộ não bắt đầu kết nối và quét danh sách file cho '{label}'...", task_id)

                import sys
                workspace_path = "/workspace"
                if workspace_path not in sys.path:
                    sys.path.insert(0, workspace_path)
                from intelligence.Knowledge_Manager.manager import connection_manager

                res = await connection_manager.sync_connection(
                    source_id,
                    progress_cb=lambda scanned, total, fname: _publish_log(
                        "SYSTEM",
                        f" [SYNC-PROGRESS]: '{label}' — [{scanned}/{total}] Đang xử lý: {fname}",
                        task_id,
                    )
                )

                if res.get("status") == "ok":
                    stats = res.get("stats", {})
                    _publish_log("SYSTEM",
                        f" [SYNC-DONE]: Đồng bộ '{label}' hoàn tất! "
                        f"Tổng: {stats.get('scanned', 0)} file | "
                        f"Nạp mới: {stats.get('imported', 0)} | "
                        f"Bỏ qua (cache): {stats.get('skipped', 0)} | "
                        f"Lỗi: {stats.get('failed', 0)} thưa Master.",
                        task_id)
                else:
                    _publish_log("SYSTEM", f" [SYNC-ERR]: '{label}' — {res.get('msg', 'Lỗi không rõ')} thưa Master.", task_id)
            except Exception as e:
                _publish_log("SYSTEM", f" [SYNC-ERR]: '{label}' — {e} thưa Master.", task_id)
            finally:
                _active_syncs.discard(source_id)  # Luôn release lock thưa Master

        asyncio.ensure_future(_run_cloud())
        return {"ok": True, "status": "started", "task_id": task_id, "mode": "cloud_api"}


    # ── 3. XỬ LÝ ĐỒNG BỘ THƯ MỤC VẬT LÝ LOCAL ─────────────────────────
    # Nếu là local và chưa có directory, fallback về settings.INTELLIGENCE_DIR
    if not directory:
        from core.config import settings
        directory = settings.INTELLIGENCE_DIR

    if not _os.path.isdir(directory):
        return {"ok": False, "error": f"Directory not found or not mounted: {directory}"}

    _publish_log("SYSTEM", f" [KS-SYNC]: Bắt đầu quét thư mục local '{label}' tại {directory} thưa Master.", task_id)

    async def _run_local():
        try:
            from core.knowledge_sources.pipeline import ingestion_pipeline
            stats = await ingestion_pipeline.ingest_directory(
                directory=directory,
                source_id=source_id,
                task_id=task_id,
            )
            _publish_log("SYSTEM",
                f" [KS-SYNC-DONE]: '{label}' — "
                f"Mới: {stats.get('new',0)} | Cập nhật: {stats.get('updated',0)} | "
                f"Bỏ qua: {stats.get('skipped',0)} | Lỗi: {stats.get('failed',0)} thưa Master.",
                task_id)
        except Exception as e:
            _publish_log("SYSTEM", f" [KS-SYNC-ERR]: '{label}' — {e} thưa Master.", task_id)

    asyncio.ensure_future(_run_local())
    return {"ok": True, "status": "started", "task_id": task_id, "directory": directory, "mode": "local_fs"}



@app.post('/session/init')
async def initialize_session():
    """ [SPOTLESS-START]: Giao thức thanh tẩy mỗi khi Master mở trang thưa Master."""
    try:
        # Gọi quyền năng thanh tẩy từ Lõi Chủ quyền thông qua API thưa Master
        client = engine._get_client()
        await client.post(f"{engine.control_plane_url}/commander/flush")
        
        _publish_log("ZENITH", " [NEURAL-FLUSH]: Hệ thống đã được thanh tẩy. Chào mừng Master trở lại với diện mạo tinh khôi nhất!")
        return {"status": "ok", "msg": "Spotless Interface Active"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

@app.post('/stop')
async def stop_task():
    """️ EMERGENCY STOP PROTOCOL: Ngắt mạch mọi tiến trình theo ý chí của Master thưa Ngài."""
    _publish_log("ZENITH", " [ABORT]: Master đã ra lệnh ngắt mạch. Đang kích hoạt Giao thức Dừng khẩn cấp thưa Master.")
    redis_safe(lambda r: r.set("agent:stop_signal", "true", ex=60))
    return {"status": "ok", "msg": "Hệ thống đang ngắt mạch nơ-ron thưa Master!"}

@app.post('/plan')
async def plan_task(request: Request):
    data = await _safe_get_json(request)
    if not data:
        return {"steps": [], "ambiguous": False, "error": "Invalid JSON or Encoding thưa Master. ️"}
    sync_hlc_from_payload(data)
    try:
        ctx = dict(data.get('context') or {})
        if data.get('domain'):
            ctx['domain'] = data.get('domain')
        if data.get('agent_role'):
            ctx['agent_role'] = data.get('agent_role')
        if data.get('use_planning_pipeline'):
            ctx['use_planning_pipeline'] = True
        if data.get('trace_id'):
            ctx['trace_id'] = data.get('trace_id')
        result = await planner.generate_plan(
            goal=data.get('goal', ''),
            context=ctx,
            images=data.get('images'),
            history=data.get('history', []),
            task_id=data.get('task_id', 'system'),
            domain=data.get('domain') or ctx.get('domain'),
        )
        return result
    except Exception as e:
        import traceback
        logger.error("[PLAN-ERR] %s\n%s", e, traceback.format_exc())
        _publish_log('SYS_LOG', f'Loi Planner: {str(e)}')
        return {"steps": [], "ambiguous": False, "error": str(e)}

@app.post('/review')
async def review_plan(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    try:
        return await critic.review_plan(data.get('goal', ''), data.get('steps', []))
    except Exception as e:
        logger.error("[REVIEW-ERR] %s", e)
        return {"approved": True, "feedback": f"Critic error (auto-approved): {str(e)}"}

@app.post('/dispatch')
async def dispatch_task(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    return await dispatcher.dispatch(data.get('goal', ''), data.get('task_id', 'sys'))

@app.post('/summarize')
async def summarize_task(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    role_cfg = engine.get_role_config('SUMMARIZER')
    steps_info = ""
    if data.get("steps"):
        steps_info = f"\nThông tin các bước thực thi: {json.dumps(data.get('steps'), ensure_ascii=False)}"
        
    prompt = f"Báo cáo kết quả thực thi nhiệm vụ dựa trên dữ liệu thô sau.\nKết quả thô: {json.dumps(data.get('result', []), ensure_ascii=False)}\nMục tiêu ban đầu của Master: {data.get('goal', '')}{steps_info}\n\nHãy đóng vai trợ lý AI chuyên nghiệp (JKAI Zenith), viết báo cáo tổng hợp kết quả súc tích, chuyên nghiệp."
    
    response = await engine.call_chat(
        messages=[{"role": "user", "content": prompt}], 
        role="SUMMARIZER", 
        model=role_cfg.get('model'),
        lock_timeout=data.get('lock_timeout')
    )
    return {"type": "MISSION", "summary": response}

@app.post('/memorize')
async def memorize_conversation(request: Request):
    data = await request.json()
    goal, answer, task_id = data.get('goal', ''), data.get('answer', ''), data.get('task_id', 'mem')
    if len(goal) + len(answer) < 50: return {"status": "skipped"}
    try:
        memory_content = f"### [NEURAL-MEMORY] {int(_time.time())}\n**Master Goal**: {goal}\n**JKAI Response**: {answer}"
        scrubbed = await assimilator.ai_scrub(memory_content, f"mem_{task_id}.md")
        if scrubbed and scrubbed.get("content"):
            from core.utils.embed import embed
            from core.qdrant_client import qdrant_client as qc
            txt = scrubbed["content"]
            vector = await embed.get_embedding_async(txt[:1000])
            if vector:
                await qc.upsert_intel(text=txt, embedding=vector, metadata={"source": f"memory_{task_id}", "type": "memory", "ts": _time.time()})
                return {"status": "memorized"}
    except Exception: pass
    return {"status": "error"}

@app.post('/distill')
async def distill_knowledge(request: Request):
    """ [COGNITIVE-DISTILLATION]: Chắt lọc tri thức vào 12 Trụ cột thưa Master."""
    data = await request.json()
    task_id = data.get('task_id', 'unknown')
    goal = data.get('goal', 'unknown')
    
    #  [PROPOSAL-PROTOCOL]: Tạo đề xuất thỉnh lệnh Master thưa Ngài
    proposal_id = f"distill_{task_id}_{int(_time.time())}"
    proposal_msg = f" [BỘ TRÍCH LỌC]: Phát hiện tri thức mới từ Sứ mệnh `{goal[:50]}...`. Master có cho phép Chắt lọc vào 12 Trụ cột không thưa Ngài?"
    
    try:
        #  [SOVEREIGN-DISTILLATION]: Để Distiller tự triệu hồi Vệ binh thưa Master
        asyncio.create_task(distiller.distill_task(task_id, goal))
        return {"status": "distillation_initiated", "task_id": task_id}

    except Exception as e:
        logger.error("[DISTILL-ERR] %s", e)
        return {"status": "error", "reason": str(e)}

def normalize_and_format_answer(answer: Any) -> str:
    """Chuẩn hóa dữ liệu đầu ra (mảng, chuỗi biểu diễn mảng) thành văn bản gạch đầu dòng rõ ràng, sáng tạo."""
    if not answer:
        return ""
        
    import re
    # 1. Nếu là list/tuple thực tế
    if isinstance(answer, (list, tuple)):
        lines = []
        for x in answer:
            s = str(x).strip()
            if s:
                # Tự động định dạng thành gạch đầu dòng nếu chưa có
                if not s.startswith("-") and not s.startswith("*") and not re.match(r"^\d+\.", s):
                    lines.append(f"- {s}")
                else:
                    lines.append(s)
        return "\n".join(lines).strip()
        
    # 2. Nếu là chuỗi nhưng bị rò rỉ định dạng mảng (ví dụ: "['A', 'B']")
    if isinstance(answer, str):
        val = answer.strip()
        if (val.startswith("[") and val.endswith("]")) or (val.startswith("(") and val.endswith(")")):
            try:
                import json
                # Thử parse JSON
                parsed = json.loads(val.replace("'", '"'))
                if isinstance(parsed, (list, tuple)):
                    return normalize_and_format_answer(parsed)
            except Exception:
                # Tách thô sơ bằng regex nếu lỗi parse
                cleaned = re.sub(r"^[\[\(\'\"]+|[\]\)\'\"]+$", "", val)
                parts = [p.strip().strip("'\"") for p in cleaned.split("', '") if p.strip()]
                if len(parts) > 1:
                    return normalize_and_format_answer(parts)
        return val
        
    return str(answer).strip()

async def _neural_council_audit(goal: str, answer: str, task_id: str):
    """️ [NEURAL-COUNCIL]: Hội đồng nơ-ron đa tầng thẩm định thưa Master.
    Trả về (final_answer, approved, action_plan)."""
    try:
        refusal_keywords = [
            "xin lỗi", "không thể cung cấp", "thời gian thực", "thông tin mới nhất",
            "trở ngại", "xin lỗi vì sự bất tiện", "không tìm thấy", "unable to provide",
            "real-time information", "sorry"
        ]
        answer_lower = answer.lower()
        if any(kw in answer_lower for kw in refusal_keywords):
            logger.info("[NEURAL-COUNCIL] Refusal/safety response detected. Bypassing audit thưa Master.")
            return answer, True, []
 
        audit_prompt = (
            f"Mục tiêu của Master: {goal}\n"
            f"Câu trả lời dự kiến: {answer}\n\n"
            "Hãy đóng vai Hội đồng Phê bình Zenith. Nếu câu trả lời trên hời hợt hoặc thiếu sót, hãy sửa lại cho 'Elite' hơn. "
            "LƯU Ý QUAN TRỌNG: Nếu câu trả lời dự kiến chỉ là bản kế hoạch nháp, chứa các từ khóa chờ đợi thực thi "
            "(như 'Chờ kết quả...', 'đang thực thi...', 'chưa có dữ liệu...', 'sắp chạy...'), hoặc chưa thực sự thực hiện "
            "công việc, bạn KHÔNG ĐƯỢC điền vào 'corrected_answer'. Hãy thiết lập 'approved': false, 'corrected_answer': '' (để trống), "
            "và điền các hành động cụ thể cần làm vào 'action_plan' để kích hoạt cơ chế chạy lại (retry) tự động của hệ thống.\n\n"
            "Trả về JSON: {'approved': bool, 'corrected_answer': str, 'action_plan': [str]}"
        )
        audit_res = await engine.call_chat(
            messages=[{"role": "user", "content": audit_prompt}],
            role="CRITIC",
            json_mode=True,
            skip_memory=True,
            task_id=task_id
        )
        if isinstance(audit_res, dict):
            approved = audit_res.get("approved", True)
            action_plan = audit_res.get("action_plan", [])
            corrected = audit_res.get("corrected_answer") or audit_res.get("final_answer") or ""
            # Trả về chuỗi rỗng nếu corrected là rỗng để tránh kích hoạt nhanh
            if not corrected.strip():
                corrected = ""
            return corrected, approved, action_plan
    except Exception: pass
    return "", True, []
 
@app.post('/receptionist')
async def receptionist_task(request: Request):
    data = await _safe_get_json(request)
    if not data:
        return {'status': 'error', 'answer': 'Yêu cầu không hợp lệ thưa Master. ️'}
    sync_hlc_from_payload(data)
    
    goal, task_id = data.get('goal', ''), data.get('task_id', 'sys')
    
    #  [STAGE-2]: KHỚI ĐỘNG CỔNG INGRESS (VỚI SHADOW MODE)
    try:
        result = await ingress_gateway.receive_request(
            goal=goal,
            task_id=task_id,
            history=data.get('history', []),
            images=data.get('images'),
            mode=data.get('mode', 'fast'),
            mission_id=data.get('mission_id'),
            parent_mission_id=data.get('parent_mission_id'),
            trace_id=data.get('trace_id'),
        )
    except MasterAbortException:
        from core.utils.engine import engine
        engine.request_cache.pop(task_id, None)
        return {
            'status': 'ok',
            'answer': ' Giao thức dừng đã được kích hoạt. Toàn bộ Đặc vụ đã dừng theo lệnh của Master.',
            'task_id': task_id,
            'aborted': True
        }
    
    raw_answer = result.get('answer', '')
    has_steps = bool(result.get('steps'))
    is_command = goal.strip().startswith("/")
    
    req_mode = data.get('mode', 'fast')
    is_fast_mode = (result.get('mode') == 'fast') or (req_mode == 'fast') or (result.get('pipeline') == 'fast')
    audit_keywords = ['sửa', 'viết', 'tạo', 'xóa', 'chạy', 'cải tiến', 'tối ưu', 'edit', 'write', 'create', 'delete', 'run', 'execute', 'modify', 'update', 'config', 'file', 'sh', 'bash', 'script', 'command', 'cmd', 'docker', 'tusualoi', 'tucaitien']
    goal_lower = goal.lower()
    has_audit_keywords = any(kw in goal_lower for kw in audit_keywords)
    
    if is_command:
        return {'status': 'ok', **result}
    
    async def _audit_and_retry(current_goal, current_answer, retry_count=0):
        if len(current_answer) <= 50:
            return normalize_and_format_answer(current_answer)
            
        _publish_log("ZENITH", " [NEURAL-COUNCIL]: Đang triệu hồi Hội đồng để thẩm định phản hồi...")
        corrected, approved, action_plan = await _neural_council_audit(current_goal, current_answer, task_id)
        
        # ️ 1. CRITIC ENFORCEMENT: Nếu bị từ chối và Critic đã sửa đổi câu trả lời, ép sử dụng ngay lập tức
        if not approved and corrected:
            _publish_log("ZENITH", "️ [CRITIC-ENFORCE]: Sử dụng trực tiếp câu trả lời đã chỉnh sửa của Hội đồng Thẩm định.")
            return normalize_and_format_answer(corrected)
            
        # ️ 2. FALLBACK RETRY: Nếu bị từ chối nhưng không có câu trả lời sửa sẵn, tiến hành chạy lại
        if not approved and action_plan and retry_count < 1:
            _publish_log("WARN", f" [CRITIC-RETRY]: Critic từ chối. Retry với action_plan ({len(action_plan)} bước)...")
            retry_goal = current_goal + "\n\n[CRITIC-FEEDBACK]: " + "\n".join(action_plan)
            retry_tid = f"retry_{task_id}"
            retry_result = await ingress_gateway.receive_request(
                goal=retry_goal, task_id=retry_tid,
                history=data.get("history", []),
                images=data.get("images"),
                mode=data.get("mode", "fast"),
                mission_id=data.get("mission_id"),
                parent_mission_id=data.get("parent_mission_id"),
                trace_id=data.get("trace_id") or task_id,
            )
            retry_answer = retry_result.get("answer", "")
            return normalize_and_format_answer(retry_answer)
            
        return normalize_and_format_answer(corrected or current_answer)
    
    is_fast_pipeline = result.get('pipeline') == 'fast'
    if is_fast_mode or is_fast_pipeline or not has_audit_keywords:
        return {'status': 'ok', 'answer': normalize_and_format_answer(raw_answer)}
    
    final_answer = await _audit_and_retry(goal, raw_answer)
    return {'status': 'ok', 'answer': final_answer}

@app.post('/chat')
async def chat_task(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    role_cfg = engine.get_role_config('CHAT')
    response = await engine.call_chat(messages=data.get('messages', []), model=role_cfg.get('model'), lock_timeout=data.get('lock_timeout'))
    return {'status': 'ok', 'answer': response}

@app.post('/stream')
async def stream_chat(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    goal, task_id, role, history, images = data.get('goal', ''), data.get('task_id', 'stream'), data.get('role', 'RECEPTIONIST'), data.get('history', []), data.get('images', [])

    async def token_generator():
        full_response = ''
        from redis_client import get_redis
        r_conn = get_redis()
        try:
            #  [SESSION-WARMUP]: Đảm bảo mạch chat luôn sẵn sàng thưa Master
            if r_conn: r_conn.set("agent:status", "running")
            
            role_cfg = engine.get_role_config(role)
            model = role_cfg.get('model')
            ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
            
            system_prompt = engine.get_intel_file('agent_receptionist.md') or 'Bạn là JKAI Zenith.'
            messages = [{'role': 'system', 'content': system_prompt}] + history[-10:] + [{'role': 'user', 'content': goal}]
            if images: messages[-1]['images'] = images if isinstance(images, list) else [images]

            client = engine._get_client()
            async with client.stream('POST', f'{ollama_host}/api/chat', json={'model': model, 'messages': messages, 'stream': True, 'options': role_cfg.get('options', {}), 'keep_alive': role_cfg.get('keep_alive', '5m')}) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip(): continue

                    chunk = json.loads(line)
                    
                    # ️ [STREAM-INTERRUPT]: Kiểm tra tín hiệu dừng thưa Master
                    if r_conn and r_conn.get("agent:stop_signal") in [b'true', 'true']:
                        yield f"data: {json.dumps({'token': '... [STOPPED BY MASTER] ...', 'task_id': task_id}, ensure_ascii=False)}\n\n"
                        break

                    token = chunk.get('message', {}).get('content', '')
                    if token:
                        full_response += token
                        yield f"data: {json.dumps({'token': token, 'task_id': task_id}, ensure_ascii=False)}\n\n"
                    if chunk.get('done', False):
                        yield f"data: {json.dumps({'done': True, 'task_id': task_id, 'full': full_response}, ensure_ascii=False)}\n\n"
                        # Log to Redis...
                        log_payload = json.dumps({'tag': 'CHAT_INTEL', 'msg': full_response, 'ts': _time.time(), 'task_id': task_id}, ensure_ascii=False)
                        def _redis_op(r):
                            r.lpush('monitor:log_history', log_payload)
                            r.ltrim('monitor:log_history', 0, 499)
                        redis_safe(_redis_op)
                        break
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'task_id': task_id})}\n\n"

    return StreamingResponse(token_generator(), media_type='text/event-stream')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
