import hashlib

class IdempotencyLayer:
    """
    🛡️ Idempotency Layer (Chống Double-Execute)
    """
    def __init__(self, redis_conn):
        self.redis = redis_conn

    def generate_key(self, trace_id: str, tool_name: str, args: dict) -> str:
        """Tạo khóa độc nhất cho một hành động cụ thể."""
        args_str = str(sorted(args.items()))
        raw = f"{trace_id}:{tool_name}:{args_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def check_and_lock(self, idempotency_key: str, timeout: int = 3600) -> bool:
        """
        Kiểm tra xem khóa đã tồn tại chưa. Nếu chưa thì khóa lại.
        Trả về True nếu chưa từng thực thi (được phép chạy).
        Trả về False nếu đã thực thi rồi (cần bị chặn).
        """
        # redis.setnx trả về True nếu set thành công (chưa tồn tại)
        success = self.redis.setnx(f"idem:{idempotency_key}", "locked")
        if success:
            self.redis.expire(f"idem:{idempotency_key}", timeout)
        return bool(success)
        
    def mark_completed(self, idempotency_key: str):
        self.redis.set(f"idem:{idempotency_key}", "completed")
