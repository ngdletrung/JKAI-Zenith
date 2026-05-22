import os
import json
import time as _time
import asyncio
from core.utils.engine import engine
from core.utils.redis_client import redis_safe

class HITLManager:
    """
    🛡️ BỘ LỌC AN TOÀN TỐI CAO (Nuclear Key Protocol)
    Đảm bảo JKAI không bao giờ vượt quyền Master LeeTrung.
    """
    def __init__(self, redis_client):
        self.redis = redis_client

    def _publish_log(self, tag, msg, task_id="manual"):
        """[LOG-BRIDGE]: Chuyển tiếp tới Engine tối cao."""
        return engine.publish_mission_log(tag, msg, task_id)

    async def check_nuclear_permission(self, command_type: str, user_input: str) -> bool:
        """🛡️ [SOVEREIGN-VERIFICATION]: Xác thực Mật mã Tối thượng."""
        try:
            from main import sovereign
            return sovereign.verify_key(user_input.strip())
        except Exception as e:
            self._publish_log("ERROR", f"❌ [AUTH-SYSTEM-FAILURE]: {str(e)}")
            return False

    async def _handle_nuclear_key(self, task_id, review):
        await self.request_approval(task_id, review.get("feedback", "Yêu cầu Nuclear Key."), "CODE")
        self._publish_log("STEWARD", "⚠️ [SECURITY ALERT] Rủi ro cao. Vui lòng nhập Mật mã Hạt nhân để phê duyệt tối cao.", task_id)
        
        start_wait = _time.time()
        while _time.time() - start_wait < 3600:
            user_input = redis_safe(lambda r: r.get(f"hitl_approve_code:{task_id}"), None)
            if user_input:
                user_code = user_input.decode() if isinstance(user_input, bytes) else user_input
                if await self.check_nuclear_permission("CODE_CHANGE", user_code):
                    self._publish_log("SYSTEM", "✅ [AUTHENTICATED]: Mật mã chính xác. Khởi động thực thi...", task_id)
                    redis_safe(lambda r: r.delete(f"hitl_approve_code:{task_id}"))
                    redis_safe(lambda r: r.set(f"hitl_approve:{task_id}", "true", ex=60))
                    return
                else:
                    self._publish_log("ERROR", "❌ [DENIED]: Mật mã không trùng khớp. Master vui lòng nhập lại hoặc Hủy bỏ.", task_id)
                    redis_safe(lambda r: r.delete(f"hitl_approve_code:{task_id}"))
            
            if redis_safe(lambda r: r.get(f"hitl_approve:{task_id}") == b'true', False):
                 redis_safe(lambda r: r.delete(f"hitl_approve:{task_id}"))
                 return

            await asyncio.sleep(2)
        raise Exception("Yêu cầu bị từ chối hoặc hết hạn.")

    async def request_approval(self, task_id: str, message: str, type: str):
        """Gửi yêu cầu phê duyệt lên Dashboard cho Master."""
        payload = {
            "task_id": task_id,
            "message": message,
            "type": type,
            "ts": _time.time()
        }
        if self.redis:
            await self.redis.hset("hitl_pending", task_id, json.dumps(payload))
            print(f"🔍 [HITL] Approval requested for task {task_id}")
        else:
            print(f"⚠️ [HITL-ERR] Redis client is missing during approval request for {task_id}")
