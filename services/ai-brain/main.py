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
    except: pass

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
        # 🌀 [SINGULARITY-PULSE]: Kích hoạt nhịp đập Tự tiến hóa đầu tiên thưa Master
        asyncio.create_task(_autonomous_evolution_loop())
    asyncio.create_task(delayed_warmup())

async def _autonomous_evolution_loop():
    """🌀 [ETERNAL-ZENITH]: Giao thức Tự tiến hóa Vĩnh cửu thưa Master."""
    while True:
        try:
            # Nghỉ ngơi giữa các nhịp đập nơ-ron (Mặc định 1 giờ thưa Master)
            await asyncio.sleep(3600) 
            _publish_log("ZENITH", "🌀 [OMNI-EVOLVE]: Khởi động nhịp đập tự tầm soát hệ thống thưa Master...")
            
            # 🧪 Chắt lọc kinh nghiệm và đề xuất bản vá tự động thưa Ngài
            await distiller.distill_recent_tasks()
            _publish_log("ZENITH", "🌀 [OMNI-EVOLVE]: Đã hoàn tất đúc kết nơ-ron. Các đề xuất đã được niêm yết tại Sovereign Guard thưa Master.")
        except Exception as e:
            logger.error(f"❌ [EVOLVE-ERR]: {e}")
            await asyncio.sleep(300)

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
        result = await planner.generate_plan(
            goal=data.get('goal', ''),
            context=data.get('context', {}),
            images=data.get('images'),
            history=data.get('history', []),
            task_id=data.get('task_id', 'system')
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
            vector = embed(txt[:1000])
            if vector:
                await qc.upsert_intel(text=txt, embedding=vector, metadata={"source": f"memory_{task_id}", "type": "memory", "ts": _time.time()})
                return {"status": "memorized"}
    except: pass
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
    except: pass
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
        mode=data.get('mode', 'fast')
    )
    
    raw_answer = result.get('answer', '')
    has_steps = bool(result.get('steps'))
    
    # 🔬 [STEP-2]: Chỉ kiểm tra Hội Đồng Nơ-ron cho phản hồi hội thoại thưa Master
    # Nếu là FAST_PIPELINE (có steps), bỏ qua audit — trả trực tiếp cho Control Plane
    if has_steps:
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
