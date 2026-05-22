import os
import json
import time
import asyncio
from .redis_client import redis_safe

class SovereignGuard:
    """
    🏛️ JKAI ZENITH: VỆ BINH CHỦ QUYỀN (SOVEREIGN GUARD v1.5)
    Giao thức Chuẩn hóa Nhất thể: Nguồn sự thật duy nhất cho mọi tiến trình dừng và thỉnh lệnh.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")

    def _log(self, tag: str, msg: str, task_id: str = "system"):
        """Phát tín hiệu chuẩn hóa."""
        try:
            log_payload = json.dumps({
                "tag": tag, 
                "msg": msg, 
                "ts": time.time(),
                "task_id": task_id
            }, ensure_ascii=False)
            redis_safe(lambda r: r.publish("monitor:log_channel", log_payload))
        except: pass

    async def ensure_approval(self, task_id: str, action_desc: str, is_core: bool = False, req_type: str = None) -> bool:
        """
        🛡️ GIAO THỨC PHÊ DUYỆT NHẤT THỂ:
        Dừng mọi tiến trình và đợi lệnh từ Master.
        """
        if not task_id or task_id == "unknown":
            return False

        proposal_id = f"hitl_{task_id}_{int(time.time()*1000)}"
        approval_key = f"hitl_approve:{proposal_id}"
        
        # 📜 1. ĐỊNH NGHĨA LOẠI PHÊ DUYỆT CHUẨN HÓA
        if not req_type:
            final_type = "AUTH_REQUIRED" if is_core else "APPROVE_REQUIRED"
        else:
            final_type = req_type
            
        try:
            payload = {
                "task_id": task_id,
                "proposal_id": proposal_id,
                "service": self.service_name,
                "message": f"⚖️ [{self.service_name.upper()}]: Master có phê duyệt hành động: `{action_desc}` không ạ?",
                "is_core": is_core,
                "type": final_type,
                "ts": time.time()
            }
            
            # Đẩy vào hàng chờ hiển thị trên Dashboard và phát sóng PubSub 0ms thưa Master
            redis_safe(lambda r: r.hset("hitl_pending", proposal_id, json.dumps(payload, ensure_ascii=False)))
            redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_created", "payload": payload}, ensure_ascii=False)))
            
            status_msg = f"⚠️ [{final_type}]: Đang đợi Master phê chuẩn hành động tại {self.service_name}..."
            if is_core or "AUTH" in final_type:
                status_msg = f"🚨 [CORE-AUTH]: Hành động can thiệp HẠT NHÂN. Master vui lòng nhập MẬT MÃ CHỦ QUYỀN!"
            
            self._log("SECURITY", status_msg, task_id)

            # ⏳ 2. VÒNG LẶP CHỜ ĐỢI NHẤT THỂ
            start_wait = time.time()
            timeout = 1800 # 30 phút chuẩn hóa
            
            while time.time() - start_wait < timeout:
                
                if redis_safe(lambda r: r.get(approval_key) == b'true', False):
                    redis_safe(lambda r: (r.delete(approval_key), r.hdel("hitl_pending", proposal_id)))
                    redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_resolved", "proposal_id": proposal_id})))
                    self._log("SECURITY", f"✅ [APPROVED]: Ý chỉ của Master đã được tiếp nhận. Tiếp tục thực thi...", task_id)
                    return True
                
                await asyncio.sleep(2)
            
            self._log("SECURITY", "⏰ [TIMEOUT]: Đã quá thời gian chờ phê duyệt. Hành động bị hủy.", task_id)
            redis_safe(lambda r: r.hdel("hitl_pending", proposal_id))
            redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_resolved", "proposal_id": proposal_id})))
            return False

        except Exception as e:
            self._log("ERROR", f"❌ [GUARD-ERR]: Sự cố tại Vệ binh: {str(e)}", task_id)
            return False

# 💎 Khởi tạo Vệ binh mặc định
guard = SovereignGuard("Zenith Core")
