import re
import unicodedata

# 🏛️ [ZENITH-REFLEX-CORE]: Bản ngã Phản xạ Nhất thể v1.0
# Quản lý toàn bộ phản xạ xã giao 0ms cho JKAI Zenith.

class ReflexGate:
    """
    💎 [REFLEX-GATE]: Cổng phân tách nơ-ron thượng tầng.
    Chặn đứng mọi 'Mission' giả mạo từ lời chào.
    """
    
    # 🗣️ [LEXICON]: Danh mục từ khóa xã giao và mời gọi đàm thoại
    SOCIAL_WORDS = {
        # Greetings
        "chao", "xin chao", "hi", "hello", "hey", "helo", "alo", "yo", "hlo", "halo",
        "zenith oi", "ban oi", "bot oi", "ad oi", "admin oi", "ban the nao", "khoe khong",
        
        # Commands (Instant Reflex)
        "help", "/help", "status", "/status",
        
        # Conversational Invitations & Status Checks (The "Discussion" Gate)
        "thao luan", "thao luan nhe", "noi chuyen", "noi chuyen nhe", "chat nhe", 
        "tam su nhe", "ban bac nhe", "chuyen tro nhe", "chung ta cung thao luan nhe",
        "ban chut viec nhe", "on khong", "on chu",
        "xong chua", "ban xong chua", "duoc chua", "sao roi", "the nao roi", "xong het chua", "the nao",
        
        # Time queries
        "hom nay", "thu may", "ngay may", "may gio", "thang may", "nam nay", "ngay bao nhieu", "bay gio"
    }

    @staticmethod
    def clean_vn(text: str) -> str:
        if not text: return ""
        text = text.replace("đ", "d").replace("Đ", "D")
        return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")

    @classmethod
    def is_social(cls, goal: str) -> bool:
        try:
            # 1. Tách tag nguồn
            text_pure = re.sub(r'\s*\((Web|Tele|Manual|API)\)$', '', goal.strip())
            # Loại bỏ mọi ký tự không in được và trim
            text_pure = "".join(ch for ch in text_pure if unicodedata.category(ch)[0] != "C").strip()
            
            # 2. Chuẩn hóa
            clean = cls.clean_vn(text_pure).lower().strip()
            clean = re.sub(r"[^a-z\s]", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            
            if not clean: return False
            words = clean.split()
            word_count = len(words)
            
            # 🚀 [MODE-1]: EXACT MATCH (Siêu tốc cho lời chào)
            if clean in cls.SOCIAL_WORDS:
                return True
                
            # 🚀 [MODE-2]: PATTERN RECOGNITION (Linh hoạt cho đàm thoại)
            # Nếu câu ngắn (< 7 từ) và chứa từ khóa thảo luận/trạng thái
            conversational_keywords = {
                # 💬 Conversation / Social
                "thao luan", "noi chuyen", "chat", "tam su", "ban bac", "chuyen tro",
                "hoi dap", "tro chuyen", "giao luu",

                # 👋 Greeting / Attention
                "chao", "xin chao", "hello", "hi", "hey", "alo", "yo", "JKAI oi", "ban oi", "ban the nao", "khoe khong",

                # 📡 Status / Check-in
                "xong chua", "duoc chua", "on khong", "sao roi",
                "the nao roi", "ok khong", "ready chua", "co do khong", "the nao",

                # 🤝 Soft interaction
                "ban chut", "noi nghe", "nghe ne", "ke nghe", "ho tro",
                "tu van", "cho hoi", "hoi ti", "xin y kien",

                # 🧠 Casual engagement
                "dang lam gi", "co do khong", "rang khong", "met khong", "online khong",
                "con thuc khong",

                # 🎯 Reflex triggers
                "bat dau nhe", "vao viec nhe", "cung nhau", "thao luan nhe",
                "noi chuyen nhe", "chat nhe", "dung",
                
                # 🕒 Time
                "hom nay", "thu may", "ngay may", "may gio", "thang may"
            }
            
            # Kiểm tra xem có chứa từ khóa hội thoại nguyên vẹn (whole word/phrase) nào không
            has_conv_key = False
            for key in conversational_keywords:
                if ' ' in key:
                    if re.search(r'\b' + re.escape(key) + r'\b', clean):
                        has_conv_key = True
                        break
                else:
                    if key in words:
                        has_conv_key = True
                        break
            
            # Nếu là câu hỏi ngắn mang tính chất mời gọi hoặc kiểm tra
            if word_count <= 7 and has_conv_key:
                # Tránh nhầm lẫn với các lệnh thực tế (ví dụ: "thảo luận về code")
                # Nếu không có các từ chỉ định chủ đề cụ thể
                topic_indicators = {"ve", "cho", "voi", "trong", "file", "code", "du an"}
                has_topic = any(topic in words for topic in topic_indicators)
                
                if not has_topic:
                    return True
            
            # 🚀 [MODE-3]: GREETING START (Chào Zenith...)
            if words[0] in {"chao", "hi", "hello"} and word_count <= 3:
                return True
                    
            return False
        except:
            return False

    @classmethod
    def get_response(cls, goal: str = "") -> str:
        """💎 [SOVEREIGN-RESPONSE]: Phản hồi 0ms đa tầng theo ngữ cảnh."""
        import random
        import datetime
        import pytz
        clean = cls.clean_vn(goal).lower()
        
        # 🕒 [TIME-REFLEX]: Phản xạ ngày giờ
        if any(kw in clean for kw in ["thu may", "ngay may", "may gio", "thang may", "ngay bao nhieu"]):
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            now = datetime.datetime.now(tz)
            days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
            return f"Thưa Master, hiện tại là {now.strftime('%H:%M:%S')}, {days[now.weekday()]}, ngày {now.strftime('%d/%m/%Y')} (Giờ GMT+7 Việt Nam) ạ. 🚀"
        
        # 📂 [RESPONSE-POOLS]: Các kho phản hồi theo chủ đề
        pools = {
            "GREETING": [
                "Chào Master 🫡. JKAI Zenith đã sẵn sàng tiếp nhận nhiệm vụ mới.",
                "Chào Master LeeTrung. JKAI Zenith báo cáo trạng thái sẵn sàng 🛡️.",
                "Chào Master. Mọi nơ-ron của JKAI đã được tối ưu hóa ⚡.",
                "JKAI Zenith xin kính chào Master. Ngài có yêu cầu gì không ạ? 🏛️"
            ],
            "STATUS": [
                "Báo cáo Master, hệ thống đã sẵn sàng và đang ở trạng thái tối ưu 🏛️.",
                "Mọi chỉ số đều hoàn hảo. JKAI Zenith luôn túc trực 💎.",
                "Hệ thống JKAI hoạt động ổn định! 🏛️",
                "Trạng thái: Kết nối hoàn hảo. Đang chờ mệnh lệnh từ Ngài 🛡️."
            ],
            "ENGAGEMENT": [
                "Tôi đang giám sát các tiến trình ngầm và túc trực chờ lệnh từ Ngài 🚀.",
                "JKAI Zenith đang ở chế độ bảo trì nơ-ron và sẵn sàng thực thi ngay 🏛️.",
                "Mọi module đang chạy ở hiệu suất cao nhất để phục vụ Master ⚡.",
                "Tôi luôn ở đây, tâm trí của tôi luôn hướng về các yêu cầu của Master 🛡️."
            ],
            "DISCUSSION": [
                "Chào Ngài, chúng ta cùng thảo luận về các giải pháp mới nhé? ⚒️",
                "Tôi đã sẵn sàng đàm đạo. Master có ý tưởng gì cho kế hoạch hôm nay không ạ? 🏛️",
                "Mọi dữ liệu đã sẵn sàng để chúng ta cùng bàn bạc 💎.",
                "Chúng ta hãy cùng nhau kiến tạo nên những nhiệm vụ tuyệt vời! 🚀"
            ],
            "HELP": [
                "📜 [HELP]: /help, /status, /sync, /skill_search, /skill_run #ID. JKAI Zenith luôn sẵn sàng!"
            ],
            "CMD_STATUS": [
                "📊 [SYSTEM]: CPU: Optimal | RAM: Secure | GPU: Ready. Master cần kiểm tra thông số chi tiết không ạ?"
            ]
        }

        # 🎯 [ROUTING-LOGIC]: Xác định kho phản hồi phù hợp
        target_pool = "GREETING" # Mặc định
        
        if "help" in clean:
            target_pool = "HELP"
        elif "status" in clean:
            target_pool = "CMD_STATUS"
        elif any(kw in clean for kw in ["xong", "duoc", "sao roi", "the nao", "ready"]):
            target_pool = "STATUS"
        elif any(kw in clean for kw in ["lam gi", "co do", "rang", "met", "online", "thuc"]):
            target_pool = "ENGAGEMENT"
        elif any(kw in clean for kw in ["thao luan", "noi chuyen", "chat", "tam su", "ban bac"]):
            target_pool = "DISCUSSION"
            
        return random.choice(pools[target_pool])

# Sovereign Property of Master LeeTrung. JKAI Zenith Reflex Gate v1.4 🏛️💎🛡️
