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
        except:
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
            if res.status_code == 200:
                safe_send_message(MASTER_ID, f"✅ <b>HỆ THỐNG:</b> Đã tiếp nhận yêu cầu <i>(Mode: {mode.upper()})</i>. Đang khởi tạo luồng tư duy...", parse_mode="HTML")
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
        combined_text = "\n\n".join(non_pinned_buffer)
        non_pinned_buffer.clear()
        non_pinned_timer = None
    
    # Gửi qua safe_send_message
    safe_send_message(MASTER_ID, combined_text, parse_mode="HTML")

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
        if non_pinned_buffer:
            combined_text = "\n\n".join(non_pinned_buffer)
            non_pinned_buffer.clear()
            safe_send_message(MASTER_ID, combined_text, parse_mode="HTML")
        non_pinned_timer = None
    
    safe_send_message(MASTER_ID, text, parse_mode="HTML", reply_markup=markup)

# ==========================================
# 🛰️ ĐỘI TUẦN TRA LOG (LISTENER)
# ==========================================
def log_listener():
    print("🛰️ [JKAI-TELEGRAM] Mobile Command Center ONLINE.")
    
    # 🧠 Cache to prevent any duplication (FIFO sliding window list of processed log IDs & hashes)
    processed_ids = []
    processed_messages = []
    pin_map = {}

    while True:
        try:
            pubsub = redis_client.pubsub()
            pubsub.subscribe("monitor:log_channel", "monitor:progress_channel")
            print("📡 [TELE-SYNC]: Kết nối Redis Pub/Sub thành công.")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        
                        # 🛡️ Deduplication Protocol using Stable IDs
                        log_id = data.get("id")
                        clean_msg = data.get("msg", "").strip()
                        if not clean_msg: continue
                        
                        # 💎 [AESTHETIC-TELE-MSG]: Lọc triệt để mọi thẻ [TAG] ở đầu dòng
                        prev_msg = None
                        while clean_msg != prev_msg:
                            prev_msg = clean_msg
                            clean_msg = re.sub(r'^([^\[a-zA-Z0-9]*?)\[[A-Z0-9_\s-]+\]:?\s*', r'\1', clean_msg)
                        clean_msg = clean_msg.strip()
                        if not clean_msg: continue
                        
                        pin_id = data.get("pin_id")
                        is_pin = bool(pin_id)

                        # Allow stealth logs on Telegram only if they are pinned (updating in-place)
                        if data.get("stealth", False) and not is_pin:
                            continue

                        # 1. Deduplicate by ID (bypass for pinned streaming updates)
                        if not is_pin and log_id:
                            if log_id in processed_ids:
                                continue
                            processed_ids.append(log_id)
                            if len(processed_ids) > 500:
                                processed_ids.pop(0)
                        
                        tag = data.get("tag", "SYSTEM").upper()
                        task_id = data.get("task_id", "manual")

                        # 2. Deduplicate by Content Hash (bypass for pinned streaming updates)
                        if not is_pin:
                            msg_hash = hashlib.md5(f"{task_id}:{data.get('tag')}:{clean_msg}".encode()).hexdigest()
                            if msg_hash in processed_messages:
                                continue
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
                        if "GATEWAY" in raw_tag or "RECEPTIONIST" in raw_tag:
                            action_label = "Ban Lễ Tân"
                        elif "DISPATCHER" in raw_tag or "ROUTING" in raw_tag:
                            action_label = "Ban Điều Phối"
                        elif "PLANNER" in raw_tag or "THOUGHT" in raw_tag:
                            action_label = "Ban Kế Hoạch"
                        elif "EXECUTOR" in raw_tag or "ALPHA" in raw_tag or "BETA" in raw_tag:
                            action_label = "Ban Thực Thi"
                        elif "SUMMARIZER" in raw_tag:
                            action_label = "Ban Thư Ký"
                        elif "CRITIC" in raw_tag or "AUDIT" in raw_tag or "REVIEW" in raw_tag:
                            action_label = "Ban Kiểm Soát"
                        elif "DATA_SCOUT" in raw_tag or "RESEARCH" in raw_tag or "SEARCH" in raw_tag or "LATENCY" in raw_tag or "PERFORMANCE" in raw_tag or "METRICS" in raw_tag or "SIEUTIMKIEM" in raw_tag or "TIMKIEM" in raw_tag:
                            action_label = "Ban Hành Chính"
                        elif "SYSTEM" in raw_tag or "SYS_LOG" in raw_tag or "NEURAL" in raw_tag:
                            action_label = "Ban Kỹ Thuật"
                        elif "ENGINE" in raw_tag or "CORE" in raw_tag:
                            action_label = "Trung tâm Điều hành"
                        elif "MASTER" in raw_tag or "USER" in raw_tag:
                            action_label = "Ban Giám Đốc"
                        elif "MISSION_RESULT" in raw_tag or "RESULT" in raw_tag:
                            action_label = "Kết quả"
                        else:
                            action_label = data.get('action') or tag.replace('_', ' ').title()
                        
                        # Keep full length for dynamic pinned updates
                        short_msg = clean_msg[:4000] if is_pin else (clean_msg[:300] + "..." if len(clean_msg) > 300 else clean_msg)
                        
                        is_thought = "THOUGHT]" in clean_msg or "THOUGHT:" in data.get("full_tag", "") or (is_pin and bool(data.get("source")))
                        
                        if is_pin and (tag == "THOUGHT" or is_thought):
                            # Lấy role name từ source field
                            role_name = data.get("source", "") or tag
                            
                            # Loại bỏ tiền tố "🧠 [ROLE THOUGHT]:" để lấy nội dung thuần
                            short_msg = re.sub(r'^🧠\s*\[.*?THOUGHT\]:\s*', '', short_msg)
                            
                            if not role_name or role_name == "THOUGHT":
                                role_name = "MODEL"
                            role_name = role_name.upper()
                            
                            display_role = role_name
                            if "GATEWAY" in role_name or "RECEPTIONIST" in role_name:
                                display_role = "Ban Lễ Tân"
                            elif "DISPATCHER" in role_name or "ROUTING" in role_name:
                                display_role = "Ban Điều Phối"
                            elif "PLANNER" in role_name or "THOUGHT" in role_name:
                                display_role = "Ban Kế Hoạch"
                            elif "EXECUTOR" in role_name or "ALPHA" in role_name or "BETA" in role_name:
                                display_role = "Ban Thực Thi"
                            elif "SUMMARIZER" in role_name:
                                display_role = "Ban Thư Ký"
                            elif "CRITIC" in role_name or "AUDIT" in role_name or "REVIEW" in role_name:
                                display_role = "Ban Kiểm Soát"
                            elif "DATA_SCOUT" in role_name or "RESEARCH" in role_name or "SEARCH" in role_name or "LATENCY" in role_name or "PERFORMANCE" in role_name or "METRICS" in role_name or "SIEUTIMKIEM" in role_name or "TIMKIEM" in role_name:
                                display_role = "Ban Hành Chính"
                            elif "SYSTEM" in role_name or "SYS_LOG" in role_name or "NEURAL" in role_name:
                                display_role = "Ban Kỹ Thuật"
                            elif "ENGINE" in role_name or "CORE" in role_name:
                                display_role = "Trung tâm Điều hành"
                            elif "MASTER" in role_name or "USER" in role_name:
                                display_role = "Ban Giám Đốc"
                            elif "MISSION_RESULT" in role_name or "RESULT" in role_name:
                                display_role = "Kết quả"
                            
                            # Convert markdown-like structures to beautiful Telegram HTML
                            formatted_msg = escape_html(short_msg)
                            formatted_msg = formatted_msg.replace("*[Đang suy nghĩ]*", "<b>[Đang suy nghĩ]</b>")
                            formatted_msg = formatted_msg.replace("*[Đang suy nghĩ...]*", "<b>[Đang suy nghĩ...]</b>")
                            formatted_msg = formatted_msg.replace("*[Đang trả lời...]*", "<b>[Đang trả lời...]</b>")
                            
                            # Replace Markdown bold **text** with HTML <b>text</b> (100% safe)
                            formatted_msg = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_msg)
                            
                            # Convert blockquote lines to beautiful, sovereign vertical bars (100% safe)
                            formatted_msg = formatted_msg.replace("&gt; ", "┃ ").replace("&gt;", "┃ ")
                            
                            final_text = f"🏢 <b>{display_role}</b>:\n{formatted_msg}"
                        elif tag in ["MASTER", "MASTER_WEB", "MASTER_TELE", "JKAI", "MISSION_RESULT", "DONE", "RESULT", "ERROR", "CRITICAL", "SYSTEM"]:
                            final_text = f"{prefix} <b>{tag}</b>:\n{escape_html(clean_msg)}"
                        else:
                            # Đảm bảo Tên Ban: Nội dung cho các log hành động
                            final_text = f"🏢 <b>{action_label}</b>: {escape_html(short_msg)}"

                        if tag == "ZENITH": 
                            final_text = f"💎 <b>[ZENITH]</b>:\n{escape_html(clean_msg)}"
                        elif tag == "WARN": 
                            final_text = f"⚠️ <b>[CẢNH BÁO]</b>:\n{escape_html(clean_msg)}"
                        elif tag in ["AUTH", "SECURITY"]: 
                            final_text = f"🔐 <b>[BẢO MẬT]</b>:\n{escape_html(clean_msg)}"

                        # 🔄 IN-PLACE MESSAGE EDIT!
                        if is_pin and pin_id in pin_map:
                            try:
                                bot.edit_message_text(
                                    chat_id=MASTER_ID,
                                    message_id=pin_map[pin_id],
                                    text=final_text,
                                    parse_mode="HTML",
                                    reply_markup=markup
                                )
                                continue
                            except Exception as edit_err:
                                if "message is not modified" in str(edit_err).lower():
                                    continue
                                # Fallback to sending a new message if the message was deleted
                                pass

                        if is_pin:
                            msg_obj = safe_send_message(MASTER_ID, final_text, parse_mode="HTML", reply_markup=markup)
                            if msg_obj:
                                pin_map[pin_id] = msg_obj.message_id
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
    help_text = (
        "🏛️ <b>BỘ TƯ LỆNH JKAI ZENITH</b>\n\n"
        "<b>🔹 NHÓM LỆNH VẬN HÀNH (HỆ THỐNG)</b>\n"
        "• <code>/status</code> - 📊 Kiểm tra sức khỏe của các lõi AI.\n"
        "• <code>/sync</code> - 🔄 Kích hoạt tiến trình đồng hóa tri thức.\n"
        "• <code>/reset</code> (hoặc <code>/clear</code>) - 🧹 Xóa bộ nhớ ngữ cảnh hiện tại để bắt đầu task mới.\n"
        "• <code>/insights</code> - 💡 Trích xuất top 10 tư duy chiến lược gần nhất từ Vỏ não.\n\n"
        "<b>🔹 NHÓM LỆNH HÀNH ĐỘNG (SKILLS)</b>\n"
        "• <code>/search_skill [từ khóa]</code> - 🔍 Tra cứu các kỹ năng (VD: <i>/search_skill docker</i>).\n"
        "• <code>/run_skill [#ID]</code> - 🚀 Chạy cưỡng bức một kỹ năng (VD: <i>/run_skill #09</i>).\n\n"
        "<b>🔹 NHÓM LỆNH ỨNG CỨU VÀ CẢI TIẾN</b>\n"
        "• <code>/tusualoi</code> - 🛡️ Đặc quyền toàn hệ thống để tìm và tự động vá lỗi.\n"
        "• <code>/tucaitien</code> - 🧬 Kích hoạt lõi tiến hóa, tự viết lại mã nguồn để tối ưu hóa.\n"
        "• <code>/cancel</code> (hoặc <code>/stop</code>) - 🛑 Ngắt mạch khẩn cấp mọi tiến trình AI.\n\n"
        "💡 <b>MẸO:</b>\n"
        "- Thêm <code>[DEEP]</code> ở đầu câu để ép AI suy nghĩ sâu.\n"
        "- Gửi Voice hoặc Ảnh để gọi Giao thức Nhãn thần/Thính giác.\n"
        "- Gõ <code>/help_secret</code> để xem danh sách Lệnh Đặc Quyền của Tổng Giám Đốc."
    )
    safe_send_message(MASTER_ID, help_text, parse_mode="HTML")

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
        mode = "fast"
        if base_goal.upper().startswith("[DEEP]"):
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
            except: pass
            
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
        mode = "fast"
        if goal.upper().startswith("[DEEP]"):
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
        except: pass
        # Chuyển về Brain xử lý xác thực ngầm
        execute_neural_command(text)
        return

    mode = "fast"
    if text.upper().startswith("[DEEP]"):
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
