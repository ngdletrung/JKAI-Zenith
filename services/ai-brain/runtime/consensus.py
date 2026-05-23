class ConsensusLayer:
    """
    🤝 Tầng Đồng Thuận (Leader Election & Locks)
    Đảm bảo khi chạy multi-node, 2 runtime không cùng cướp 1 Trace.
    """
    def __init__(self, redis_conn):
        self.redis = redis_conn

    def acquire_execution_lock(self, trace_id: str, runtime_id: str, ttl: int = 60) -> bool:
        """Giành quyền sở hữu Execution cho Trace."""
        lock_key = f"lock:trace:{trace_id}"
        return bool(self.redis.set(lock_key, runtime_id, nx=True, ex=ttl))
        
    def release_execution_lock(self, trace_id: str, runtime_id: str):
        lock_key = f"lock:trace:{trace_id}"
        current_owner = self.redis.get(lock_key)
        if current_owner == runtime_id:
            self.redis.delete(lock_key)
