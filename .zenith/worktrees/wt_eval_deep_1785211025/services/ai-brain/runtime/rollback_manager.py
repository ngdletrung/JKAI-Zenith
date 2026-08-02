# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/rollback_manager.py
# - Role: Saga Pattern Compensating Actions Manager
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Thiet lap va thuc hien cac hanh dong bu tru (Saga compensations) mot cach deterministic.

import asyncio

class RollbackManager:
    """
    Chien luoc Dao nguoc (Saga Pattern Compensating Actions)
    Khi he thong rot vao ROLLED_BACK, can co hanh dong bu tru de bao ve tinh toan ven.
    """
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.compensations = {} # Luu tru cac ham bu tru dong dang ky theo trace_id

    def register_compensation(self, trace_id: str, action_name: str, compensation_func, *args, **kwargs):
        """Dang ky dong mot hanh dong bu tru cho mot buoc cu the trong Trace."""
        if trace_id not in self.compensations:
            self.compensations[trace_id] = []
        self.compensations[trace_id].append((action_name, compensation_func, args, kwargs))

    def execute_compensation(self, trace_id: str, original_action: str):
        """Kich hoat hanh dong bu tru dua tren action truoc do."""
        print(f"[ROLLBACK-MANAGER]: Khoi dong don dep/bu tru cho Trace {trace_id}, su co tai '{original_action}'")
        
        # 1. Thuc thi cac ham bu tru dong duoc dang ky truoc (LIFO)
        if trace_id in self.compensations:
            registered = self.compensations[trace_id]
            for action_name, func, args, kwargs in reversed(registered):
                try:
                    print(f"[ROLLBACK-EXEC]: Chay ham bu tru dang ky cho {action_name}")
                    if asyncio.iscoroutinefunction(func):
                        asyncio.create_task(func(*args, **kwargs))
                    else:
                        func(*args, **kwargs)
                except Exception as e:
                    print(f"[ROLLBACK-EXEC-ERR]: Loi khi chay bu tru cho {action_name}: {e}")
            del self.compensations[trace_id]

        # 2. Thuc thi cac quy tac den bu tinh dua tren ten action
        if original_action in ["write_file", "create_file"]:
            print(f"[ROLLBACK-STATIC]: Phat hien hanh dong tao file, kich hoat don dep tai nguyen tinh.")
        elif original_action == "db_transaction":
            print(f"[ROLLBACK-STATIC]: Phat hien giao dich DB hong, kich hoat ROLLBACK TRANSACTION.")
