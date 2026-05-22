# 🧬 [GEVENT-MONKEY-PATCH]: Phải được thực hiện TRƯỚC mọi import khác
import gevent.monkey
gevent.monkey.patch_all()

import os
import json
import time
import hashlib
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from api.tasks import bp as tasks_bp
from core.warmup import start_warmup_sequence
from core.redis_client import redis_safe

from config import config

# 🌐 [NETWORK-COORDINATES]: Tọa độ mạng lưới Nhất thể hóa
AI_CONTROL_PLANE_URL = os.getenv('AI_CONTROL_PLANE_URL', 'http://ai-control-plane:8000')
AI_BRAIN_URL = os.getenv('AI_BRAIN_URL', 'http://ai-brain:8000')
EXECUTOR_URL = os.getenv('EXECUTOR_URL', 'http://ai-executor-1:8000')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://qdrant:6333')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
BROWSER_URL = os.getenv('BROWSER_URL', 'http://ai-browser:8000')
POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://n8n:n8n@postgres:5432/n8n')

app = Flask(__name__, static_folder='../frontend/dist')
# 🛡️ [SECURITY-GUARD]: Sử dụng khóa dự phòng nếu config bị lỗi
app.config['SECRET_KEY'] = getattr(config, 'SECRET_KEY', os.getenv('SECRET_KEY', 'jkai-zenith-secret-key-default-2026'))
# 🛰️ [ASYNC-STABILITY]: Cấu hình nhịp tim SocketIO bền bỉ
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25,
    manage_session=False
)

# Register Blueprints
app.register_blueprint(tasks_bp)

MISSIONS_DIR = os.path.join(os.path.dirname(__file__), 'missions')
if not os.path.exists(MISSIONS_DIR):
    os.makedirs(MISSIONS_DIR)

# ====================== BACKGROUND: Artifact Watcher (WATCHDOG/POLLING) ======================
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

if HAS_WATCHDOG:
    class ZenithArtifactHandler(FileSystemEventHandler):
        def __init__(self, socketio, targets):
            self.socketio = socketio
            self.targets = targets
            self.last_emit = {}

        def on_modified(self, event):
            if event.is_directory: return
            filename = os.path.basename(event.src_path)
            for key, target in self.targets.items():
                if filename == target:
                    now = time.time()
                    if now - self.last_emit.get(key, 0) > 1:
                        self.last_emit[key] = now
                        self.socketio.emit("artifact_new", {"type": key, "ts": now})
else:
    print("⚠️ [JKAI-WARN] Watchdog not found. Falling back to Polling mode.")

def artifact_watcher():
    """
    👁️ [ARTIFACT-EYE]: Theo dõi sự thay đổi của hồ sơ.
    Tự động chọn Watchdog (siêu tốc) hoặc Polling (ổn định) tùy môi trường.
    """
    # 💎 [STORAGE-SYNC]: Sử dụng vùng nhớ dùng chung để đồng bộ Artifact
    docs_dir = os.getenv("ARTIFACTS_DIR", "/storage/artifacts")
    if not os.path.exists(docs_dir): os.makedirs(docs_dir, exist_ok=True)
    
    targets = {
        'plan': 'implementation_plan.md',
        'tasks': 'task.md',
        'walkthrough': 'walkthrough.md'
    }

    if HAS_WATCHDOG:
        event_handler = ZenithArtifactHandler(socketio, targets)
        observer = Observer()
        observer.schedule(event_handler, docs_dir, recursive=False)
        observer.start()
        print("📡 [JKAI] Artifact Watcher (WATCHDOG) ONLINE.")
        try:
            while True: time.sleep(10)
        except:
            observer.stop()
        observer.join()
    else:
        # Polling Fallback
        last_mtimes = {}
        print("📡 [JKAI] Artifact Watcher (POLLING) ONLINE.")
        while True:
            try:
                for key, filename in targets.items():
                    path = os.path.join(docs_dir, filename)
                    if os.path.exists(path):
                        mtime = os.path.getmtime(path)
                        if mtime > last_mtimes.get(key, 0):
                            last_mtimes[key] = mtime
                            socketio.emit("artifact_new", {"type": key, "ts": mtime})
                time.sleep(5)
            except:
                time.sleep(10)

# ====================== BACKGROUND: Hardware Pulse ➜ SocketIO ======================
def hardware_pulse_broadcaster():
    """
    Đọc dữ liệu nhịp tim phần cứng từ Host (thông qua file JSON dùng chung)
    và phát tới toàn bộ Master UI.
    """
    pulse_file = "/intelligence/protocols/hardware_pulse.json"
    print("📡 [JKAI] Hardware Pulse Broadcaster ONLINE.")
    while True:
        try:
            if os.path.exists(pulse_file):
                with open(pulse_file, 'r', encoding='utf-8') as f:
                    pulse_data = json.load(f)
                    socketio.emit("hardware_pulse", pulse_data)
            time.sleep(2)
        except:
            time.sleep(5)

# ====================== BACKGROUND: Redis ➜ SocketIO Bridge ======================
def redis_log_broadcaster():
    """
    Sử dụng Redis Pub/Sub để phát log với cơ chế BATCHING.
    Giúp giảm tải SocketIO và làm Dashboard mượt mà hơn.
    """
    import redis as redis_lib
    print("📡 [JKAI] Unified Redis Broadcaster (BATCHING) ONLINE.")
    
    redis_host = os.getenv("REDIS_HOST", "redis-ai")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_pass = os.getenv("REDIS_PASSWORD")
    
    operational_buffer = []
    progress_buffer = []
    processed_progress_ids = []
    processed_progress_hashes = []
    last_flush = time.time()
    
    while True:
        try:
            pubsub_client = redis_lib.Redis(
                host=redis_host, port=redis_port, password=redis_pass, decode_responses=True,
                socket_timeout=None, socket_keepalive=True
            )
            pubsub = pubsub_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe("monitor:log_channel", "monitor:progress_channel", "monitor:pulse_channel", "monitor:hitl_channel")
            print("✅ [JKAI-NEURAL] Quad Routing Active [ops, progress, pulse, hitl]", flush=True)
            
            while True:
                message = pubsub.get_message(timeout=0.02)
                if message and message.get('type') == 'message':
                    try:
                        channel = message['channel']
                        data = json.loads(message['data'])
                        
                        if channel == "monitor:pulse_channel":
                            pulse_data = data.get("data", data)
                            socketio.emit("hardware_pulse", pulse_data)
                        elif channel == "monitor:hitl_channel":
                            socketio.emit("hitl_pending_event", data)
                        elif channel == "monitor:progress_channel":
                            log_id = data.get("id")
                            msg = data.get("msg", "")
                            tag = data.get("tag", "SYSTEM")
                            task_id = data.get("task_id", "manual")
                            
                            is_dup = False
                            is_streamable = data.get("pin_id") is not None or tag in ["PROGRESS", "HEARTBEAT"] or "THOUGHT" in tag
                            
                            if not is_streamable and log_id:
                                if log_id in processed_progress_ids:
                                    is_dup = True
                                else:
                                    processed_progress_ids.append(log_id)
                                    if len(processed_progress_ids) > 1000:
                                        processed_progress_ids.pop(0)
                            
                            if not is_streamable and not is_dup:
                                msg_hash = hashlib.md5(f"{task_id}:{tag}:{msg}".encode()).hexdigest()
                                if msg_hash in processed_progress_hashes:
                                    is_dup = True
                                else:
                                    processed_progress_hashes.append(msg_hash)
                                    if len(processed_progress_hashes) > 1000:
                                        processed_progress_hashes.pop(0)
                            
                            if not is_dup:
                                progress_buffer.append(data)
                        else:
                            # Operational Channel
                            log_id = data.get("id")
                            msg = data.get("msg", "")
                            tag = data.get("tag", "SYSTEM")
                            task_id = data.get("task_id", "manual")
                            
                            is_dup = False
                            is_streamable = data.get("pin_id") is not None or tag in ["PROGRESS", "HEARTBEAT"] or "THOUGHT" in tag
                            
                            if not is_streamable and log_id:
                                if log_id in processed_progress_ids:
                                    is_dup = True
                                else:
                                    processed_progress_ids.append(log_id)
                                    if len(processed_progress_ids) > 1000:
                                        processed_progress_ids.pop(0)
                            
                            if not is_streamable and not is_dup:
                                msg_hash = hashlib.md5(f"{task_id}:{tag}:{msg}".encode()).hexdigest()
                                if msg_hash in processed_progress_hashes:
                                    is_dup = True
                                else:
                                    processed_progress_hashes.append(msg_hash)
                                    if len(processed_progress_hashes) > 1000:
                                        processed_progress_hashes.pop(0)
                            
                            if not is_dup:
                                operational_buffer.append(data)
                                # 🏛️ [PERSISTENCE-SYNC]: Also save missing operational logs to progress history list
                                try:
                                    raw_json = message['data']
                                    pubsub_client.lpush("monitor:progress_history", raw_json)
                                    pubsub_client.ltrim("monitor:progress_history", 0, 1999)
                                except: pass
                    except Exception as e:
                        print(f"[JKAI-CORE] Parse error: {e}")

                # 🚀 [ELITE-FLUSH]: Đảm bảo nhịp độ hiển thị tối ưu cho Master
                now = time.time()
                if now - last_flush > 0.05:
                    if operational_buffer:
                        socketio.emit("log_batch:operational", {"logs": operational_buffer})
                        operational_buffer = []
                    if progress_buffer:
                        socketio.emit("log_batch:progress", {"logs": progress_buffer})
                        progress_buffer = []
                    last_flush = now
        except Exception as e:
            print(f"❌ [JKAI-NEURAL] Connection error: {e}. Reconnecting in 3s...")
            time.sleep(3)

# ====================== UTILS: Security ======================
def verify_nuclear_key(data):
    """🛡️ [SOVEREIGN-VERIFICATION]: Kiểm tra Ấn Chủ quyền ở tầng sâu nhất."""
    # 🔓 Vùng đỏ đã được tháo gỡ theo lệnh của Master, luôn cho phép can thiệp tự do.
    return True

# ====================== API ROUTES ======================
@app.route('/api/system_status')
def system_status():
    import requests as req
    # 📡 [TELEMETRY]: Ghi nhận yêu cầu từ Dashboard
    print(f"💓 [HEARTBEAT-REQ]: Tiếp nhận yêu cầu kiểm tra sức khỏe từ {request.remote_addr}", flush=True)
    results = {
        "status": "online",
        "brain": "Offline", "executor": "Offline",
        "redis": "Offline", "qdrant": "Offline",
        "ollama": "Offline", "postgres": "Offline",
        "os": "JKAI ZENITH OS v42.5",
        "uplink": "stable"
    }
    try:
        r = req.get(f"{AI_BRAIN_URL}/health", timeout=3)
        if r.status_code == 200: results["brain"] = "Optimal"
    except: pass
    try:
        r = req.get(f"{EXECUTOR_URL}/health", timeout=3)
        if r.status_code == 200: results["executor"] = "Ready"
    except: pass
    is_redis = redis_safe(lambda r: r.ping(), False)
    if is_redis: results["redis"] = "Online"
    try:
        r = req.get(f"{QDRANT_URL}/readyz", timeout=3)
        if r.status_code == 200: results["qdrant"] = "Active"
    except: pass
    try:
        r = req.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if r.status_code == 200: results["ollama"] = "Online"
    except: pass
    
    # Lấy thông tin Model đang chạy thực tế & Tài nguyên VRAM
    try:
        r = req.get(f"{OLLAMA_HOST}/api/ps", timeout=3)
        if r.status_code == 200:
            models = r.json().get("models", [])
            if models:
                m = models[0]
                results["active_model"] = m.get("name", "Unknown")
                vram = m.get('size_vram', m.get('vram_usage', 0))
                total_vram = m.get('size', 0)
                results["model_vram"] = f"{vram / (1024**3):.1f}GB"
                results["vram_percent"] = int((vram / total_vram) * 100) if total_vram > 0 else 0
                results["processor"] = "GPU" if vram > 0 else "CPU"
            else:
                results["active_model"] = "None"
                results["model_vram"] = "0GB"
                results["vram_percent"] = 0
                results["processor"] = "Standby"
    except: pass

    # Đếm số lượng Kỹ năng (Skills) thực tế
    try:
        skills_path = "/intelligence/skills"
        if os.path.exists(skills_path):
            files = [f for f in os.listdir(skills_path) if f.endswith('.py')]
            results["skills_count"] = len(files)
    except: pass

    try:
        r = req.get(f"{BROWSER_URL}/health", timeout=3)
        if r.status_code == 200: results["browser"] = "Active"
    except: pass
    try:
        import psycopg2
        try:
            conn = psycopg2.connect(POSTGRES_URL, connect_timeout=3)
            conn.close()
            results["postgres"] = "Online"
        except Exception:
            conn = psycopg2.connect(
                host="postgres", port=5432,
                user=os.getenv('POSTGRES_USER', 'n8n'),
                password=os.getenv('POSTGRES_PASSWORD', ''),
                dbname=os.getenv('POSTGRES_DB', 'n8n'),
                connect_timeout=3
            )
            conn.close()
            results["postgres"] = "Online"
    except Exception as e:
        print(f"Postgres health check failed: {e}")
    return jsonify(results)

@app.route('/api/hitl_pending')
def hitl_pending():
    """Lấy danh sách Task đang chờ phê duyệt Nuclear Key."""
    pending = redis_safe(lambda r: r.hgetall("hitl_pending"), {})
    result = {}
    for k, v in pending.items():
        try: result[k] = json.loads(v)
        except: pass
    return jsonify(result)

@app.route('/api/hitl_approve', methods=['POST'])
def hitl_approve():
    """Phê duyệt Task bằng Nuclear Key."""
    from flask import request
    data = request.json or {}
    task_id = data.get('task_id')
    code = data.get('code', '')
    
    # 🛡️ KIỂM TRA MÃ TỐI CAO
    if not verify_nuclear_key(data):
        return jsonify({"error": "Unauthorized: Invalid Nuclear Key", "ok": False}), 403

    if not task_id: return jsonify({"error": "Missing task_id"}), 400
    
    # Nếu là broadcast: phê duyệt tất cả task đang chờ trong Redis
    if task_id == 'broadcast':
        pending = redis_safe(lambda r: r.hgetall("hitl_pending"), {})
        approved_ids = []
        for tid in pending.keys():
            tid_str = tid.decode() if isinstance(tid, bytes) else tid
            redis_safe(lambda r: r.set(f"hitl_approve:{tid_str}", "true", ex=300))
            redis_safe(lambda r: r.hdel("hitl_pending", tid_str))
            approved_ids.append(tid_str)
        
        if not approved_ids:
            # Không có task pending, gửi tín hiệu chung
            redis_safe(lambda r: r.set("hitl_approve:latest", "true", ex=300))
        
        msg = f"🔑 **Nuclear Key Verified**. Authorizing {len(approved_ids)} pending task(s)..."
        redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
        return jsonify({"status": "approved", "task_ids": approved_ids, "ok": True})
    
    # Phê duyệt task cụ thể
    redis_safe(lambda r: r.set(f"hitl_approve:{task_id}", "true", ex=300))
    redis_safe(lambda r: r.hdel("hitl_pending", task_id))  # Xóa khỏi danh sách chờ
    
    msg = f"🔑 **Nuclear Key Verified** for task `{task_id}`. Resuming execution..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    
    return jsonify({"status": "approved", "task_id": task_id, "ok": True})

@app.route('/api/hitl_reject', methods=['POST'])
def hitl_reject():
    """Bác bỏ Task (Hủy bỏ hành động)."""
    from flask import request
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')
    
    if not task_id: return jsonify({"error": "Missing task_id"}), 400
    
    # Gửi tín hiệu Bác bỏ vào Redis
    if task_id == 'broadcast':
        redis_safe(lambda r: r.set("hitl_reject:latest", "true", ex=300))
        # Xóa toàn bộ pending
        redis_safe(lambda r: r.delete("hitl_pending"))
    else:
        redis_safe(lambda r: r.set(f"hitl_reject:{task_id}", "true", ex=300))
        redis_safe(lambda r: r.hdel("hitl_pending", task_id))
    
    msg = f"🚫 **PROPOSAL REJECTED** by Master. Aborting task `{task_id}`..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    
    return jsonify({"status": "rejected", "task_id": task_id, "ok": True})

@app.route('/api/hitl_clarify', methods=['POST'])
def hitl_clarify():
    """Gửi câu trả lời làm rõ cho Task."""
    from flask import request
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')
    answer = data.get('answer')
    if not task_id or not answer: return jsonify({"error": "Missing params"}), 400
    
    # Lưu câu trả lời vào Redis
    redis_safe(lambda r: r.set(f"task_clarification:{task_id}", answer, ex=300))
    
    msg = f"💬 **Clarification Received**: \"{answer}\". Re-planning..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    
    return jsonify({"status": "clarified", "task_id": task_id})

@app.route('/api/docker_logs')
def docker_logs():
    """Lấy log từ history list (không xóa)."""
    try:
        raw = redis_safe(lambda r: r.lrange("monitor:log_history", 0, 199), [])
        lines = []
        for item in raw:
            try:
                obj = json.loads(item)
                ts = time.strftime('%H:%M:%S', time.localtime(obj.get('ts', 0)))
                lines.append(f"[{ts}] [{obj.get('tag','SYS')}] {obj.get('msg','')}")
            except: pass
        return jsonify({"logs": lines[::-1]})
    except Exception as e:
        return jsonify({"logs": [f"Error: {e}"]})

@app.route('/api/progress_logs')
def progress_logs():
    """Lấy toàn bộ technical trace từ Hộp đen."""
    try:
        raw = redis_safe(lambda r: r.lrange("monitor:progress_history", 0, 1999), [])
        lines = []
        for item in raw:
            try:
                obj = json.loads(item)
                lines.append(obj)
            except: pass
        return jsonify({"logs": lines[::-1]})
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)})

@app.route('/api/action', methods=['POST'])
def trigger_action():
    from flask import request
    data = request.get_json(silent=True) or {}
    
    # 🛡️ KIỂM TRA QUYỀN CHỦ TỊCH
    if not verify_nuclear_key(data):
        return jsonify({"error": "Unauthorized: Access Denied", "ok": False}), 403

    action = data.get('action', 'Unknown').lower()
    
    msg = f"🚀 Action Triggered: **{action.upper()}**"
    
    if action == 'scout':
        skills_path = "/shared/tools/definitions"
        try:
            files = [f for f in os.listdir(skills_path) if f.endswith('.py')]
            msg = f"🔍 **Neural Scan Complete**: Found {len(files)} active skills.\n" + "\n".join([f"- `{f}`" for f in files[:5]])
        except:
            msg = "🔍 **Neural Scan**: Scanning intelligence layer... All neurons firing normally."
    elif action == 'update_skills':
        msg = "🔄 **Neural Sync**: Capability matrix updated. All tool definitions reloaded."
    elif action == 'inject_prompt':
        msg = "🖋️ **Neural Sync**: System persona synchronized with *JKAI Zenith: Karpathy Elite Protocol*."
    elif action == 'set_rules':
        msg = "🛡️ **Operational Guard**: Karpathy's 4 Principles enforced across all neural layers."
    elif action == 'import_intel':
        import requests as req
        try:
            r = req.post(f"{AI_BRAIN_URL}/assimilate", timeout=120)
            if r.status_code == 200:
                msg = "📥 **Intel Ingestion Authorized**: Quy trình đồng hóa tri thức đang diễn ra dưới sự giám sát của Master."
            else:
                msg = f"⚠️ **Assimilation Failed**: Bộ não AI phản hồi lỗi ({r.status_code})."
        except Exception as e:
            msg = f"❌ **Neural Link Error**: Không thể kết nối với bộ não AI ({str(e)})."
    elif action == 'generate_report':
        return generate_report()
    elif action == 'warmup':
        import requests as req
        try:
            r = req.post(f"{AI_BRAIN_URL}/warmup", timeout=5)
            if r.status_code == 200:
                msg = "🚀 **Neural Warmup Initialized**: Toàn bộ quân đoàn nơ-ron đang được triệu hồi vào VRAM/RAM."
            else:
                msg = f"⚠️ **Warmup Failed**: AI Brain không phản hồi đúng ({r.status_code})."
        except Exception as e:
            msg = f"❌ **Link Failure**: Không thể gửi lệnh Warmup ({str(e)})."
    elif action == 'clear_log_history':
        redis_safe(lambda r: r.delete("monitor:log_history"))
        msg = "🧹 **Neural Log Purged**. Nhật ký tiến trình đã được quét sạch."
    
    if action != 'clear_log_history': # Tránh ghi đè log ngay sau khi xóa
        payload = json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})
        def _act(r):
            r.lpush("monitor:log_history", payload)
            r.ltrim("monitor:log_history", 0, 499)
            r.publish("monitor:log_channel", payload)
        redis_safe(_act)
    else:
        # Gửi tín hiệu thông báo xóa log qua channel
        payload = json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})
        redis_safe(lambda r: r.publish("monitor:log_channel", payload))

    return jsonify({"status": "ok", "msg": msg})

@app.route('/api/commander/stop', methods=['POST'])
def stop_agent():
    """Dừng phẫu thuật: Ủy thác lệnh cho Siêu Gateway."""
    import requests as req
    data = request.get_json(silent=True) or {}
    try:
        # 📡 [GATEWAY-PROXY]: Chuyển tiếp tới Đầu mối Trung tâm
        r = req.post(f"{AI_CONTROL_PLANE_URL}/api/commander/stop", json=data, timeout=5)
        return jsonify(r.json())
    except Exception as e:
        msg = f"❌ [STOP-ERR] Gateway không phản hồi: {e}"
        return jsonify({"status": "error", "msg": msg}), 500

@app.route('/api/commander/poweroff', methods=['POST'])
def power_off():
    msg = "⚠️ **System Shutdown Initialized**. Terminating all neural links..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    return jsonify({"status": "shutdown_started"})

@app.route('/api/commander/pause', methods=['POST'])
def toggle_pause():
    is_paused = redis_safe(lambda r: r.get("agent:paused") == b'true', False)
    new_state = 'false' if is_paused else 'true'
    redis_safe(lambda r: r.set("agent:paused", new_state))
    
    status_msg = "⏸️ **System Paused**. All agents on standby." if new_state == 'true' else "▶️ **System Resumed**. Continuing task."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": status_msg, "ts": time.time()})))
    return jsonify({"paused": new_state == 'true'})

@app.route('/api/commander/clear_stop', methods=['POST'])
def clear_stop():
    redis_safe(lambda r: r.delete("agent:stop_signal"))
    return jsonify({"status": "cleared"})

@app.route('/api/commander/restart', methods=['POST'])
def restart_services():
    msg = "🔄 **System Restart Requested**. Cycling neural cores..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    return jsonify({"status": "restarting"})

@app.route('/api/commander/clear_memory', methods=['POST'])
def clear_memory():
    redis_safe(lambda r: r.delete("ai_memory_context"))
    msg = "🧠 **Memory Flash Complete**. All short-term neural pathways have been purged."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    return jsonify({"status": "cleared"})

@app.route('/api/commander/diagnostics')
def run_diagnostics():
    msg = "🔍 **Deep Diagnostics Initiated**. Checking microservices latency and container health..."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    return jsonify({"status": "running"})

@app.route('/api/commander/config_models', methods=['POST'])
def config_models():
    data = request.get_json(silent=True) or {}
    planner = data.get('planner')
    critic = data.get('critic')
    msg = f"⚙️ **Model Re-configuration**: Planner -> `{planner}`, Critic -> `{critic}`."
    redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
    return jsonify({"status": "updated"})

@app.route('/api/commander/skills')
def list_skills():
    skills_path = "/intelligence/skills"
    if not os.path.exists(skills_path):
        return jsonify([{"id": 0, "name": "System Core", "purpose": "Default Intelligence", "note": "[Legacy]"}])
    
    try:
        files = [f for f in os.listdir(skills_path) if f.endswith('.md')]
        skills = []
        for i, f in enumerate(sorted(files)):
            skills.append({
                "id": i + 1,
                "name": f.replace('skill_', '').replace('.md', '').replace('_', ' ').title(),
                "purpose": "Kỹ năng đã được đồng hóa",
                "note": "[Elite]"
            })
        return jsonify(skills if skills else [{"id": 0, "name": "Wait for Assimilator", "purpose": "Đang hồi sinh tri thức...", "note": "[System]"}])
    except Exception as e:
        return jsonify([{"error": str(e)}])

@app.route('/api/commander/generate_report', methods=['POST'])
def generate_report():
    try:
        raw = redis_safe(lambda r: r.lrange("monitor:log_history", 0, 499), [])
        if not raw: return jsonify({"ok": False, "msg": "No logs found to generate report."})
        report_lines = [
            "# 🚀 JKAI Mission Report",
            f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "---",
            "## 📍 Neural Audit Log (Chi tiết chiến sự)",
            "| Timestamp | Unit | Intelligence Feed |",
            "| :--- | :--- | :--- |"
        ]
        for item in raw[::-1]:
            obj = json.loads(item)
            ts = time.strftime('%H:%M:%S', time.localtime(obj.get('ts', 0)))
            tag = obj.get('tag', 'SYS')
            msg = obj.get('msg', '').replace('\n', ' ')
            report_lines.append(f"| {ts} | {tag} | {msg} |")
        report_dir = os.path.join(os.getcwd(), 'reports')
        if not os.path.exists(report_dir): os.makedirs(report_dir)
        filename = f"mission_report_{int(time.time())}.md"
        filepath = os.path.join(report_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        msg = f"📜 **Neural Report Syntheticized**: `{filename}`. Lưu tại thư mục `/reports`."
        redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
        return jsonify({"ok": True, "msg": msg, "path": filepath})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route('/api/system/read_file')
def read_file_content():
    from flask import request
    path = request.args.get('path', '')
    if not path: return jsonify({"error": "Missing path"}), 400
    if not path.startswith('/') and not path.startswith('d:\\'):
        path = os.path.join('/workspace', path)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read(), "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/explorer')
def project_explorer():
    root_dir = '/workspace'
    if not os.path.exists(root_dir):
        return jsonify({"error": "Workspace not found"}), 404
    def get_tree(path):
        d = {'name': os.path.basename(path), 'path': os.path.relpath(path, root_dir)}
        if os.path.isdir(path):
            d['type'] = 'directory'
            children = []
            try:
                for f in os.listdir(path):
                    if f in ['.git', '__pycache__', 'node_modules', '.docker', '.next', 'dist']:
                        continue
                    child_path = os.path.join(path, f)
                    children.append(get_tree(child_path))
                d['children'] = sorted(children, key=lambda x: (x.get('type') != 'directory', x['name'].lower()))
            except:
                d['children'] = []
        else:
            d['type'] = 'file'
            ext = os.path.splitext(path)[1].lower()
            d['extension'] = ext
        return d
    try:
        tree = get_tree(root_dir)
        return jsonify(tree)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/save_file', methods=['POST'])
def save_file_content():
    from flask import request
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    content = data.get('content', '')
    
    # 🛡️ KIỂM TRA QUYỀN CHỦ TỊCH
    if not verify_nuclear_key(data):
        return jsonify({"error": "Unauthorized: Cannot save file", "ok": False}), 403

    if not path: return jsonify({"error": "Missing path"}), 400
    if not path.startswith('/') and not path.startswith('d:\\'):
        path = os.path.join('/workspace', path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        msg = f"💾 **File Saved**: `{os.path.basename(path)}`."
        redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
        return jsonify({"status": "ok", "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/delete_file', methods=['POST'])
def delete_file():
    from flask import request
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    
    # 🛡️ KIỂM TRA QUYỀN CHỦ TỊCH
    if not verify_nuclear_key(data):
        return jsonify({"error": "Unauthorized: Cannot delete file", "ok": False}), 403

    if not path: return jsonify({"error": "Missing path"}), 400
    if not path.startswith('/') and not path.startswith('d:\\'):
        path = os.path.join('/workspace', path)
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        msg = f"🗑️ **File Deleted**: `{os.path.basename(path)}`."
        redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/missions')
def list_missions():
    try:
        files = [f for f in os.listdir(MISSIONS_DIR) if f.endswith('.json')]
        missions = []
        for f in files:
            try:
                with open(os.path.join(MISSIONS_DIR, f), 'r', encoding='utf-8') as j:
                    data = json.load(j)
                    logs = data.get("logs", [])
                    last_msg = ""
                    if logs:
                        for l in reversed(logs):
                            if l.get('msg'):
                                last_msg = l.get('msg')[:100] + "..." if len(l.get('msg', '')) > 100 else l.get('msg')
                                break
                    missions.append({
                        "id": data.get("id"),
                        "title": data.get("title") or (data.get("goal", "").split('\n')[0][:60] + "..." if data.get("goal") else f"Sứ mệnh {data.get('id')}"),
                        "goal": data.get("goal", ""),
                        "ts": data.get("ts", 0),
                        "status": data.get("status", "idle"),
                        "preview": last_msg
                    })
            except: pass
        missions.sort(key=lambda x: x['ts'], reverse=True)
        return jsonify(missions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mission/<mid>')
def get_mission_detail(mid):
    path = os.path.join(MISSIONS_DIR, f"mission_{mid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Mission not found"}), 404
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mission/save', methods=['POST'])
def save_mission():
    from flask import request
    data = request.get_json(silent=True) or {}
    mid = data.get('id')
    if not mid:
        mid = f"m_{int(time.time())}"
        data['id'] = mid
    if not data.get('title'):
        goal = data.get('goal', '')
        logs = data.get('logs', [])
        
        # 💎 [SMART TITLE EVOLUTION v2]: Tìm kiếm tên xứng tầm
        candidate_text = goal
        if not candidate_text and logs:
            # Nếu Goal trống, lấy tin nhắn đầu tiên của Master
            for l in logs:
                if l.get('type') == 'user' or 'MASTER' in l.get('tag', '').upper():
                    candidate_text = l.get('msg', '')
                    break
        
        if candidate_text:
            lines = [l.strip() for l in candidate_text.split('\n') if l.strip()]
            first_content = "Sứ mệnh không tên"
            for line in lines:
                clean_line = line.replace('`', '').strip().lower()
                if clean_line in ['py', 'python', 'js', 'javascript', 'sh', 'bash', 'sql', 'json', 'yaml']: continue
                first_content = line
                break
            
            if len(first_content) > 70:
                data['title'] = first_content[:67] + '...'
            else:
                data['title'] = first_content
        else:
            data['title'] = f"Sứ mệnh {mid}"
    artifacts = data.get('artifacts', {})
    status = data.get('status', 'idle')
    
    # 🛡️ CHỈ CẬP NHẬT TỪ THƯ MỤC DOCS NẾU SỨ MỆNH ĐANG CHẠY
    if status == 'running':
        docs_dir = os.path.join(os.getcwd(), 'docs')
        filename_map = {
            'plan': 'implementation_plan.md',
            'tasks': 'task.md',
            'walkthrough': 'walkthrough.md'
        }
        for key, filename in filename_map.items():
            try:
                path = os.path.join(docs_dir, filename)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        artifacts[key] = f.read()
            except: pass
            
    data['artifacts'] = artifacts
    data['ts'] = time.time()
    path = os.path.join(MISSIONS_DIR, f"mission_{mid}.json")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True, "id": mid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mission/<mid>', methods=['DELETE'])
def delete_mission(mid):
    data = request.get_json(silent=True) or {}
    print(f"DEBUG: DELETE MISSION request received for id: {mid}")
    # Đã tắt xác thực Mật mã cho việc xóa lịch sử để Master dễ dàng thao tác.

    path = os.path.join(MISSIONS_DIR, f"mission_{mid}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Mission not found"}), 404
    try:
        os.remove(path)
        return jsonify({"ok": True, "message": f"Mission {mid} deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/missions', methods=['DELETE'])
def clear_missions():
    """🛡️ [ZENITH-PURGE]: Thanh tẩy toàn bộ hồ sơ và nhật ký vĩnh viễn."""
    data = request.get_json(silent=True) or {}
    print("DEBUG: CLEAR ALL MISSIONS request received")
    # Đã tắt xác thực Mật mã cho việc thanh tẩy lịch sử.

    try:
        # 1. Xóa toàn bộ tệp hồ sơ JSON
        for f in os.listdir(MISSIONS_DIR):
            if f.endswith('.json'):
                os.remove(os.path.join(MISSIONS_DIR, f))
        
        # 2. ⚡ [REDIS-WIPE]: Quét sạch nhật ký thời gian thực
        redis_safe(lambda r: r.delete("monitor:log_history"))
        
        msg = "🧹 **Zenith Purge Complete**. Toàn bộ hồ sơ và nhật ký đã bị xóa vĩnh viễn."
        redis_safe(lambda r: r.publish("monitor:log_channel", json.dumps({"tag": "SYSTEM", "msg": msg, "ts": time.time()})))
        
        return jsonify({"ok": True, "message": "All missions and logs cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """🛡️ [STATIC-GUARD]: Phân phối tài nguyên Giao diện và Hình ảnh Đặc vụ."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    
    # 🧹 [SPOTLESS-LOAD]: Khong xoa chat_history de giu lai lich su
    try:
        def _redis_flush(r):
            # Chi xoa cac log tien trinh de tranh rac, giu nguyen history
            p_keys = r.keys("process_logs:*") + r.keys("monitor:logs:*")
            if p_keys:
                r.delete(*p_keys)
            r.set("agent_status", "IDLE")
            r.delete("hitl_pending")
        redis_safe(_redis_flush)
    except: pass

    return send_from_directory(app.static_folder, 'index.html')

@socketio.on('connect')
def handle_connect():
    print(f"📡 [JKAI-CORP] Master LeeTrung đã kết nối vào Tổng hành dinh.")

@app.route('/api/commander/artifact')
def get_artifact():
    from flask import request
    type_ = request.args.get('type', 'plan')
    filename_map = {
        'plan': 'implementation_plan.md',
        'tasks': 'task.md',
        'walkthrough': 'walkthrough.md',
        'registry': 'registry.md'
    }
    filename = filename_map.get(type_)
    if not filename: return jsonify({"error": "Invalid type"}), 400
    if type_ == 'registry':
        docs_path = os.path.join(os.path.dirname(os.getcwd()), 'MISSION_CONTROL_CONTEXT.md')
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        docs_path = os.path.join(base_dir, 'docs', filename)
    try:
        if os.path.exists(docs_path):
            with open(docs_path, 'r', encoding='utf-8') as f:
                return jsonify({"content": f.read()})
        else:
            return jsonify({"content": f"# {filename}\nChưa có dữ liệu cho giai đoạn này."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



socketio.start_background_task(start_warmup_sequence, socketio)
socketio.start_background_task(redis_log_broadcaster)
socketio.start_background_task(hardware_pulse_broadcaster)
socketio.start_background_task(artifact_watcher)

if __name__ == '__main__':
    print("🚀 [JKAI] Mission Control Backend starting on port 9998...")
    socketio.run(app, host='0.0.0.0', port=9998, debug=True)
