import re
import json
import hashlib
from core.utils.engine import engine

class AuthInterceptor:
    """
    🛡️ TẬP ĐOÀN JKAI ZENITH - LỚP ĐÁNH CHẶN VÀ XÁC THỰC
    """
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn
        self.SOVEREIGN_HASH = "0e94b3de1477fd760e485cf448efbbe3471497d807861eed47ae8295c2f446a2"

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    def _clean_vn_accents(self, s: str) -> str:
        patterns = {
            '[àáảãạăằắẳẵặâầấẩẫậ]': 'a',
            '[èéẻẽẹêềếểễệ]': 'e',
            '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
            '[ùúủũụưừứửữự]': 'u',
            '[ỳýỷỹỵ]': 'y',
            '[đ]': 'd'
        }
        res = s.lower()
        for pattern, replacement in patterns.items():
            res = re.sub(pattern, replacement, res)
        return res

    async def is_social_input(self, goal: str) -> bool:
        """💎 FUZZY SOCIAL SENSING"""
        clean_goal = self._clean_vn_accents(goal)
        clean_goal = re.sub(r'\(.*?\)|[^a-z0-9\s]', '', clean_goal)
        clean_goal = clean_goal.lower().strip()
        
        if len(clean_goal) < 15 and not re.search(r'(lap|chay|sua|xoa|tim|quet|tong hop|ke hoach|chien luoc)', clean_goal):
            return True
            
        social_pattern = r'^(chao|hi|hello|helo|hlo|halo|hey|he|alo|he lo|he lo|e|oi|dang lam|la ai|giup|ten gi)'
        if re.search(social_pattern, clean_goal):
            return True
        return False

    async def preflight_validation(self, goal: str, task_id: str) -> dict:
        """🛡️ PRE-FLIGHT VALIDATION GATE"""
        if not goal or not goal.strip():
            return {"valid": False, "reason": "Yêu cầu rỗng thưa Master. Ngài cần chỉ thị cụ thể để tôi hành động thưa Ngài! 🫡"}

        if re.search(r'[\x00-\x1F\x7F]', goal):
            return {"valid": False, "reason": "Phát hiện ký tự điều khiển bất thường trong yêu cầu thưa Master. Hệ thống đã ngăn chặn để đảm bảo an toàn thưa Ngài! 🛡️"}

        destructive_keywords = r'(xóa|delete|remove|destroy|format|clean|purge)\s+(tất cả|all|mọi|toàn bộ|cả)'
        if re.search(destructive_keywords, goal.lower()) and len(goal) < 30:
            return {"valid": False, "reason": "Yêu cầu có tính hủy diệt cao và quá ngắn thưa Master. Ngài vui lòng chỉ rõ đối tượng để tôi thực thi chính xác thưa Ngài! ⚖️"}

        words = goal.strip().split()
        if len(words) <= 2 and not await self.is_social_input(goal) and not goal.startswith("/"):
            return {"valid": False, "reason": f"Yêu cầu '{goal}' dường như thiếu thông tin thực thi thưa Master. Ngài có thể chỉ thị rõ hơn để tôi phục vụ tốt nhất không ạ? 🫡"}

        return {"valid": True}

    async def check_sovereign_intercept(self, clean_goal: str, task_id: str):
        """Kiểm tra Mật mã Chủ quyền hoặc Xác nhận Đa Kênh"""
        input_hash = hashlib.sha256(clean_goal.encode()).hexdigest()
        
        # 1. Sovereign Hash Intercept
        if input_hash == self.SOVEREIGN_HASH:
            try:
                pending = self.redis_conn.hgetall("hitl_pending")
                if pending:
                    latest_proposal_id = None
                    latest_ts = 0
                    for pid, data_raw in pending.items():
                        try:
                            p_data = json.loads(data_raw)
                            if ("AUTH" in p_data.get("type", "") or p_data.get("is_core")) and p_data.get("ts", 0) > latest_ts:
                                latest_ts = p_data.get("ts", 0)
                                latest_proposal_id = pid
                        except: continue
                    
                    if latest_proposal_id:
                        self.redis_conn.set(f"hitl_approve:{latest_proposal_id}", "true", ex=300)
                        msg = "🔐 [CEO-AUTH-SUCCESS]: Mật mã Chủ quyền chính xác. Đã cấp quyền thực thi vùng lõi và XÓA DẤU VẾT bảo mật thưa Tổng Giám Đốc! 🛡️💎"
                        self._log("AUTH", msg, task_id, stealth=True)
                        return {"answer": msg, "task_id": task_id, "sensitive": True, "stealth": True}
            except Exception as e:
                self._log("SYSTEM", f"⚠️ [AUTH-ERR]: Lỗi xác thực bảo mật: {str(e)}", task_id)

        # 2. Sovereign Approval Intercept (Multi-channel)
        if clean_goal.lower() in ["ok", "duyệt", "approve", "chấp thuận", "đã duyệt"]:
            try:
                pending = self.redis_conn.hgetall("hitl_pending")
                if pending:
                    latest_proposal_id = None
                    latest_ts = 0
                    p_type = "hành động"
                    
                    for pid, data_raw in pending.items():
                        try:
                            p_data = json.loads(data_raw)
                            if p_data.get("ts", 0) > latest_ts:
                                latest_ts = p_data.get("ts", 0)
                                latest_proposal_id = pid
                                p_type = p_data.get("type", "HÀNH ĐỘNG")
                        except: continue
                    
                    if latest_proposal_id:
                        self.redis_conn.set(f"hitl_approve:{latest_proposal_id}", "true", ex=300)
                        msg = f"🚀 [SOVEREIGN-APPROVED]: Tổng Giám Đốc đã phê chuẩn `{p_type}`. Các Ban đang đồng loạt xuất quân thưa Ngài! ⚔️🛡️"
                        self._log("ZENITH", msg, task_id)
                        return {"answer": msg, "task_id": task_id, "sensitive": True}
                    else:
                        return {"answer": "❓ [ZENITH]: Thưa Master, hiện con không thấy đề xuất nào đang chờ phê duyệt ạ.", "task_id": task_id, "sensitive": False}
            except Exception as e:
                self._log("SYSTEM", f"⚠️ [APPROVAL-ERR]: Lỗi xử lý phê duyệt đa kênh: {str(e)}", task_id)
        
        return None
