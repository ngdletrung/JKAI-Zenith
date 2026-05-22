import time
from typing import Optional
from redis_client import redis_safe

class ClaimManager:
    """
    🤝 [CLAIM-MANAGER]: Quản lý quyền sở hữu tác vụ.
    Đảm bảo tính nhất quán trong Swarm đa đặc vụ (Alpha/Beta).
    """
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds

    def claim_task(self, task_id: str, step_id: str, agent_id: str) -> bool:
        """Thử chiếm quyền thực thi một bước."""
        lock_key = f"claim:{task_id}:{step_id}"
        
        def _attempt_claim(r):
            # NX = Only set if NOT exists
            success = r.set(lock_key, agent_id, ex=self.ttl, nx=True)
            return bool(success)
        
        return redis_safe(_attempt_claim) or False

    def release_task(self, task_id: str, step_id: str, agent_id: str):
        """Giải phóng nơ-ron tác vụ."""
        lock_key = f"claim:{task_id}:{step_id}"
        
        def _release(r):
            current_owner = r.get(lock_key)
            if current_owner == agent_id:
                r.delete(lock_key)
        
        redis_safe(_release)

    def get_owner(self, task_id: str, step_id: str) -> Optional[str]:
        """Kiểm tra ai đang sở hữu nơ-ron này."""
        lock_key = f"claim:{task_id}:{step_id}"
        return redis_safe(lambda r: r.get(lock_key))

# Singleton
claim_manager = ClaimManager()
