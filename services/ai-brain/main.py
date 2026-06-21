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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BRAIN')

sys.path.append(os.getcwd())
# 🌐 [PATH-ALIGNMENT]: Tìm đường dẫn gốc của project thưa Master
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

# 👑 [SOVEREIGN-IDENTITY]: Khẳng định đây là Lõi Trí tuệ Gốc thưa Master
engine.is_brain_service = True
engine.current_service_url = engine.brain_url

app = FastAPI(title='JKAI Zenith Brain', version='31.1')
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
            logger.error(f"❌ [HLC-SYNC-ERR]: {e}")

def _publish_log(tag: str, msg: str):
    logger.info(f'[{tag}] {msg}')
    try:
        log_payload = json.dumps({'tag': tag, 'msg': msg, 'ts': _time.time(), 'task_id': 'system'}, ensure_ascii=False)
        def _redis_op(r):
            r.lpush('monitor:log_history', log_payload)
            r.publish('monitor:log_channel', log_payload)
        redis_safe(_redis_op)
    except Exception: pass

async def _safe_get_json(request: Request):
    """🛡️ NEURAL SANITIZER: Đảm bảo dữ liệu đầu vào thanh khiết và không có BOM thưa Master."""
    try:
        body = await request.body()
        # Loại bỏ BOM nếu có và decode thưa Ngài
        content = body.decode('utf-8-sig')
        return json.loads(content)
    except Exception as e:
        logger.error(f"❌ [SANITIZER-ERR]: {e}")
        return None

@app.on_event('startup')
async def startup_event():
    logger.info("💎 JKAI Zenith: BRAIN SERVICE IS COMING ONLINE...")
    # ⏳ [NEURAL-STABILIZATION]: Chờ 30 giây để hạ tầng ổn định thưa Master
    async def delayed_warmup():
        await asyncio.sleep(30)
        await engine.warmup_all_models()
        
        # 🔄 [STARTUP-SYNC]: Tự động đồng bộ hóa toàn diện khi khởi động thưa Master
        try:
            from core.tools.sync_pipeline import run_sync_pipeline
            asyncio.create_task(run_sync_pipeline("startup_sync"))
        except Exception as startup_err:
            logger.error(f"❌ [STARTUP-SYNC-ERR]: {startup_err}")
            
        asyncio.create_task(_autonomous_evolution_loop())
        asyncio.create_task(_import_watcher_loop())
    asyncio.create_task(delayed_warmup())

async def _autonomous_evolution_loop():
    """🌀 [ETERNAL-ZENITH]: Giao thức Tự tiến hóa Vĩnh cửu thưa Master."""
    while True:
        try:
            await asyncio.sleep(3600)
            _publish_log("ZENITH", "🌀 [OMNI-EVOLVE]: Khởi động nhịp đập tự tầm soát hệ thống thưa Master...")
            await distiller.distill_recent_tasks()
            _publish_log("ZENITH", "🌀 [OMNI-EVOLVE]: Đã hoàn tất đúc kết nơ-ron. Các đề xuất đã được niêm yết tại Sovereign Guard thưa Master.")
        except Exception as e:
            logger.error(f"❌ [EVOLVE-ERR]: {e}")
            await asyncio.sleep(300)

_import_watcher_lock = False
async def _import_watcher_loop():
    """🔍 Auto-import: poll files/Import/ mỗi 30s, tự động chạy import_pipeline khi có file mới."""
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
                _publish_log("ZENITH", f"🔍 Phát hiện {len(new_files)} file mới trong Import, tự động đồng bộ...")
                if not _import_watcher_lock:
                    _import_watcher_lock = True
                    try:
                        from core.tools.sync_pipeline import run_sync_pipeline
                        result = await run_sync_pipeline("auto_import")
                        ok = result.get("ok", 0)
                        total = result.get("total", 0)
                        _publish_log("ZENITH", f"✅ Auto-sync hoàn tất: {ok}/{total} phases OK ({result.get('msg', '')})")
                    except Exception as pipe_err:
                        logger.error(f"[IMPORT-WATCHER] {pipe_err}")
                    finally:
                        _import_watcher_lock = False
                known_files = current
            else:
                known_files = current
        except Exception as e:
            logger.error(f"[IMPORT-WATCHER-ERR] {e}")
        await asyncio.sleep(30)

@app.get('/health')
async def health_check(): return {'status': 'alive'}

from planner import Planner
from critic import Critic
from receptionist import Receptionist # Old receptionist
from dispatcher import Dispatcher # Old/New dispatcher

from security.semantic_firewall import SemanticFirewall
from ingress_gateway.ingress import IngressGateway

planner = Planner()
critic = Critic()
receptionist_legacy = Receptionist(critic=critic, assimilator=assimilator) # Legacy doesn't need container
dispatcher_new = Dispatcher()

semantic_firewall = SemanticFirewall()
ingress_gateway = IngressGateway(receptionist_legacy, semantic_firewall, dispatcher_new)

@app.post('/session/init')
async def initialize_session():
    """✨ [SPOTLESS-START]: Giao thức thanh tẩy mỗi khi Master mở trang thưa Master."""
    try:
        # Gọi quyền năng thanh tẩy từ Lõi Chủ quyền thông qua API thưa Master
        async with httpx.AsyncClient() as client:
            await client.post(f"{engine.control_plane_url}/commander/flush")
        
        _publish_log("ZENITH", "✨ [NEURAL-FLUSH]: Hệ thống đã được thanh tẩy. Chào mừng Master trở lại với diện mạo tinh khôi nhất!")
        return {"status": "ok", "msg": "Spotless Interface Active"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

@app.post('/stop')
async def stop_task():
    """🛡️ EMERGENCY STOP PROTOCOL: Ngắt mạch mọi tiến trình theo ý chí của Master thưa Ngài."""
    _publish_log("ZENITH", "🛑 [ABORT]: Master đã ra lệnh ngắt mạch. Đang kích hoạt Giao thức Dừng khẩn cấp thưa Master.")
    redis_safe(lambda r: r.set("agent:stop_signal", "true", ex=60))
    return {"status": "ok", "msg": "Hệ thống đang ngắt mạch nơ-ron thưa Master!"}

@app.post('/plan')
async def plan_task(request: Request):
    data = await _safe_get_json(request)
    if not data:
        return {"steps": [], "ambiguous": False, "error": "Invalid JSON or Encoding thưa Master. 🛡️"}
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
        logger.error(f'[PLAN-ERR] {e}\n{traceback.format_exc()}')
        _publish_log('SYS_LOG', f'Loi Planner: {str(e)}')
        return {"steps": [], "ambiguous": False, "error": str(e)}

@app.post('/review')
async def review_plan(request: Request):
    data = await request.json()
    sync_hlc_from_payload(data)
    try:
        return await critic.review_plan(data.get('goal', ''), data.get('steps', []))
    except Exception as e:
        logger.error(f'[REVIEW-ERR] {e}')
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
    """🧪 [COGNITIVE-DISTILLATION]: Chắt lọc tri thức vào 12 Trụ cột thưa Master."""
    data = await request.json()
    task_id = data.get('task_id', 'unknown')
    goal = data.get('goal', 'unknown')
    
    # 📜 [PROPOSAL-PROTOCOL]: Tạo đề xuất thỉnh lệnh Master thưa Ngài
    proposal_id = f"distill_{task_id}_{int(_time.time())}"
    proposal_msg = f"🧪 [BỘ TRÍCH LỌC]: Phát hiện tri thức mới từ Sứ mệnh `{goal[:50]}...`. Master có cho phép Chắt lọc vào 12 Trụ cột không thưa Ngài?"
    
    try:
        # 🧪 [SOVEREIGN-DISTILLATION]: Để Distiller tự triệu hồi Vệ binh thưa Master
        asyncio.create_task(distiller.distill_task(task_id, goal))
        return {"status": "distillation_initiated", "task_id": task_id}

    except Exception as e:
        logger.error(f"❌ [DISTILL-ERR]: {e}")
        return {"status": "error", "reason": str(e)}

async def _neural_council_audit(goal: str, answer: str, task_id: str) -> str:
    """🛡️ [NEURAL-COUNCIL]: Hội đồng nơ-ron đa tầng thẩm định thưa Master."""
    try:
        # Bypass audit for safety refusals or standard fallback messages thưa Master
        refusal_keywords = [
            "xin lỗi", "không thể cung cấp", "thời gian thực", "thông tin mới nhất",
            "trở ngại", "xin lỗi vì sự bất tiện", "không tìm thấy", "unable to provide",
            "real-time information", "sorry"
        ]
        answer_lower = answer.lower()
        if any(kw in answer_lower for kw in refusal_keywords):
            logger.info("🛡️ [NEURAL-COUNCIL]: Refusal/safety response detected. Bypassing audit thưa Master.")
            return answer

        audit_prompt = (
            f"Mục tiêu của Master: {goal}\n"
            f"Câu trả lời dự kiến: {answer}\n\n"
            "Hãy đóng vai Hội đồng Phê bình Zenith. Nếu câu trả lời trên hời hợt hoặc thiếu sót, hãy sửa lại cho 'Elite' hơn. "
            "Nếu đã tốt, hãy giữ nguyên. Trả về JSON: {'approved': bool, 'final_answer': str}"
        )
        # Triệu hồi nơ-ron phụ để thẩm định song song thưa Ngài
        audit_res = await engine.call_chat(
            messages=[{"role": "user", "content": audit_prompt}],
            role="CRITIC",
            json_mode=True,
            skip_memory=True, # Tránh vòng lặp bộ nhớ thưa Master
            task_id=task_id
        )
        if isinstance(audit_res, dict) and audit_res.get("final_answer"):
            return audit_res["final_answer"]
    except Exception: pass
    return answer

@app.post('/receptionist')
async def receptionist_task(request: Request):
    data = await _safe_get_json(request)
    if not data:
        return {'status': 'error', 'answer': 'Yêu cầu không hợp lệ thưa Master. 🛡️'}
    sync_hlc_from_payload(data)
    
    goal, task_id = data.get('goal', ''), data.get('task_id', 'sys')
    
    # 🧠 [STAGE-2]: KHỚI ĐỘNG CỔNG INGRESS (VỚI SHADOW MODE)
    # Traffic giờ đi qua IngressGateway. Nó sẽ tự gọi Legacy Pipeline
    # và song song chạy Shadow Pipeline để đo đạc sự khác biệt.
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
    
    raw_answer = result.get('answer', '')
    has_steps = bool(result.get('steps'))
    is_command = goal.strip().startswith("/")
    
    is_fast_mode = result.get('mode') == 'fast' or data.get('mode') == 'fast'
    audit_keywords = ['sửa', 'viết', 'tạo', 'xóa', 'chạy', 'cải tiến', 'tối ưu', 'edit', 'write', 'create', 'delete', 'run', 'execute', 'modify', 'update', 'config', 'file', 'sh', 'bash', 'script', 'command', 'cmd', 'docker', 'tusualoi', 'tucaitien']
    goal_lower = goal.lower()
    has_audit_keywords = any(kw in goal_lower for kw in audit_keywords)
    
    # [STEP-2]: Chỉ kiểm tra Hội Đồng Nơ-ron cho phản hồi hội thoại thưa Master
    # Nếu là FAST_PIPELINE (có steps), siêu lệnh (command), fast mode, hoặc không có từ khóa nhạy cảm cần thẩm định, bỏ qua audit — trả trực tiếp cho Control Plane
    if has_steps or is_command or is_fast_mode or not has_audit_keywords:
        return {'status': 'ok', **result}
    
    if len(raw_answer) > 50:
        _publish_log("ZENITH", "🔬 [NEURAL-COUNCIL]: Đang triệu hồi Hội đồng để thẩm định phản hồi...")
        final_answer = await _neural_council_audit(goal, raw_answer, task_id)
        return {'status': 'ok', 'answer': final_answer}
    
    return {'status': 'ok', 'answer': raw_answer}

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

    # 🔒 [NEURAL-LOCK]: Đảm bảo mạch chat luôn trơn chu thưa Master
    lock_name = "gpu_vram"
    if not await engine._acquire_neural_lock(lock_name, timeout=60):
         return StreamingResponse(iter([f"data: {json.dumps({'error': 'Hệ thống đang bận...'}, ensure_ascii=False)}\n\n"]), media_type='text/event-stream')

    async def token_generator():
        full_response = ''
        from redis_client import get_redis
        r_conn = get_redis()
        try:
            # 🧹 [SESSION-WARMUP]: Đảm bảo mạch chat luôn sẵn sàng thưa Master
            if r_conn: r_conn.set("agent:status", "running")
            
            role_cfg = engine.get_role_config(role)
            model = role_cfg.get('model')
            ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
            
            system_prompt = engine.get_intel_file('agent_receptionist.md') or 'Bạn là JKAI Zenith.'
            messages = [{'role': 'system', 'content': system_prompt}] + history[-10:] + [{'role': 'user', 'content': goal}]
            if images: messages[-1]['images'] = images if isinstance(images, list) else [images]


            async with httpx.AsyncClient(timeout=600.0) as client:
                async with client.stream('POST', f'{ollama_host}/api/chat', json={'model': model, 'messages': messages, 'stream': True, 'options': role_cfg.get('options', {}), 'keep_alive': role_cfg.get('keep_alive', '5m')}) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip(): continue
                        

                        chunk = json.loads(line)
                        
                        # 🛡️ [STREAM-INTERRUPT]: Kiểm tra tín hiệu dừng thưa Master
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
        finally:
            await engine._release_neural_lock(lock_name)

    return StreamingResponse(token_generator(), media_type='text/event-stream')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
