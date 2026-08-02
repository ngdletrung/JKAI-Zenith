import json, time, uuid, os
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, Response, stream_with_context
import requests, logging
from werkzeug.utils import secure_filename
from core.redis_client import redis_safe

# 🛡️ [SYSTEM-LOGGING]: Cấu hình ghi nhật ký cấu trúc
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

bp = Blueprint("tasks", __name__)

# 🌐 [NETWORK-COORDINATES]: Tọa độ mạng lưới Nhất thể hóa
AI_BRAIN_URL = os.getenv('AI_BRAIN_URL', 'http://ai-brain:8000')
AI_CONTROL_PLANE_URL = os.getenv('AI_CONTROL_PLANE_URL', 'http://ai-control-plane:8000')
EXECUTOR_URL = os.getenv('EXECUTOR_URL', 'http://ai-executor-1:8000')

@bp.route("/api/submit_task", methods=["POST"])
def submit_task():
    data = request.get_json(silent=True) or {}
    goal = data.get("goal","").strip()
    mode = data.get("mode", "fast").lower()
    files_data = data.get("files", []) # 📎 [FILE-UPLINK]: Nhận danh sách file
    
    raw_mid = data.get("mission_id")
    mission_id = str(raw_mid) if raw_mid and str(raw_mid) not in ["null", "undefined", "None"] else "default"
    # 🆔 [ID-GUARDIAN]: UUID + Timestamp để triệt tiêu hoàn toàn xung đột
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone(timedelta(hours=7))) # Giờ Việt Nam
    date_code = now.strftime('%d%m-%H%M') # e.g. 3105-0936
    task_id = f"{mission_id}_{date_code}_{uid}"
    
    # 🏰 [MISSION-STORAGE-ISOLATION]: Tách biệt hoàn toàn không gian dữ liệu
    mission_root = os.path.join(os.getcwd(), 'missions', mission_id)
    input_dir = os.path.join(mission_root, 'input')
    docs_dir = os.path.join(mission_root, 'docs')
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    # 💎 [WORKSPACE-SYNC]: Khôi phục Artifacts của sứ mệnh hiện tại
    artifacts = data.get("artifacts", {})
    filename_map = {
        'plan': 'implementation_plan.md',
        'tasks': 'task.md',
        'walkthrough': 'walkthrough.md'
    }
    for key, filename in filename_map.items():
        path = os.path.join(docs_dir, filename)
        content = artifacts.get(key)
        if content is not None:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Xóa file cũ nếu sứ mệnh này không có artifact đó (hoặc sứ mệnh mới)
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass

    saved_files = []
    import base64
    MAX_FILE_SIZE = 20 * 1024 * 1024 # 🛡️ [RESOURCE-GUARD]: Giới hạn 20MB
    
    # 🧠 [RAG-INJECTION]: Nén nội dung file văn bản để gửi thẳng vào context
    attached_files_content = ""
    MAX_EXTRACT_SIZE = 50000 # Giới hạn 50KB text mỗi file
    
    for f in files_data:
        try:
            raw_name = f.get("name", "unknown_file")
            name = secure_filename(raw_name) # 🔐 [SECURITY-SHIELD]: Chống Directory Traversal
            content = f.get("content", "") # Base64 string
            
            if len(content) > (MAX_FILE_SIZE * 1.4): # Ước tính Base64 overhead
                logger.warning(f"⚠️ [FILE-SIZE-EXCEEDED]: {name} quá lớn, đã bị từ chối.")
                continue

            if name and content:
                # 💾 [DISK-PERSISTENCE]: Lưu vào đĩa với định danh duy nhất
                unique_name = f"{uid}_{name}"
                file_path = os.path.join(input_dir, unique_name)
                if "," in content: content = content.split(",")[1]
                decoded_data = base64.b64decode(content)
                
                with open(file_path, "wb") as wb:
                    wb.write(decoded_data)
                
                # 🧠 [RAG-INJECTION]: Thử bóc tách Text nếu là file văn bản
                if len(decoded_data) < MAX_EXTRACT_SIZE:
                    try:
                        text_val = decoded_data.decode("utf-8")
                        attached_files_content += f"\n\n--- [FILE: {name}] ---\n{text_val}\n"
                    except UnicodeDecodeError:
                        pass # Bỏ qua nếu là file nhị phân (PDF, PNG, v.v.)
                
                # ⚡ [REDIS-ACCELERATION]: Đẩy vào bộ nhớ nóng dùng chung
                # Key: mission_data:{mission_id}:file:{filename}
                mission_id = data.get("mission_id", "default")
                redis_key = f"mission_data:{mission_id}:file:{name}"
                redis_safe(lambda r: r.set(redis_key, content, ex=3600)) # Giữ trong 1 giờ
                
                saved_files.append(name)
        except Exception as e:
            print(f"⚠️ [UPLOAD-ERR]: {e}")

    if saved_files:
        if not goal:
            goal = f"[FILE_ONLY]: {', '.join(saved_files)}"
        else:
            goal = f"{goal}\n\n📎 [SYSTEM-NOTE]: Đã đồng bộ {len(saved_files)} tệp tin vào Workspace Sứ mệnh. Truy cập qua ID: {uid}."

    # 🚀 [METADATA-ENRICHMENT]: Bổ sung thông tin định danh
    trace_id = f"trace_{uid}"
    logger.info(f"🚀 [TASK-SUBMIT]: ID={task_id}, Trace={trace_id}, Mission={mission_id}")
    
    images = data.get("images", [])
    # Nén thẳng nội dung file vào Goal để đảm bảo mô hình chắc chắn đọc được
    final_goal = f"{goal}\n\n{attached_files_content}".strip() if attached_files_content else goal

    payload = {
        "task_id": task_id,
        "trace_id": trace_id,
        "goal": final_goal,
        "mode": mode,
        "lang": data.get("lang", "vi"),
        "images": images,
        "source": "Web",
        "attached_files": saved_files,
        "attached_files_content": attached_files_content.strip(),
        "mission_id": mission_id,
        "parent_mission_id": data.get("parent_mission_id"),
    } 
    
    # 🏛️ [CENTRAL-GATEWAY]: Gửi tới Đầu mối ai-control-plane với Timeout kép
    try:
        # (Connect Timeout, Read Timeout)
        target_url = f"{AI_CONTROL_PLANE_URL}/api/submit_task"
        print(f"🚀 [UPLINK-TRACE]: Sending task to {target_url}", flush=True)
        
        resp = requests.post(target_url, json=payload, timeout=(5, 60))
        data = resp.json()
        if "ok" not in data: data["ok"] = True 
        return jsonify(data)
    except requests.exceptions.ConnectionError:
        # 🚨 [CRITICAL-DISCONNECT]: Chỉ fallback khi mất kết nối hoàn toàn
        print(f"❌ [GATEWAY-DISCONNECT]: Mất kết nối tới {AI_CONTROL_PLANE_URL}. Đang đẩy vào hàng chờ dự phòng...")
        redis_safe(lambda r: r.rpush("ai_task_queue", json.dumps(payload)))
        return jsonify({"ok": True, "task_id": task_id, "uploaded": saved_files, "fallback": True})
    except Exception as e:
        print(f"❌ [GATEWAY-ERR]: {e}")
        return jsonify({"ok": False, "error": str(e), "task_id": task_id})

@bp.route("/api/stream", methods=["POST"])
def stream_proxy():
    """
    💎 SSE STREAM PROXY: Chuyển tiếp token streaming từ ai-brain về Dashboard.
    Frontend kết nối endpoint này để nhận tokens theo thời gian thực.
    """
    data = request.get_json(silent=True) or {}
    gateway_url = AI_CONTROL_PLANE_URL
    
    def generate():
        try:
            with requests.post(
                f"{gateway_url}/api/stream",
                json=data,
                stream=True,
                timeout=(5, 600)
            ) as resp:
                # 💎 [LINE-BY-LINE]: Đảm bảo không vỡ Frame dữ liệu
                for line in resp.iter_lines():
                    if line:
                        yield line + b"\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n".encode()
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@bp.route("/api/geolocation", methods=["POST"])
def update_geolocation():
    """
    [GEOLOCATION-UPDATE]: Cap nhat toa do dinh vi chinh xac tu Browser.
    Luu vao Redis de cac dac vu va engine chia se dong thoi thoi gian thuc.
    """
    data = request.get_json(silent=True) or {}
    lat = data.get("latitude")
    lon = data.get("longitude")
    address = data.get("address")
    accuracy = data.get("accuracy")
    altitude = data.get("altitude")
    heading = data.get("heading")
    speed = data.get("speed")
    
    if lat is not None and lon is not None:
        geo_data = {
            "latitude": lat,
            "longitude": lon,
            "accuracy": accuracy,
            "altitude": altitude,
            "heading": heading,
            "speed": speed,
            "address": address or "",
            "timestamp": time.time()
        }
        # Luu vao Redis de chia se giua tat ca cac container
        redis_safe(lambda r: r.set("user:precise_geolocation", json.dumps(geo_data)))
        logger.info(f"GEOLOCATION-UPDATE: Saved browser location: {lat}, {lon} - accuracy: {accuracy}m - address: {address}")
        return jsonify({"ok": True, "msg": "Location synced successfully."})
        
    return jsonify({"ok": False, "error": "Invalid location data"}), 400

