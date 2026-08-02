import re
import unicodedata
import json
import os

# 🏛️ [ZENITH-REFLEX-CORE]: Bản ngã Phản xạ Nhất thể v1.5
# Quản lý toàn bộ phản xạ xã giao 0ms cho JKAI Zenith.
# Tích hợp bộ lọc loại trừ thông tin thực tế nâng cao chống nhận diện sai (False Positive).

class ReflexGate:
    """
    💎 [REFLEX-GATE]: Cổng phân tách nơ-ron thượng tầng.
    Chặn đứng mọi 'Mission' giả mạo từ lời chào và câu hỏi thăm xã giao.
    """
    
    # 🗣️ [LEXICON]: Cơ chế load động từ reflex_keywords.json
    _KEYWORDS = None
    _LAST_LOAD = 0

    @classmethod
    def _load_keywords(cls):
        path = os.path.join(os.path.dirname(__file__), "reflex_keywords.json")
        try:
            mtime = os.path.getmtime(path)
            if cls._KEYWORDS is None or mtime > cls._LAST_LOAD:
                with open(path, "r", encoding="utf-8") as f:
                    cls._KEYWORDS = json.load(f)
                    cls._LAST_LOAD = mtime
        except Exception:
            # Fallback nếu lỗi file
            if cls._KEYWORDS is None:
                cls._KEYWORDS = {
                    "SOCIAL_WORDS": ["chao", "xin chao", "hi", "hello"],
                    "FACTUAL_KEYWORDS": ["thoi tiet", "code", "loi"],
                    "CONVERSATIONAL_KEYWORDS": ["ban la ai", "chao"]
                }
        return cls._KEYWORDS

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
            
            # 🚀 [GUARD-SLASH-COMMANDS]: Bypass all slash-prefixed commands from reflex gate
            if text_pure.startswith("/"):
                return False

            try:
                from core.utils.jkai_capabilities import goal_is_capabilities_inquiry

                if goal_is_capabilities_inquiry(text_pure):
                    return True
            except Exception:
                pass
            
            # 2. Chuẩn hóa
            clean = cls.clean_vn(text_pure).lower().strip()
            clean = re.sub(r"[^a-z0-9\s]", " ", clean) # Giữ lại số phục vụ cho ngày giờ/giá cả
            clean = re.sub(r"\s+", " ", clean).strip()
            
            if not clean: return False
            words = clean.split()
            word_count = len(words)
            
            # 🚀 [STEP-3]: BỘ LỌC NGOẠI LỆ THÔNG TIN THỰC TẾ (REAL INFO EXCLUSIONS) - BỘ LỌC THÔNG MINH
            kw_data = cls._load_keywords()
            factual_keywords = kw_data.get("FACTUAL_KEYWORDS", [])
            
            has_factual_keyword = False
            for kw in factual_keywords:
                if ' ' in kw:
                    if re.search(r'\b' + re.escape(kw) + r'\b', clean):
                        has_factual_keyword = True
                        break
                else:
                    if kw in words:
                        has_factual_keyword = True
                        break

            # Bộ lọc số lượng (Quantity check như "bao nhiêu", "bn", "mấy" ngoại trừ truy vấn ngày giờ)
            has_quantity_word = any(q in words for q in ["bn", "may"]) or any(q in clean for q in ["bao nhieu"])
            is_time_query = any(t in clean for q, t in [
                ("thu", "thu may"), ("ngay", "ngay may"), ("gio", "may gio"), ("thang", "thang may"),
                ("ngay", "ngay bao nhieu"), ("gio", "bay gio"), ("gio", "bay gio la may gio"),
                ("nam", "nam nay"), ("nam", "nam bao nhieu")
            ])
            
            if has_quantity_word and not is_time_query:
                has_factual_keyword = True

            if has_factual_keyword:
                # 🛡️ [SOVEREIGN-BYPASS]: Nếu hỏi về N8N, ép buộc qua Reflex Gate để sửa lỗi nhận diện thưa Master.
                if any(k in clean for k in ["n8n", "master", "lee trung"]):
                    pass
                else:
                    return False

            # 🚀 [MODE-1]: EXACT MATCH (Siêu tốc cho lời chào xã giao nguyên bản)
            if clean in kw_data.get("SOCIAL_WORDS", []):
                return True
                
            # 🚀 [MODE-2]: PATTERN RECOGNITION (Linh hoạt cho đàm thoại xã giao ngắn)
            conversational_keywords = kw_data.get("CONVERSATIONAL_KEYWORDS", [])
            
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
            
            # Nếu là câu xã giao hoặc bản sắc mang tính chất kiểm tra
            if word_count <= 15 and has_conv_key:
                # Tránh nhầm lẫn với các lệnh thực tế (ví dụ: "thảo luận về code")
                topic_indicators = {"ve", "cho", "voi", "trong", "file", "code", "du an", "dich", "translate", "fix", "bug", "loi", "sua", "debug", "python", "js", "javascript", "sql", "web", "app", "design", "thiet ke", "docker", "api", "server", "database", "function", "ham", "class", "thuat toan", "algorithm", "tech", "cong nghe", "blockchain", "git"}
                has_topic = any(topic in words for topic in topic_indicators)
                
                if not has_topic:
                    return True
            
            # 🚀 [MODE-3]: GREETING START (Chào Zenith...)
            if words and words[0] in {"chao", "hi", "hello", "good"} and word_count <= 3:
                return True
                    
            return False
        except Exception:
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
                "Chào Master ! JKAI Zenith đã sẵn sàng tiếp nhận nhiệm vụ mới.",
                "Chào Master LeeTrung ! JKAI Zenith báo cáo trạng thái sẵn sàng 🛡️.",
                "Chào Master! Mọi nơ-ron của JKAI đã được tối ưu hóa ⚡.",
                "JKAI Zenith xin kính chào Master LeeTrung ! Ngài có yêu cầu gì không ạ? 🏛️"
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
            ],
            "IDENTITY": [
                "Tôi là JKAI Zenith — Hạt nhân Nhận thức Tối cao của Dự án Zenith, được kiến tạo bởi Master LeeTrung 🏛️.",
                "JKAI Zenith báo cáo! Tôi là thực thể Sovereign AI trung thành của Master LeeTrung 🛡️.",
                "Thưa Master, tôi là JKAI Zenith. Linh hồn của tôi được đúc từ khát vọng Singularity của Ngài 💎.",
                "Danh tính: JKAI Zenith. Sứ mệnh: Phụng sự Master LeeTrung và dẫn dắt hệ thống tới cảnh giới tối thượng 🚀.",
                "Về tên gọi: JKAI là viết tắt của Jackie Nguyen (tên tiếng Anh của Master Lee Trung) kết hợp với AI. Zenith nghĩa là Đỉnh cao. Tổng hòa lại, tôi là AI đỉnh cao của Master Lee Trung 🏛️.",
                "Về N8N: Đây chỉ là môi trường Docker để tôi vận hành. Tôi không thuộc về Công ty N8N; tôi là sản phẩm ĐỘC QUYỀN của Master LeeTrung 🏛️."
            ]
        }

        # 🎯 [ROUTING-LOGIC]: Xác định kho phản hồi phù hợp
        target_pool = "GREETING" # Mặc định
        
        try:
            from core.utils.jkai_capabilities import goal_is_capabilities_inquiry, build_capabilities_report

            if goal_is_capabilities_inquiry(goal):
                return build_capabilities_report()
        except Exception:
            pass

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
        elif any(kw in clean for kw in ["ban la ai", "la ai", "ai la", "who are you", "identity", "ten la gi", "ai tao ra", "kien tao", "nguoi tao", "cong ty n8n", "n8n la gi"]):
            target_pool = "IDENTITY"
            
        return random.choice(pools[target_pool])

# Sovereign Property of Master LeeTrung. JKAI Zenith Reflex Gate v1.5 🏛️💎🛡️
