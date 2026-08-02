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
from datetime import datetime, timezone
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

def safe_edit_message_text(chat_id, message_id, text, p_id=None, last_edit_map=None, **kwargs):
    """
    🛡️ [TELE-RATE-LIMIT-GUARD]: Thao tác sửa tin nhắn Telegram an toàn tuyệt đối.
    Tránh lỗi 429 Too Many Requests bằng cách tự động phân tích Retry-After và áp đặt Cooldown.
    """
    try:
        res = bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
        if p_id and isinstance(last_edit_map, dict):
            last_edit_map[p_id] = time.time()
        return res
    except Exception as err:
        err_str = str(err).lower()
        if "message is not modified" in err_str:
            return None
            
        if "too many requests" in err_str or "429" in err_str:
            import re
            m = re.search(r'retry after (\d+)', err_str)
            retry_after = int(m.group(1)) if m else 10
            cooldown_period = retry_after + 2.0
            if p_id and isinstance(last_edit_map, dict):
                last_edit_map[p_id] = time.time() + cooldown_period
                print(f"⚠️ [TELE-429-BACKOFF]: Telegram Rate Limit hit cho {p_id}. Tự động tạm hoãn sửa tin nhắn trong {cooldown_period:.0f}s.")
            else:
                print(f"⚠️ [TELE-429-BACKOFF]: Telegram Rate Limit hit. Tự động tạm hoãn sửa tin nhắn trong {cooldown_period:.0f}s.")
            return None
            
        print(f"❌ [TELE-EDIT-ERR] {err}")
        return None

def safe_send_message(chat_id, text, **kwargs):
    """🚀 [RESILIENT-SENDER]: Giao thức gửi tin nhắn bền bỉ với cơ chế Tái thử."""
    import random
    time.sleep(random.uniform(0.2, 0.6))
    max_retries = 10
    for i in range(max_retries):
        try:
            return bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            if i == max_retries - 1: 
                print(f"❌ [TELE-CRITICAL]: Mất kết nối vĩnh viễn: {e}")
                raise e
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
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
    html = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', html)
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    html = re.sub(r'^\s*[-*]\s+', '• ', html, flags=re.MULTILINE)
    html = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', html, flags=re.MULTILINE)
    html = re.sub(r'^[\s]*[—\-_]{10,}[\s]*$', '<s>───</s>', html, flags=re.MULTILINE)
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
def execute_neural_command(goal, images=None, mode="fast"):
    try:
        task_id = f"tele_{int(time.time())}"
        payload = {
            "task_id": task_id,
            "goal": goal,
            "mode": mode,
            "source": "TELEGRAM",
            "ts": time.time(),
            "images": images or []
        }
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
    if tag_upper.startswith("MASTER"):
        return {"dept_name": "VĂN PHÒNG CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ", "clearance": "⚡ CHỈ THỊ THƯỢNG KHẨN (SUPREME DIRECTIVE)", "serial_prefix": "JKAI-CHAIRMAN-", "emoji": "👑"}
    if tag_upper == "JKAI":
        return {"dept_name": "BAN ĐIỀU HÀNH TRUNG ƯƠNG (CENTRAL OPS BOARD)", "clearance": "💎 NGHỊ QUYẾT TOÀN DIỆN (EXECUTIVE DECREE)", "serial_prefix": "JKAI-CORE-", "emoji": "💎"}
    if tag_upper == "ANTIGRAVITY":
        return {"dept_name": "PHÂN KHU KIẾN TẠO KIẾN TRÚC & TƯ DUY", "clearance": "🌌 ĐỀ XUẤT CẤU TRÚC (ARCHITECTURAL INITIATIVE)", "serial_prefix": "JKAI-ANTIGRAV-", "emoji": "🌌"}
    if "GATEWAY" in tag_upper or "RECEPTIONIST" in tag_upper or "GATEWAY" in src_upper or "RECEPTIONIST" in src_upper:
        return {"dept_name": "BAN TRỢ LÝ & ĐỐI NGOẠI TẬP ĐOÀN", "clearance": "🟢 THÔNG THƯỜNG (PUBLIC ACCESSIBLE)", "serial_prefix": "JKAI-RECEPT-", "emoji": "🛎️"}
    if "PLANNER" in tag_upper or "THOUGHT" in tag_upper or "PLANNER" in src_upper or "THOUGHT" in src_upper:
        return {"dept_name": "PHÒNG HOẠCH ĐỊNH CHIẾN LƯỢC & THIẾT LỘ TRÌNH", "clearance": "🔵 PHƯƠNG ÁN CHIẾN LƯỢC (STRATEGIC PLAN)", "serial_prefix": "JKAI-PLAN-", "emoji": "🎯"}
    if "EXECUTOR" in tag_upper or "ALPHA" in tag_upper or "BETA" in tag_upper or "EXECUTOR" in src_upper or "ALPHA" in src_upper or "BETA" in src_upper:
        return {"dept_name": "BAN THỰC THI & TRIỂN KHAI KỸ THUẬT", "clearance": "🟡 LƯU HÀNH NỘI BỘ (INTERNAL ONLY)", "serial_prefix": "JKAI-EXEC-", "emoji": "⚙️"}
    if "CRITIC" in tag_upper or "AUDIT" in tag_upper or "REVIEW" in tag_upper or "CRITIC" in src_upper or "AUDIT" in src_upper or "REVIEW" in src_upper:
        return {"dept_name": "BAN KIỂM SOÁT NỘI BỘ & AN NINH TẬP ĐOÀN", "clearance": "🔴 TỐI MẬT (HIGHLY CONFIDENTIAL)", "serial_prefix": "JKAI-AUDIT-", "emoji": "🛡️"}
    if "SUMMARIZER" in tag_upper or "SUMMARIZER" in src_upper:
        return {"dept_name": "BAN THƯ KÝ & TỔNG HỢP VĂN PHÒNG ĐIỀU HÀNH", "clearance": "🟡 LƯU HÀNH NỘI BỘ (INTERNAL ONLY)", "serial_prefix": "JKAI-SEC-", "emoji": "✍️"}
    if tag_upper == "ERROR":
        return {"dept_name": "BAN KIỂM SOÁT & KHẮC PHỤC SỰ CỐ KHẨN CẤP", "clearance": "🚨 SỰ CỐ KHẨN CẤP (EMERGENCY ALARM)", "serial_prefix": "JKAI-ERR-", "emoji": "🚨"}
    return {"dept_name": "BAN ĐIỀU PHỐI & HÀNH CHÍNH NỘI BỘ", "clearance": "⚙️ THÔNG TIN HỆ THỐNG (SYSTEM STATUS)", "serial_prefix": "JKAI-ADMIN-", "emoji": "📡"}

# ==========================================
# 🛰️ ĐỘI TUẦN TRA LOG (LISTENER)
# ==========================================
def log_listener():
    print("🛰️ [JKAI-TELEGRAM] Mobile Command Center ONLINE.")
    processed_ids = []
    processed_messages = []
    sent_content_window = {}
    pin_map = {}
    pinned_content_cache = {}
    pinned_ts_cache = {}
    last_edit_time = {}
    pending_texts = {}
    pending_markups = {}
    active_timers = {}
    stream_lock = threading.Lock()

    def flush_pin(p_id):
        with stream_lock:
            if p_id not in pin_map: return
            txt = pending_texts.get(p_id)
            mkup = pending_markups.get(p_id)
            if not txt: return
            try:
                safe_edit_message_text(chat_id=MASTER_ID, message_id=pin_map[p_id], text=txt, p_id=p_id, last_edit_map=last_edit_time, parse_mode="HTML", reply_markup=mkup)
            finally:
                active_timers.pop(p_id, None)

    while True:
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe("monitor:log_channel")
            print("📡 [TELE-SYNC]: Kết nối Redis Pub/Sub thành công.")
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        log_id = data.get("id")
                        pin_id = data.get("pin_id")
                        is_pin = bool(pin_id)
                        raw_msg = data.get("msg", "")
                        
                        with stream_lock:
                            if is_pin:
                                last_ts = pinned_ts_cache.get(pin_id, 0.0)
                                current_ts = float(data.get("ts", 0.0))
                                is_newer = current_ts > last_ts
                                is_same_but_full_flush = (abs(current_ts - last_ts) < 1e-5) and not data.get("is_delta", False)
                                if is_newer or is_same_but_full_flush:
                                    current_content = pinned_content_cache.get(pin_id, "")
                                    new_content = current_content + raw_msg if data.get("is_delta", False) else raw_msg
                                    pinned_content_cache[pin_id] = new_content
                                    pinned_ts_cache[pin_id] = current_ts
                                    clean_msg = new_content.strip()
                                else:
                                    continue
                            else:
                                clean_msg = raw_msg.strip()
                        
                        if not clean_msg: continue
                        
                        prev_msg = None
                        while clean_msg != prev_msg:
                            prev_msg = clean_msg
                            clean_msg = re.sub(r'^([^\[a-zA-Z0-9]*?)\[[A-Z0-9_\s-]+\]:?\s*', r'\1', clean_msg)
                        clean_msg = clean_msg.strip()
                        if not clean_msg: continue
                        
                        if data.get("stealth", False) and not is_pin: continue

                        # [STREAMING-FIREWALL]: Ngăn chặn tuyệt đối rác token stream (is_delta=True) phát trực tiếp lên Telegram
                        if not is_pin and (data.get("is_delta", False) or data.get("stream", False)):
                            continue

                        # [ISOLATION-GATE]: Lọc bỏ hoàn toàn tin nhắn ngầm từ OMNI-EVOLVE hoặc tiến trình nền [Task: None]/system khỏi kênh đàm thoại
                        t_id_check = str(data.get("task_id", "manual"))
                        if t_id_check in ("omni_evolve", "None", "NoneType", "system") or "OMNI-EVOLVE" in raw_msg or "Task: None" in raw_msg:
                            continue

                        if not is_pin and log_id:
                            if log_id in processed_ids:
                                continue
                            processed_ids.append(log_id)
                            if len(processed_ids) > 500: processed_ids.pop(0)
                        
                        tag = data.get("tag", "SYSTEM").upper()
                        task_id = data.get("task_id", "manual")

                        if not is_pin:
                            msg_hash = hashlib.md5(f"{task_id}:{data.get('tag')}:{clean_msg}".encode()).hexdigest()
                            if msg_hash in processed_messages: continue
                            processed_messages.append(msg_hash)
                            if len(processed_messages) > 500: processed_messages.pop(0)

                            # [SEMANTIC-DEDUPLICATION]: Bộ lọc lặp tin nhắn theo nội dung tinh gọn, bỏ qua tag hoặc mốc thời gian chênh lệch từ các module
                            if not tag.startswith("MASTER"):
                                pure_txt = re.sub(r'\[.*?\]|\d{2,4}[/-]\d{2,4}[/-]\d{2,4}|\d{2}:\d{2}:\d{2}(?:\.\d+)?|\b\d+\.\d+\b', '', clean_msg)
                                pure_txt = re.sub(r'[^\w\s]', '', pure_txt).strip().lower()
                                if len(pure_txt) > 5:
                                    pure_hash = hashlib.md5(pure_txt.encode()).hexdigest()
                                    now_ts_win = time.time()
                                    if pure_hash in sent_content_window and (now_ts_win - sent_content_window[pure_hash]) < 45.0:
                                        continue
                                    sent_content_window[pure_hash] = now_ts_win
                                    if len(sent_content_window) > 200:
                                        sent_content_window = {k: v for k, v in sent_content_window.items() if (now_ts_win - v) < 60.0}

                        markup = None
                        if any(k in clean_msg for k in ["Phê duyệt", "Kế hoạch", "Master có phê duyệt"]):
                            markup = types.InlineKeyboardMarkup()
                            btn_text = "✅ PHÊ DUYỆT" if "Kế hoạch" not in clean_msg else "🚀 TRIỂN KHAI"
                            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"approve_{task_id}"), types.InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"reject_{task_id}"))

                        prefix = "👑" if tag in ["MASTER", "MASTER_WEB", "MASTER_TELE"] else "🧠" if tag in ["JKAI", "MISSION_RESULT", "DONE", "RESULT", "THOUGHT"] else "🚨" if tag in ["ERROR", "CRITICAL", "WARN"] else "⚙️" if tag == "SYSTEM" else "📈" if tag in ["HEARTBEAT", "PROGRESS"] else "⚡"
                        
                        raw_tag = tag.upper()
                        if "GATEWAY" in raw_tag or "RECEPTIONIST" in raw_tag: action_label = "Ban Trợ Lý"
                        elif "PLANNER" in raw_tag or "THOUGHT" in raw_tag: action_label = "Ban Kế Hoạch"
                        elif "EXECUTOR" in raw_tag or "ALPHA" in raw_tag or "BETA" in raw_tag: action_label = "Ban Thực Thi"
                        elif "SUMMARIZER" in raw_tag or "SYNTHESIS" in raw_tag: action_label = "Ban Thư Ký"
                        elif "CRITIC" in raw_tag or "AUDIT" in raw_tag or "REVIEW" in raw_tag or "GUARDRAIL" in raw_tag: action_label = "Ban Kiểm Soát"
                        elif any(k in raw_tag for k in ["DATA_SCOUT", "RESEARCH", "SEARCH", "ANTIGRAVITY", "FORGE", "CREATOR", "KIẾN TẠO", "KIENTAO", "TÌNH BÁO", "TINHBAO"]): action_label = "Ban Trợ Lý"
                        elif "MASTER" in raw_tag or "USER" in raw_tag: action_label = "Master (Web)" if tag == "MASTER_WEB" else "Master"
                        elif any(k in raw_tag for k in ["MISSION_RESULT", "RESULT", "DONE", "JKAI"]): action_label = "JKAI"
                        else: action_label = "Ban Hành Chính"
                        
                        short_msg = clean_msg[:3800] if is_pin else (clean_msg[:3800] + "..." if len(clean_msg) > 3800 else clean_msg)
                        is_thought = "THOUGHT]" in clean_msg or "THOUGHT:" in data.get("full_tag", "") or (is_pin and bool(data.get("source")))
                        source_role = data.get("source", "") or tag
                        if is_pin and (tag == "THOUGHT" or is_thought):
                            short_msg = re.sub(r'^🧠\s*\[.*?THOUGHT\]:\s*', '', short_msg)
                            if not source_role or source_role == "THOUGHT": source_role = "MODEL"
                        
                        meta = get_corporate_metadata(tag, source_role)
                        now_ts = data.get("ts") or time.time()
                        tz_name = os.getenv("GENERIC_TIMEZONE", "Asia/Bangkok")
                        try:
                            import pytz
                            dt = datetime.fromtimestamp(now_ts, tz=timezone.utc).astimezone(pytz.timezone(tz_name))
                        except Exception:
                            dt = datetime.fromtimestamp(now_ts)
                        formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
                        
                        formatted_msg = translate_markdown_to_html(short_msg)
                        formatted_msg = formatted_msg.replace("<i>[Đang suy nghĩ]</i>", "<b>[Đang suy nghĩ]</b>").replace("<i>[Đang suy nghĩ...]</i>", "<b>[Đang suy nghĩ...]</b>").replace("<i>[Đang trả lời...]</i>", "<b>[Đang trả lời...]</b>").replace("&gt; ", "┃ ").replace("&gt;", "┃ ")

                        final_text = f"{prefix} <b>[{action_label}]</b> <code>({formatted_time.split(' ')[1]})</code>:\n{formatted_msg}"

                        with stream_lock:
                            if is_pin and pin_id in pin_map:
                                pending_texts[pin_id] = final_text
                                pending_markups[pin_id] = markup
                                now_time = time.time()
                                time_since_last_edit = now_time - last_edit_time.get(pin_id, 0)
                                edit_interval = 3.0 # Tần suất sửa tin nhắn Telegram tối thiểu 3s để tuân thủ Rate Limit
                                if time_since_last_edit > edit_interval:
                                    if pin_id in active_timers:
                                        active_timers[pin_id].cancel()
                                        del active_timers[pin_id]
                                    safe_edit_message_text(chat_id=MASTER_ID, message_id=pin_map[pin_id], text=final_text, p_id=pin_id, last_edit_map=last_edit_time, parse_mode="HTML", reply_markup=markup)
                                else:
                                    if pin_id not in active_timers:
                                        wait_time = max(edit_interval - time_since_last_edit, 0.5)
                                        t = threading.Timer(wait_time, flush_pin, args=[pin_id])
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
        payload = {"task_id": task_id, "goal": "/help", "mode": "fast", "source": "TELEGRAM", "ts": time.time()}
        with httpx.Client(timeout=15.0) as client:
            res = client.post(f"{CONTROL_PLANE_URL}/execute", json=payload)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("answer") or data.get("msg") or "Không có câu trả lời thưa Master."
                formatted_help = translate_markdown_to_html(answer)
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
# ==========================================
def analyze_image_sync(base64_image: str) -> str:
    try:
        payload = {"prompt": "Mô tả thật chi tiết bức ảnh này bằng tiếng Việt. Trích xuất bất kỳ văn bản nào có trong ảnh.", "image_path": "telegram_upload", "image_data": base64_image}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{CONTROL_PLANE_URL}/api/vision", json=payload)
            if resp.status_code == 200: return resp.json().get("analysis", "").strip()
            return ""
    except Exception as e:
        print(f"❌ [VISION-RELAY-ERR] {e}")
        return ""

# ==========================================
# 📂 GIAO THỨC GOM CỤM THƯ MỤC/HÌNH ẢNH (MEDIA GROUP AGGREGATOR)
# ==========================================
media_group_buffer = {}
media_group_timers = {}
buffer_lock = threading.Lock()

def process_media_group(media_group_id):
    try:
        with buffer_lock:
            messages = media_group_buffer.pop(media_group_id, [])
            media_group_timers.pop(media_group_id, None)
        if not messages: return
        messages.sort(key=lambda m: m.message_id)
        captions = []
        files_saved = []
        images_base64 = []
        for msg in messages:
            if msg.caption:
                c = msg.caption.strip()
                if c not in captions: captions.append(c)
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
                    with open(save_path, 'wb') as f: f.write(downloaded_file)
                    files_saved.append(file_name)
                except Exception as doc_err:
                    print(f"❌ [MEDIA-GROUP-DOC-ERR]: {doc_err}")
        
        base_goal = " ".join(captions)
        mode = "auto"
        if base_goal.upper().startswith("[FAST]"): mode, base_goal = "fast", base_goal[6:].strip()
        elif base_goal.upper().startswith("[DEEP]"): mode, base_goal = "deep", base_goal[6:].strip()
        elif base_goal.upper().startswith("[AUTO]"): mode, base_goal = "auto", base_goal[6:].strip()
            
        vision_descriptions = []
        if images_base64:
            bot.send_chat_action(MASTER_ID, 'upload_photo')
            status_msg = safe_send_message(MASTER_ID, f"👁️ <b>VISION:</b> Đang dùng Moondream Cục bộ để dịch {len(images_base64)} hình ảnh...", parse_mode="HTML")
            for idx, img_b64 in enumerate(images_base64):
                desc = analyze_image_sync(img_b64)
                if desc: vision_descriptions.append(f"[Ảnh {idx+1}]: {desc}")
            try: bot.delete_message(MASTER_ID, status_msg.message_id)
            except Exception: pass
            
        goal = base_goal
        vision_text = '\n'.join(vision_descriptions) if vision_descriptions else ''
        if not goal:
            if files_saved and vision_descriptions: goal = f"[FILE_ONLY]: {', '.join(files_saved)}\n\n[THỊ GIÁC - MOONDREAM]:\n{vision_text}"
            elif files_saved: goal = f"[FILE_ONLY]: {', '.join(files_saved)}"
            elif vision_descriptions: goal = f"[IMAGE_ONLY]\n\n[THỊ GIÁC - MOONDREAM]:\n{vision_text}"
        else:
            if files_saved: goal = f"{goal}\n\n[TỆP ĐÍNH KÈM]: {', '.join(files_saved)}"
            if vision_descriptions: goal = f"{goal}\n\n[THỊ GIÁC - MOONDREAM]:\n{vision_text}"
                
        if files_saved and vision_descriptions: safe_send_message(MASTER_ID, f"📂 <b>MEDIA-GROUP:</b> Đã tiếp nhận {len(files_saved)} file và {len(images_base64)} ảnh vào vùng `Input`.", parse_mode="HTML")
        elif files_saved: safe_send_message(MASTER_ID, f"📂 <b>MEDIA-GROUP:</b> Đã nhận {len(files_saved)} file vào vùng `Input`.", parse_mode="HTML")
        elif vision_descriptions: safe_send_message(MASTER_ID, f"👁️ <b>MEDIA-GROUP:</b> Đã giải mã {len(images_base64)} hình ảnh thành công.", parse_mode="HTML")
            
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
        if goal.upper().startswith("[FAST]"): mode, goal = "fast", goal[6:].strip()
        elif goal.upper().startswith("[DEEP]"): mode, goal = "deep", goal[6:].strip()
        elif goal.upper().startswith("[AUTO]"): mode, goal = "auto", goal[6:].strip()
            
        bot.reply_to(message, "👁️ <b>VISION:</b> Đang dùng Moondream Cục bộ (Local) để dịch ảnh thành tri thức...", parse_mode="HTML")
        vision_text = analyze_image_sync(encoded_string)
        
        if vision_text:
            goal = f"{goal}\n\n[THỊ GIÁC - MOONDREAM]:\n{vision_text}"
            bot.reply_to(message, f"👁️ <b>ĐÃ GIẢI MÃ:</b>\n<i>{vision_text}</i>\n\nĐang truyền lên Không Gian Tư Duy...", parse_mode="HTML")
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
        with open(save_path, 'wb') as f: f.write(downloaded_file)
            
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
        execute_neural_command(text)
        return

    mode = "fast"
    if text.upper().startswith("[FAST]"):
        mode = "fast"
        text = text[6:].strip()
    elif text.upper().startswith("[DEEP]"):
        mode = "deep"
        text = text[6:].strip()
    elif text.upper().startswith("[AUTO]"):
        mode = "auto"
        text = text[6:].strip()
    
    execute_neural_command(text, mode=mode)

if __name__ == "__main__":
    if not wait_for_internet():
        print("⚠️ [RESILIENCE]: Không thể thiết lập kết nối internet sau 60s. Đang khởi động ở chế độ offline...")
    
    # 🛡️ [TELE-TIMEOUT-GUARD]: Set HTTP Read/Connect timeouts higher than Telegram long_polling_timeout (20s)
    telebot.apihelper.READ_TIMEOUT = 90
    telebot.apihelper.CONNECT_TIMEOUT = 30

    threading.Thread(target=init_whisper, daemon=True).start()
    threading.Thread(target=log_listener, daemon=True).start()
    print("🚀 [JKAI-TELEGRAM] Bot is polling with resilient timeouts (READ_TIMEOUT=90s)...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=20)
        except Exception as e:
            print(f"⚠️ [TELE-POLLING-RETRY] Polling exception caught: {e}. Retrying in 5s...")
            time.sleep(5)
