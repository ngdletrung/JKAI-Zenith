import telebot
from telebot import types
import httpx
import os
import json
import time
import threading
import re
import base64
import hashlib
import asyncio
from edge_tts import Communicate
from redis import Redis
from dotenv import load_dotenv
from pydub import AudioSegment
from faster_whisper import WhisperModel

# ==========================================
# 💎 CẤU HÌNH HỆ THỐNG
# ==========================================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
MASTER_ID = int(os.getenv("MASTER_ID", "0"))
CONTROL_PLANE_URL = os.getenv("AI_CONTROL_PLANE_URL", "http://ai-control-plane:8000")
DASHBOARD_URL = "http://mission-control:5173"
REDIS_HOST = os.getenv("REDIS_HOST", "redis-ai")
REDIS_PASS = os.getenv("REDIS_PASSWORD")

# 🕵️ MÃ BĂM CHỦ QUYỀN (PROTECTED - SHA256 of OK JKAI GO)
MASTER_HASH = "0e94b3de1477fd760e485cf448efbbe3471497d807861eed47ae8295c2f446a2"

bot = telebot.TeleBot(TOKEN)
redis_client = Redis(host=REDIS_HOST, port=6379, db=0, password=REDIS_PASS, decode_responses=True)

# 📡 [UNIFIED-LOG-PROTOCOL]: Chuyển tiếp log về Đầu mối Trung tâm
def publish_mission_log(tag, msg, task_id="system", **kwargs):
    try:
        payload = {"tag": tag, "msg": msg, "task_id": task_id, "kwargs": kwargs}
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{CONTROL_PLANE_URL}/api/log", json=payload)
    except Exception as e:
        print(f"❌ [LOG-RELAY-ERR] {e}")

# 🧠 Khởi tạo Neural Ear (Whisper) - CPU Mode
whisper_model = None
def init_whisper():
    try:
        print("🎙️ [VOICE] Đang nạp Giao thức Thính giác (Whisper)...")
        global whisper_model
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        print("✅ [VOICE] Whisper đã sẵn sàng.")
    except Exception as e:
        print(f"❌ [VOICE-ERR] {e}")

# ==========================================
# 🛡️ GIAO THỨC TỰ TRỊ (RESILIENCE)
# ==========================================
def wait_for_internet(timeout=60):
    """💎 [NEURAL-LINK]: Chờ kết nối internet để thiết lập Synapse."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            import socket
            socket.create_connection(("api.telegram.org", 443), timeout=5)
            return True
        except Exception:
            time.sleep(2)
    return False

def safe_send_message(chat_id, text, **kwargs):
    """🚀 [RESILIENT-SENDER]: Giao thức gửi tin nhắn bền bỉ với cơ chế Tái thử."""
    import random
    # Thêm độ trễ ngẫu nhiên nhỏ (0.2s đến 0.6s) để tránh timing pattern cố định
    time.sleep(random.uniform(0.2, 0.6))
    
    max_retries = 10
    for i in range(max_retries):
        try:
            return bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            if i == max_retries - 1: 
                print(f"❌ [TELE-CRITICAL]: Mất kết nối vĩnh viễn: {e}")
                raise e
            # Thêm Jitter ngẫu nhiên vào thời gian chờ tái thử (ví dụ: wait + 1.0s đến 3.0s)
            wait = min((i + 1) * 3, 30) + random.uniform(1.0, 3.0)
            print(f"⚠️ [TELE-RETRY]: Mất kết nối hoặc bị giới hạn. Đang thử lại sau {wait:.2f}s... (Lần {i+1})")
            time.sleep(wait)

# ==========================================
# 🛠️ TIỆN ÍCH HỆ THỐNG
# ==========================================
def escape_html(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def translate_markdown_to_html(md: str) -> str:
    if not md: return ""
    html = escape_html(md)
    # Convert Markdown Bold (**text**) to HTML Bold (<b>text</b>)
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
    # Convert Markdown Italic (*text*) to HTML Italic (<i>text</i>) safely without breaking double asterisks
    html = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', html)
    # Convert Inline Code (`code`) to HTML Code (<code>code</code>)
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    # Convert Bullet Points (starts with "- " or "* ") to "• "
    html = re.sub(r'^\s*[-*]\s+', '• ', html, flags=re.MULTILINE)
    # Convert Markdown Headers (## Header) to HTML Bold (<b>Header</b>)
    html = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', html, flags=re.MULTILINE)
    # Convert separator lines (---, ———, ___ 10+) to strikethrough
    html = re.sub(r'^[\s]*[—\-_]{10,}[\s]*$', '<s>───</s>', html, flags=re.MULTILINE)
    # Convert pipe table separator rows (| --- | --- |) — remove to reduce noise
    html = re.sub(r'^\|[\s\-:]+\|[\s\-:|]+\|$', '', html, flags=re.MULTILINE)
    return html

def generate_voice(text, chat_id):
    if len(text) > 300: return None
    try:
        os.makedirs("/tmp/audio", exist_ok=True)
        output_file = f"/tmp/audio/res_{chat_id}_{int(time.time())}.ogg"
        clean_text = re.sub(r'[*`#_\[\]()]', '', text)
        async def _speak():
            communicate = Communicate(clean_text, "vi-VN-HoaiMyNeural")
            await communicate.save(output_file)
        asyncio.run(_speak())
        return output_file
    except Exception as e:
        print(f"❌ [TTS-ERR] {e}")
        return None

# ==========================================
# 🧠 XỬ LÝ LỆNH TRUNG TÂM (CORE LOGIC)
# ==========================================
def execute_neural_command(goal, images=None, mode="auto"):
    try:
        task_id = f"tele_{int(time.time())}"
        
        # 📡 [LOG-TELEGRAM]: Xuất hiện trên Tab Tiến trình
        # Removed duplicate publish_mission_log here as main.py handles it
        
        payload = {
            "task_id": task_id,
            "goal": goal,
            "mode": mode,
            "source": "TELEGRAM",
            "ts": time.time(),
            "images": images or []
        }
        
        # 🌐 [UNIFIED-EXECUTION]: Dùng /api/submit_task cho mọi mode (non-blocking)
        # Kết quả luôn đến qua Redis pub/sub (log_listener) — không cần chờ HTTP
        # Timeout 600s chỉ để đảm bảo kết nối không bị cắt giữa chừng
        with httpx.Client(timeout=600.0) as client:
            res = client.post(f"{CONTROL_PLANE_URL}/api/submit_task", json=payload)
            data = res.json() if res.status_code == 200 else {}
            mode_label = {"fast": "FAST (Phản xạ)", "deep": "DEEP (Tư duy sâu)", "auto": "AUTO"}.get(mode, mode.upper())
            if res.status_code == 200:
                safe_send_message(MASTER_ID, f"✅ <b>HỆ THỐNG:</b> Đã tiếp nhận yêu cầu <i>(Mode: {mode_label})</i>. Đang khởi tạo luồng tư duy...", parse_mode="HTML")
            else:
                safe_send_message(MASTER_ID, f"⚠️ <b>LỖI HỆ THỐNG:</b> Không thể kết nối Trung tâm <i>(Mã lỗi: {res.status_code})</i>. Đang chuyển vào hàng chờ...", parse_mode="HTML")
    except Exception as e:
        safe_send_message(MASTER_ID, f"❌ <b>LỖI KẾT NỐI:</b> {str(e)}", parse_mode="HTML")

# ==========================================
# 📦 BỘ GOM LOG CHỐNG SPAM (LOG AGGREGATOR)
# ==========================================
non_pinned_buffer = []
non_pinned_timer = None
non_pinned_lock = threading.Lock()

def flush_non_pinned_logs():
    """🚀 [BUFFER-FLUSHER]: Gửi toàn bộ log gom lại trong chu kỳ."""
    global non_pinned_timer
    with non_pinned_lock:
        if not non_pinned_buffer:
            non_pinned_timer = None
            return
        
        # Group messages ensuring each combined block is under 4000 characters
        chunks = []
        current_chunk = []
        current_len = 0
        for msg in non_pinned_buffer:
            if current_len + len(msg) + 1 > 4000:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [msg]
                current_len = len(msg)
            else:
                current_chunk.append(msg)
                current_len += len(msg) + 1
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        non_pinned_buffer.clear()
        non_pinned_timer = None
    
    for chunk in chunks:
        if chunk.strip():
            safe_send_message(MASTER_ID, chunk, parse_mode="HTML")

def queue_non_pinned_log(text):
    """📥 [BUFFER-QUEUE]: Gom log tiến trình để gửi gộp."""
    global non_pinned_timer
    with non_pinned_lock:
        non_pinned_buffer.append(text)
        if non_pinned_timer is None:
            non_pinned_timer = threading.Timer(1.5, flush_non_pinned_logs)
            non_pinned_timer.start()

def send_immediate_log(text, markup=None):
    """⚡ [IMMEDIATE-SENDER]: Giải phóng hàng chờ và gửi ngay tin nhắn quan trọng."""
    global non_pinned_timer
    with non_pinned_lock:
        if non_pinned_timer:
            non_pinned_timer.cancel()
            
        chunks = []
        if non_pinned_buffer:
            current_chunk = []
            current_len = 0
            for msg in non_pinned_buffer:
                if current_len + len(msg) + 1 > 4000:
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                    current_chunk = [msg]
                    current_len = len(msg)
                else:
                    current_chunk.append(msg)
                    current_len += len(msg) + 1
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            non_pinned_buffer.clear()
        non_pinned_timer = None
    
    for chunk in chunks:
        if chunk.strip():
            safe_send_message(MASTER_ID, chunk, parse_mode="HTML")
            
    safe_send_message(MASTER_ID, text, parse_mode="HTML", reply_markup=markup)

# ==========================================
# 🏛️ ĐỊNH DANH BAN NGÀNH DOANH NGHIỆP
# ==========================================
def get_corporate_metadata(tag: str, source: str = "") -> dict:
    tag_upper = tag.upper()
    src_upper = source.upper() if source else ""
    
    # 👑 [MASTER / CHỦ TỊCH]
    if tag_upper.startswith("MASTER"):
        return {
            "dept_name": "VĂN PHÒNG CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ",
            "clearance": "⚡ CHỈ THỊ THƯỢNG KHẨN (SUPREME DIRECTIVE)",
            "serial_prefix": "JKAI-CHAIRMAN-",
            "emoji": "👑"
        }
    
    # 🧠 [JKAI TỔNG TRỢ LÝ TỐI CAO]
    if tag_upper == "JKAI":
        return {
            "dept_name": "BAN ĐIỀU HÀNH TRUNG ƯƠNG (CENTRAL OPS BOARD)",
            "clearance": "💎 NGHỊ QUYẾT TOÀN DIỆN (EXECUTIVE DECREE)",
            "serial_prefix": "JKAI-CORE-",
            "emoji": "💎"
        }
        
    # 🌌 [ANTIGRAVITY]
    if tag_upper == "ANTIGRAVITY":
        return {
            "dept_name": "PHÂN KHU KIẾN TẠO KIẾN TRÚC & TƯ DUY",
            "clearance": "🌌 ĐỀ XUẤT CẤU TRÚC (ARCHITECTURAL INITIATIVE)",
            "serial_prefix": "JKAI-ANTIGRAV-",
            "emoji": "🌌"
        }

    # 🛎️ [BAN TRỢ LÝ]
    if "GATEWAY" in tag_upper or "RECEPTIONIST" in tag_upper or "GATEWAY" in src_upper or "RECEPTIONIST" in src_upper:
        return {
            "dept_name": "BAN TRỢ LÝ & ĐỐI NGOẠI TẬP ĐOÀN",
            "clearance": "🟢 THÔNG THƯỜNG (PUBLIC ACCESSIBLE)",
            "serial_prefix": "JKAI-RECEPT-",
            "emoji": "🛎️"
        }

    # 🎯 [BAN KẾ HOẠCH]
    if "PLANNER" in tag_upper or "THOUGHT" in tag_upper or "PLANNER" in src_upper or "THOUGHT" in src_upper:
        return {
            "dept_name": "PHÒNG HOẠCH ĐỊNH CHIẾN LƯỢC & THIẾT LỘ TRÌNH",
            "clearance": "🔵 PHƯƠNG ÁN CHIẾN LƯỢC (STRATEGIC PLAN)",
            "serial_prefix": "JKAI-PLAN-",
            "emoji": "🎯"
        }

    # ⚙️ [BAN THỰC THI]
    if "EXECUTOR" in tag_upper or "ALPHA" in tag_upper or "BETA" in tag_upper or "EXECUTOR" in src_upper or "ALPHA" in src_upper or "BETA" in src_upper:
        return {
            "dept_name": "BAN THỰC THI & TRIỂN KHAI KỸ THUẬT",
            "clearance": "🟡 LƯU HÀNH NỘI BỘ (INTERNAL ONLY)",
            "serial_prefix": "JKAI-EXEC-",
            "emoji": "⚙️"
        }

    # 🛡️ [BAN KIỂM SOÁT]
    if "CRITIC" in tag_upper or "AUDIT" in tag_upper or "REVIEW" in tag_upper or "CRITIC" in src_upper or "AUDIT" in src_upper or "REVIEW" in src_upper:
        return {
            "dept_name": "BAN KIỂM SOÁT NỘI BỘ & AN NINH TẬP ĐOÀN",
            "clearance": "🔴 TỐI MẬT (HIGHLY CONFIDENTIAL)",
            "serial_prefix": "JKAI-AUDIT-",
            "emoji": "🛡️"
        }

    # ✍️ [BAN THƯ KÝ]
    if "SUMMARIZER" in tag_upper or "SUMMARIZER" in src_upper:
        return {
            "dept_name": "BAN THƯ KÝ & TỔNG HỢP VĂN PHÒNG ĐIỀU HÀNH",
            "clearance": "🟡 LƯU HÀNH NỘI BỘ (INTERNAL ONLY)",
            "serial_prefix": "JKAI-SEC-",
            "emoji": "✍️"
        }

    # 🚨 [SỰ CỐ KHẨN]
    if tag_upper == "ERROR":
        return {
            "dept_name": "BAN KIỂM SOÁT & KHẮC PHỤC SỰ CỐ KHẨN CẤP",
            "clearance": "🚨 SỰ CỐ KHẨN CẤP (EMERGENCY ALARM)",
            "serial_prefix": "JKAI-ERR-",
            "emoji": "🚨"
        }

    # 📡 [BAN ĐIỀU PHỐI / HÀNH CHÍNH]
    return {
        "dept_name": "BAN ĐIỀU PHỐI & HÀNH CHÍNH NỘI BỘ",
        "clearance": "⚙️ THÔNG TIN HỆ THỐNG (SYSTEM STATUS)",
        "serial_prefix": "JKAI-ADMIN-",
        "emoji": "📡"
    }

# ==========================================
# 🛰️ ĐỘI TUẦN TRA LOG (LISTENER)
# ==========================================
def log_listener():
    print("🛰️ [JKAI-TELEGRAM] Mobile Command Center ONLINE.")
    
    # Cache to prevent any duplication (FIFO sliding window list of processed log IDs & hashes)
    processed_ids = []
    processed_messages = []
    pin_map = {}

    # Thread-safe caches and variables for smooth streaming on Telegram
    pinned_content_cache = {}
    pinned_ts_cache = {}
    last_edit_time = {}
    pending_texts = {}
    pending_markups = {}
    active_timers = {}
    stream_lock = threading.Lock()

    def flush_pin(p_id):
        with stream_lock:
            if p_id not in pin_map:
                return
            txt = pending_texts.get(p_id)
            mkup = pending_markups.get(p_id)
            if not txt:
                return
            try:
                bot.edit_message_text(
                    chat_id=MASTER_ID,
                    message_id=pin_map[p_id],
                    text=txt,
                    parse_mode="HTML",
                    reply_markup=mkup
                )
                last_edit_time[p_id] = time.time()
            except Exception as err:
                if "message is not modified" not in str(err).lower():
                    print(f"❌ [TELE-THROTTLE-FLUSH-ERR]: {err}")
            finally:
                active_timers.pop(p_id, None)

    while True:
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe("monitor:log_channel")
            # [DEDUP-FIX]: Chỉ subscribe monitor:log_channel.
            # engine.py publish cùng payload vào cả log_channel VÀ progress_channel,
            # subscribe cả 2 sẽ nhận mỗi log 2 lần → Telegram hiển thị trùng lặp.
            # progress_channel dành riêng cho Frontend Dashboard (streaming progress bar).
            print("📡 [TELE-SYNC]: Kết nối Redis Pub/Sub thành công.")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        
                        # Deduplication Protocol using Stable IDs
                        log_id = data.get("id")
                        pin_id = data.get("pin_id")
                        is_pin = bool(pin_id)
                        
                        raw_msg = data.get("msg", "")
                        
                        is_dup_packet = False
                        with stream_lock:
                            if is_pin:
                                last_ts = pinned_ts_cache.get(pin_id, 0.0)
                                current_ts = float(data.get("ts", 0.0))
                                
                                is_newer = current_ts > last_ts
                                is_same_but_full_flush = (abs(current_ts - last_ts) < 1e-5) and not data.get("is_delta", False)
                                
                                if is_newer or is_same_but_full_flush:
                                    current_content = pinned_content_cache.get(pin_id, "")
                                    if data.get("is_delta", False):
                                        new_content = current_content + raw_msg
                                    else:
                                        new_content = raw_msg
                                    pinned_content_cache[pin_id] = new_content
                                    pinned_ts_cache[pin_id] = current_ts
                                    clean_msg = new_content.strip()
                                else:
                                    is_dup_packet = True
                            else:
                                clean_msg = raw_msg.strip()
                        
                        if not clean_msg: continue
                        
                        # Lọc triệt để mọi thẻ [TAG] ở đầu dòng
                        prev_msg = None
                        while clean_msg != prev_msg:
                            prev_msg = clean_msg
                            clean_msg = re.sub(r'^([^\[a-zA-Z0-9]*?)\[[A-Z0-9_\s-]+\]:?\s*', r'\1', clean_msg)
                        clean_msg = clean_msg.strip()
                        if not clean_msg: continue
                        
                        # Allow stealth logs on Telegram only if they are pinned (updating in-place)
                        if data.get("stealth", False) and not is_pin:
                            continue

                        # 1. Track ID for future auditing (log not blocked — root cause fixed upstream)
                        if not is_pin and log_id:
                            if log_id not in processed_ids:
                                processed_ids.append(log_id)
                                if len(processed_ids) > 500:
                                    processed_ids.pop(0)
                        
                        tag = data.get("tag", "SYSTEM").upper()
                        task_id = data.get("task_id", "manual")

                        # 2. Dedup hash for safety (root cause = subscribing 2 channels fixed, this is secondary guard)
                        if not is_pin:
                            msg_hash = hashlib.md5(f"{task_id}:{data.get('tag')}:{clean_msg}".encode()).hexdigest()
                            if msg_hash in processed_messages:
                                continue  # Safety guard: skip truly identical messages
                            processed_messages.append(msg_hash)
                            if len(processed_messages) > 500:
                                processed_messages.pop(0)

                        markup = None
                        if any(k in clean_msg for k in ["Phê duyệt", "Kế hoạch", "Master có phê duyệt"]):
                            markup = types.InlineKeyboardMarkup()
                            btn_text = "✅ PHÊ DUYỆT"
                            if "Kế hoạch" in clean_msg: btn_text = "🚀 TRIỂN KHAI"
                            markup.add(
                                types.InlineKeyboardButton(btn_text, callback_data=f"approve_{task_id}"),
                                types.InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"reject_{task_id}")
                            )

                        # 💎 [AESTHETIC-TELE-MSG]: Match the beautiful progress bar and operational style
                        prefix = "👑" if tag in ["MASTER", "MASTER_WEB", "MASTER_TELE"] else "🧠" if tag in ["JKAI", "MISSION_RESULT", "DONE", "RESULT", "THOUGHT"] else "🚨" if tag in ["ERROR", "CRITICAL", "WARN"] else "⚙️" if tag == "SYSTEM" else "📈" if tag in ["HEARTBEAT", "PROGRESS"] else "⚡"
                        
                        raw_tag = tag.upper()
                        is_zenith_msg = "ZENITH" in raw_msg or "ZENITH" in task_id
                        if "GATEWAY" in raw_tag or "RECEPTIONIST" in raw_tag:
                            action_label = "Ban Trợ Lý"
                        elif "PLANNER" in raw_tag or "THOUGHT" in raw_tag:
                            action_label = "Ban Kế Hoạch"
                        elif "EXECUTOR" in raw_tag or "ALPHA" in raw_tag or "BETA" in raw_tag:
                            action_label = "Ban Thực Thi"
                        elif "SUMMARIZER" in raw_tag or "SYNTHESIS" in raw_tag:
                            action_label = "Ban Thư Ký"
                        elif "CRITIC" in raw_tag or "AUDIT" in raw_tag or "REVIEW" in raw_tag or "GUARDRAIL" in raw_tag:
                            action_label = "Ban Kiểm Soát"
                        elif (
                            "DATA_SCOUT" in raw_tag or "RESEARCH" in raw_tag or "SEARCH" in raw_tag or 
                            "ANTIGRAVITY" in raw_tag or "FORGE" in raw_tag or
                            "CREATOR" in raw_tag or "KIẾN TẠO" in raw_tag or "KIENTAO" in raw_tag or 
                            "TÌNH BÁO" in raw_tag or "TINHBAO" in raw_tag
                        ):
                            action_label = "Ban Trợ Lý"
                        elif "MASTER" in raw_tag or "USER" in raw_tag:
                            action_label = "Chủ Tịch"
                        elif "MISSION_RESULT" in raw_tag or "RESULT" in raw_tag or "DONE" in raw_tag or "JKAI" in raw_tag:
                            action_label = "JKAI"
                        else:
                            action_label = "Ban Hành Chính"
                        
                        # Keep full length for dynamic pinned updates (safely under 4000 characters)
                        short_msg = clean_msg[:3800] if is_pin else (clean_msg[:300] + "..." if len(clean_msg) > 300 else clean_msg)
                        
                        is_thought = "THOUGHT]" in clean_msg or "THOUGHT:" in data.get("full_tag", "") or (is_pin and bool(data.get("source")))
                        
                        source_role = data.get("source", "") or tag
                        if is_pin and (tag == "THOUGHT" or is_thought):
                            short_msg = re.sub(r'^🧠\s*\[.*?THOUGHT\]:\s*', '', short_msg)
                            if not source_role or source_role == "THOUGHT":
                                source_role = "MODEL"
                        
                        meta = get_corporate_metadata(tag, source_role)
                        
                        from datetime import datetime
                        now_ts = data.get("ts") or time.time()
                        dt = datetime.fromtimestamp(now_ts)
                        date_str = dt.strftime("%Y%m%d")
                        formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
                        
                        log_id = data.get("id")
                        if log_id:
                            hash_str = str(log_id)[-4:].upper()
                        else:
                            content_hash = hashlib.md5(f"{tag}:{clean_msg}".encode("utf-8")).hexdigest()
                            hash_str = content_hash[-4:].upper()
                        
                        doc_serial = f"{meta['serial_prefix']}{date_str}-{hash_str}"
                        
                        header_title = "BÁO CÁO NGHIỆP VỤ"
                        if tag in ["ERROR", "CRITICAL"]:
                            header_title = "BÁO CÁO SỰ CỐ KHẨN"
                        elif tag == "WARN":
                            header_title = "CẢNH BÁO HOẠT ĐỘNG"
                        elif tag in ["AUTH", "SECURITY"]:
                            header_title = "THẨM ĐỊNH BẢO MẬT"
                        elif tag.startswith("MASTER") or tag == "USER":
                            header_title = "CHỈ THỊ THƯỢNG KHẨN"
                        elif tag == "ZENITH":
                            header_title = "BÁO CÁO CHIẾN LƯỢC"
                        elif tag in ["MISSION_RESULT", "DONE", "RESULT"]:
                            header_title = "BÁO CÁO KẾT QUẢ SỨ MỆNH"

                        formatted_msg = translate_markdown_to_html(short_msg)
                        formatted_msg = formatted_msg.replace("<i>[Đang suy nghĩ]</i>", "<b>[Đang suy nghĩ]</b>")
                        formatted_msg = formatted_msg.replace("<i>[Đang suy nghĩ...]</i>", "<b>[Đang suy nghĩ...]</b>")
                        formatted_msg = formatted_msg.replace("<i>[Đang trả lời...]</i>", "<b>[Đang trả lời...]</b>")
                        formatted_msg = formatted_msg.replace("&gt; ", "┃ ").replace("&gt;", "┃ ")

                        final_text = (
                            f"{prefix} <b>[{action_label}]</b> <code>({formatted_time.split(' ')[1]})</code>:\n"
                            f"{formatted_msg}"
                        )

                        # 🔄 IN-PLACE MESSAGE EDIT!
                        with stream_lock:
                            if is_pin and pin_id in pin_map:
                                pending_texts[pin_id] = final_text
                                pending_markups[pin_id] = markup
                                
                                now_time = time.time()
                                time_since_last_edit = now_time - last_edit_time.get(pin_id, 0)
                                
                                if time_since_last_edit > 1.2:
                                    if pin_id in active_timers:
                                        active_timers[pin_id].cancel()
                                        del active_timers[pin_id]
                                    try:
                                        bot.edit_message_text(
                                            chat_id=MASTER_ID,
                                            message_id=pin_map[pin_id],
                                            text=final_text,
                                            parse_mode="HTML",
                                            reply_markup=markup
                                        )
                                        last_edit_time[pin_id] = now_time
                                    except Exception as edit_err:
                                        if "message is not modified" not in str(edit_err).lower():
                                            print(f"❌ [TELE-EDIT-ERR] {edit_err}")
                                else:
                                    if pin_id not in active_timers:
                                        t = threading.Timer(1.2 - time_since_last_edit, flush_pin, args=[pin_id])
                                        active_timers[pin_id] = t
                                        t.start()
                                continue

                        if is_pin:
                            msg_obj = safe_send_message(MASTER_ID, final_text, parse_mode="HTML", reply_markup=markup)
                            if msg_obj:
                                with stream_lock:
                                    pin_map[pin_id] = msg_obj.message_id
                                    last_edit_time[pin_id] = time.time()
                        elif markup or tag in ["MISSION_RESULT", "DONE", "ERROR", "CRITICAL", "MASTER", "MASTER_TELE", "MASTER_WEB"]:
                            send_immediate_log(final_text, markup=markup)
                        else:
                            queue_non_pinned_log(final_text)
                    except Exception as e:
                        print(f"❌ [LOG-LISTENER-MSG-ERR] {e}")
        except Exception as conn_err:
            print(f"⚠️ [TELE-SYNC-ERR]: Mất kết nối Redis. Đang kết nối lại sau 3s... Lỗi: {conn_err}")
            time.sleep(3)

# ==========================================
# 🛠️ HANDLERS (TELEGRAM EVENTS)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.from_user.id != MASTER_ID: return
    try:
        action, task_id = call.data.split("_")
        endpoint = "/hitl_approve" if action == "approve" else "/hitl_reject"
        with httpx.Client(timeout=30.0) as client:
            res = client.post(f"{CONTROL_PLANE_URL}{endpoint}", json={"task_id": task_id})
            data = res.json()
            bot.answer_callback_query(call.id, text=data.get("msg", "Đã thực thi"))
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception as e:
        bot.answer_callback_query(call.id, text=f"Lỗi: {e}")

@bot.message_handler(commands=['start', 'help'])
def cmd_help(message):
    if message.from_user.id != MASTER_ID: return
    try:
        task_id = f"tele_{int(time.time())}"
        payload = {
            "task_id": task_id,
            "goal": "/help",
            "mode": "fast",
            "source": "TELEGRAM",
            "ts": time.time()
        }
        with httpx.Client(timeout=15.0) as client:
            res = client.post(f"{CONTROL_PLANE_URL}/execute", json=payload)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("answer") or data.get("msg") or "Không có câu trả lời thưa Master."
                formatted_help = translate_markdown_to_html(answer)
                
                # 💎 [AESTHETIC-UPGRADE]: Thêm lời chào nồng nhiệt nếu là lệnh /start
                if message.text.startswith('/start'):
                    formatted_help = f"🚀 <b>Khởi động Giao thức Chủ quyền. Chào mừng Master LeeTrung trở lại!</b>\n\n{formatted_help}"
                
                safe_send_message(MASTER_ID, formatted_help, parse_mode="HTML")
            else:
                safe_send_message(MASTER_ID, f"⚠️ <b>LỖI HỆ THỐNG:</b> Không thể kết nối Trung tâm <i>(Mã lỗi: {res.status_code})</i>.", parse_mode="HTML")
    except Exception as e:
        safe_send_message(MASTER_ID, f"❌ <b>LỖI KẾT NỐI:</b> {str(e)}", parse_mode="HTML")

@bot.message_handler(commands=['cancel', 'stop'])
def cmd_stop(message):
    """🛑 [EMERGENCY-STOP]: Lệnh ngắt mạch khẩn cấp từ Telegram."""
    if message.from_user.id != MASTER_ID: return
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{CONTROL_PLANE_URL}/api/commander/stop", json={"task_id": "all"})
            data = res.json()
            safe_send_message(MASTER_ID, f"🛑 <b>HỆ THỐNG:</b> {data.get('msg')}", parse_mode="HTML")
    except Exception as e:
        safe_send_message(MASTER_ID, f"❌ <b>LỖI NGẮT MẠCH:</b> {str(e)}", parse_mode="HTML")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if message.from_user.id != MASTER_ID: return
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        path = f"/tmp/audio/voice_{message.message_id}.ogg"
        with open(path, 'wb') as f: f.write(downloaded_file)
        
        bot.send_chat_action(MASTER_ID, 'typing')
        if whisper_model:
            segments, _ = whisper_model.transcribe(path, beam_size=5)
            text = "".join([s.text for s in segments])
            bot.reply_to(message, f"🎙️ <b>Bản ký âm:</b> <i>{text}</i>", parse_mode="HTML")
            execute_neural_command(text)
        else:
            bot.reply_to(message, "❌ Giao thức Whisper chưa được nạp.")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi xử lý giọng nói: {e}")

# ==========================================
# 👁️ GIAO THỨC THỊ GIÁC CỤC BỘ (LOCAL VISION)
# 👁️ [VISION-GATEWAY]: Sử dụng Đầu mối Trung tâm
def analyze_image_sync(base64_image: str) -> str:
    try:
        payload = {
            "prompt": "Mô tả thật chi tiết bức ảnh này bằng tiếng Việt. Trích xuất bất kỳ văn bản nào có trong ảnh.",
            "image_path": "telegram_upload", # Placeholder
            "image_data": base64_image # Gửi thẳng data
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{CONTROL_PLANE_URL}/api/vision", json=payload)
            if resp.status_code == 200:
                return resp.json().get("analysis", "").strip()
            return ""
    except Exception as e:
        print(f"❌ [VISION-RELAY-ERR] {e}")
        return ""

# ==========================================
# 📂 GIAO THỨC GOM CỤM THƯ MỤC/HÌNH ẢNH (MEDIA GROUP AGGREGATOR)
# ==========================================
media_group_buffer = {}  # {media_group_id: [messages]}
media_group_timers = {}  # {media_group_id: threading.Timer}
buffer_lock = threading.Lock()

def process_media_group(media_group_id):
    try:
        with buffer_lock:
            messages = media_group_buffer.pop(media_group_id, [])
            media_group_timers.pop(media_group_id, None)
            
        if not messages:
            return
            
        messages.sort(key=lambda m: m.message_id)
        
        captions = []
        files_saved = []
        images_base64 = []
        
        for msg in messages:
            if msg.caption:
                c = msg.caption.strip()
                if c not in captions:
                    captions.append(c)
            
            if msg.photo:
                try:
                    file_id = msg.photo[-1].file_id
                    file_info = bot.get_file(file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    encoded_string = base64.b64encode(downloaded_file).decode('utf-8')
                    images_base64.append(encoded_string)
                except Exception as img_err:
                    print(f"❌ [MEDIA-GROUP-IMG-ERR]: {img_err}")
            elif msg.document:
                try:
                    file_name = msg.document.file_name
                    file_info = bot.get_file(msg.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    
                    input_dir = os.path.join(os.getcwd(), "files/Input")
                    os.makedirs(input_dir, exist_ok=True)
                    save_path = os.path.join(input_dir, file_name)
                    with open(save_path, 'wb') as f:
                        f.write(downloaded_file)
                    files_saved.append(file_name)
                except Exception as doc_err:
                    print(f"❌ [MEDIA-GROUP-DOC-ERR]: {doc_err}")
        
        base_goal = " ".join(captions)
        mode = "auto"
        if base_goal.upper().startswith("[FAST]"):
            mode = "fast"
            base_goal = base_goal[6:].strip()
        elif base_goal.upper().startswith("[DEEP]"):
            mode = "deep"
            base_goal = base_goal[6:].strip()
            
        vision_descriptions = []
        if images_base64:
            bot.send_chat_action(MASTER_ID, 'upload_photo')
            status_msg = safe_send_message(MASTER_ID, f"👁️ <b>VISION:</b> Đang dùng Moondream Cục bộ để dịch {len(images_base64)} hình ảnh...", parse_mode="HTML")
            for idx, img_b64 in enumerate(images_base64):
                desc = analyze_image_sync(img_b64)
                if desc:
                    vision_descriptions.append(f"[Ảnh {idx+1}]: {desc}")
            try: bot.delete_message(MASTER_ID, status_msg.message_id)
            except Exception: pass
            
        goal = base_goal
        if not goal:
            if files_saved and vision_descriptions:
                desc_str = "\n".join(vision_descriptions)
                files_str = ", ".join(files_saved)
                goal = f"[FILE_ONLY]: {files_str}\n\n[THỊ GIÁC - MOONDREAM]:\n{desc_str}"
            elif files_saved:
                goal = f"[FILE_ONLY]: {', '.join(files_saved)}"
            elif vision_descriptions:
                desc_str = "\n".join(vision_descriptions)
                goal = f"[IMAGE_ONLY]\n\n[THỊ GIÁC - MOONDREAM]:\n{desc_str}"
        else:
            if files_saved:
                goal = f"{goal}\n\n[TỆP ĐÍNH KÈM]: {', '.join(files_saved)}"
            if vision_descriptions:
                desc_str = "\n".join(vision_descriptions)
                goal = f"{goal}\n\n[THỊ GIÁC - MOONDREAM]:\n{desc_str}"
                
        if files_saved and vision_descriptions:
            safe_send_message(MASTER_ID, f"📂 <b>MEDIA-GROUP:</b> Đã tiếp nhận {len(files_saved)} file và {len(images_base64)} ảnh vào vùng `Input`.", parse_mode="HTML")
        elif files_saved:
            safe_send_message(MASTER_ID, f"📂 <b>MEDIA-GROUP:</b> Đã nhận {len(files_saved)} file vào vùng `Input`.", parse_mode="HTML")
        elif vision_descriptions:
            safe_send_message(MASTER_ID, f"👁️ <b>MEDIA-GROUP:</b> Đã giải mã {len(images_base64)} hình ảnh thành công.", parse_mode="HTML")
            
        execute_neural_command(goal, images=[], mode=mode)
    except Exception as e:
        print(f"❌ [MEDIA-GROUP-CRITICAL-ERR]: {e}")
        safe_send_message(MASTER_ID, f"❌ Lỗi xử lý cụm tin nhắn: {e}")

def check_and_buffer_media_group(message):
    if message.media_group_id:
        with buffer_lock:
            if message.media_group_id not in media_group_buffer:
                media_group_buffer[message.media_group_id] = []
            media_group_buffer[message.media_group_id].append(message)
            
            if message.media_group_id in media_group_timers:
                media_group_timers[message.media_group_id].cancel()
                
            timer = threading.Timer(1.2, process_media_group, args=[message.media_group_id])
            media_group_timers[message.media_group_id] = timer
            timer.start()
        return True
    return False

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.from_user.id != MASTER_ID: return
    if check_and_buffer_media_group(message): return
    try:
        bot.send_chat_action(MASTER_ID, 'upload_photo')
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        encoded_string = base64.b64encode(downloaded_file).decode('utf-8')
        
        goal = message.caption or "[IMAGE_ONLY]"
        mode = "auto"
        if goal.upper().startswith("[FAST]"):
            mode = "fast"
            goal = goal[6:].strip()
        elif goal.upper().startswith("[DEEP]"):
            mode = "deep"
            goal = goal[6:].strip()
            
        bot.reply_to(message, "👁️ <b>VISION:</b> Đang dùng Moondream Cục bộ (Local) để dịch ảnh thành trí thức...", parse_mode="HTML")
        vision_text = analyze_image_sync(encoded_string)
        
        if vision_text:
            goal = f"{goal}\n\n[THỊ GIÁC - MOONDREAM]:\n{vision_text}"
            bot.reply_to(message, f"👁️ <b>ĐÃ GIẢI MÃ:</b>\n<i>{vision_text}</i>\n\nĐang truyền lên Não Bộ Trung Ương...", parse_mode="HTML")
        else:
            bot.reply_to(message, "⚠️ <b>VISION LỖI:</b> Không thể kết nối Mô hình Thị giác Cục bộ.", parse_mode="HTML")
            
        execute_neural_command(goal, images=[], mode=mode)
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi xử lý hình ảnh: {e}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id != MASTER_ID: return
    if check_and_buffer_media_group(message): return
    try:
        file_name = message.document.file_name
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_dir = os.path.join(os.getcwd(), "files/Input")
        os.makedirs(input_dir, exist_ok=True)
        save_path = os.path.join(input_dir, file_name)
        
        with open(save_path, 'wb') as f:
            f.write(downloaded_file)
            
        goal = message.caption or f"[FILE_ONLY]: {file_name}"
        bot.reply_to(message, f"📂 <b>FILE:</b> Đã tiếp nhận `{file_name}` và nạp vào vùng `Input`.", parse_mode="HTML")
        execute_neural_command(goal)
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi xử lý tệp tin: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    if message.from_user.id != MASTER_ID: return
    text = message.text.strip()
    
    # 🛡️ [STEALTH-PROTOCOL]: Kiểm tra mã băm bảo mật
    input_hash = hashlib.sha256(text.encode()).hexdigest()
    if input_hash == MASTER_HASH:
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        # Chuyển về Brain xử lý xác thực ngầm
        execute_neural_command(text)
        return

    mode = "auto"
    if text.upper().startswith("[FAST]"):
        mode = "fast"
        text = text[6:].strip()
    elif text.upper().startswith("[DEEP]"):
        mode = "deep"
        text = text[6:].strip()
    
    execute_neural_command(text, mode=mode)

if __name__ == "__main__":
    # 🕵️ [BOOT-SYNC]: Đảm bảo internet sẵn sàng trước khi nạp linh hồn
    if not wait_for_internet():
        print("⚠️ [RESILIENCE]: Không thể thiết lập kết nối internet sau 60s. Đang khởi động ở chế độ offline...")
    
    threading.Thread(target=init_whisper, daemon=True).start()
    threading.Thread(target=log_listener, daemon=True).start()
    print("🚀 [JKAI-TELEGRAM] Bot is polling...")
    bot.infinity_polling()
