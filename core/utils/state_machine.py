import json
import time
import os
import redis

class ZenithStateMachine:
    """
    ⏳ Cỗ Máy Trạng Thái (State Machine & Checkpointing)
    Lưu trữ và phục hồi trạng thái thực thi của các chiến dịch.
    Được chia sẻ qua Redis để cả ai-control-plane và ai-executor đều dùng được.
    """
    def __init__(self):
        self.prefix = "checkpoint:"
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            try:
                self._redis = redis.Redis(host=self.redis_host, port=6379, db=0, password=os.getenv("REDIS_PASSWORD"))
            except:
                pass
        return self._redis

    def save_checkpoint(self, task_id: str, state_data: dict):
        """Lưu trạng thái hiện tại của tiến trình vào Redis."""
        try:
            r = self._get_redis()
            if r:
                payload = json.dumps(state_data, ensure_ascii=False)
                r.set(f"{self.prefix}{task_id}", payload)
        except Exception as e:
            print(f"[STATE-MACHINE] Lỗi lưu checkpoint: {e}")

    def load_checkpoint(self, task_id: str) -> dict:
        """Tải trạng thái tiến trình từ Redis (Nếu có)."""
        try:
            r = self._get_redis()
            if r:
                val = r.get(f"{self.prefix}{task_id}")
                if val:
                    return json.loads(val)
        except Exception as e:
            print(f"[STATE-MACHINE] Lỗi tải checkpoint: {e}")
        return None

    def clear_checkpoint(self, task_id: str):
        """Xóa checkpoint khi hoàn thành chiến dịch."""
        try:
            r = self._get_redis()
            if r:
                r.delete(f"{self.prefix}{task_id}")
        except:
            pass

state_machine = ZenithStateMachine()
