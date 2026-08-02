# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/rollback_manager.py
# - Role: Saga Pattern Compensating Actions Manager
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v20.0

import asyncio
import os
import logging

logger = logging.getLogger("RollbackManager")

class RollbackManager:
    """
    Chien luoc Dao nguoc (Saga Pattern Compensating Actions)
    Khi he thong rot vao ROLLED_BACK, thuc thi cac hanh dong bu tru thuc te (compensations)
    de bao ve tinh toan ven cua file system va memory state.
    """
    def __init__(self, sandbox=None):
        self.sandbox = sandbox
        self.compensations = {} # Luu tru cac ham bu tru dong dang ky theo trace_id

    def register_compensation(self, trace_id: str, action_name: str, compensation_func, *args, **kwargs):
        """Dang ky dong mot hanh dong bu tru cho mot buoc cu the trong Trace."""
        if trace_id not in self.compensations:
            self.compensations[trace_id] = []
        self.compensations[trace_id].append((action_name, compensation_func, args, kwargs))

    async def execute_compensation_async(self, trace_id: str, original_action: str, target_resource: str = None):
        """Kich hoat va cho hoan tat cac hanh dong bu tru thuc te."""
        logger.info(f"[ROLLBACK-MANAGER] Executing compensating actions for trace {trace_id}, action '{original_action}'")
        
        # 1. Thuc thi cac ham bu tru dong duoc dang ky (LIFO)
        if trace_id in self.compensations:
            registered = self.compensations[trace_id]
            for action_name, func, args, kwargs in reversed(registered):
                try:
                    logger.info(f"[ROLLBACK-EXEC] Running registered compensation for {action_name}")
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[ROLLBACK-EXEC-ERR] Failed compensation for {action_name}: {e}")
            del self.compensations[trace_id]

        # 2. Thuc thi cac quy tac den bu tinh thuc te cho Sandbox & Filesystem
        if original_action in ["write_file", "create_file", "patch_file"] and target_resource:
            try:
                if os.path.exists(target_resource):
                    backup_path = f"{target_resource}.bak"
                    if os.path.exists(backup_path):
                        os.replace(backup_path, target_resource)
                        logger.info(f"[ROLLBACK-CLEANUP] Restored file from backup: {target_resource}")
                    elif original_action == "create_file":
                        os.remove(target_resource)
                        logger.info(f"[ROLLBACK-CLEANUP] Removed created file on rollback: {target_resource}")
            except Exception as f_err:
                logger.error(f"[ROLLBACK-FILE-ERR] {f_err}")
                
        elif original_action == "db_transaction":
            try:
                from core.utils.engine import engine
                r = engine._get_redis()
                if r and trace_id:
                    r.delete(f"state:{trace_id}")
                    logger.info(f"[ROLLBACK-REDIS] Purged uncommitted state for {trace_id}")
            except Exception as r_err:
                logger.error(f"[ROLLBACK-REDIS-ERR] {r_err}")

    def execute_compensation(self, trace_id: str, original_action: str, target_resource: str = None):
        """Kich hoat linh hoat async hoac sync."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.execute_compensation_async(trace_id, original_action, target_resource))
        except RuntimeError:
            asyncio.run(self.execute_compensation_async(trace_id, original_action, target_resource))
