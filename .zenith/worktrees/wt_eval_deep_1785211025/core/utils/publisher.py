import json
import time
from core.redis_client import redis_safe

class Publisher:
    """
    📡 [PUBLISHER]: Giao thức truyền tin nơ-ron.
    Đảm bảo mọi thông điệp từ AI Brain được phát tới Dashboard thời gian thực.
    """
    def publish(self, tag: str, msg: str, task_id: str = "system"):
        """Phát tin qua Redis Pub/Sub."""
        try:
            payload = json.dumps({
                "tag": tag,
                "msg": msg,
                "ts": time.time(),
                "task_id": task_id
            }, ensure_ascii=False)
            
            def _redis_op(r):
                # 1. Lưu vào lịch sử
                r.lpush("monitor:log_history", payload)
                r.ltrim("monitor:log_history", 0, 499)
                # 2. Phát trực tiếp qua kênh nơ-ron
                r.publish("monitor:log_channel", payload)
            
            redis_safe(_redis_op)
        except Exception as e:
            # Giao thức im lặng: Không gây sập hệ thống
            print(f"❌ [PUBLISHER-ERR]: {e}")

# Singleton
publisher = Publisher()
