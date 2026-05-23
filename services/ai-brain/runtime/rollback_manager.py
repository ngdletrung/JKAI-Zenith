class RollbackManager:
    """
    🔄 Chiến lược Đảo ngược (Saga Pattern Compensating Actions)
    Khi hệ thống rớt vào ROLLED_BACK, cần có hành động bù trừ.
    """
    def __init__(self, sandbox):
        self.sandbox = sandbox
        
    def execute_compensation(self, trace_id: str, original_action: str):
        """Kích hoạt hành động bù trừ dựa trên action trước đó."""
        # Ví dụ: Nếu tạo file -> Xóa file
        # Nếu gửi mail -> Không thể rollback (non-idempotent) -> Chuyển sang Cảnh báo
        pass
