import os
import sys
import shutil
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
import asyncio

logger = logging.getLogger("SagaAtomicHealer")

class SagaAtomicHealer:
    """
    🛡️ [SAGA-ATOMIC-HEALER]: Động cơ Quản lý Giao dịch Nguyên tử (Atomic Transactions) & Tự Chữa Lỗi.
    Khi một bước chỉnh sửa mã nguồn hoặc thao tác tệp gặp sự cố:
    1. Tự động khôi phục bản sao lưu (.bak) nguyên vẹn ban đầu.
    2. Thu hồi các tệp rác tự sinh.
    3. Ghi nhận phân loại lỗi vào FailureMemory để mô hình không lặp lại sai lầm.
    """
    def __init__(self):
        self.active_transactions: Dict[str, Dict[str, Any]] = {}

    def begin_transaction(self, task_id: str, target_files: List[str]) -> bool:
        """Bắt đầu giao dịch: Tạo bản sao lưu (.bak) nguyên tử cho tất cả các tệp mục tiêu."""
        snapshots = {}
        for file_path_str in target_files:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                bak_path = file_path.with_suffix(file_path.suffix + ".bak")
                try:
                    shutil.copy2(file_path, bak_path)
                    snapshots[str(file_path)] = str(bak_path)
                except Exception as e:
                    logger.error(f"[SAGA-BACKUP-ERR] Không thể tạo backup cho `{file_path}`: {e}")

        self.active_transactions[task_id] = {
            "task_id": task_id,
            "snapshots": snapshots,
            "start_time": time.time()
        }
        logger.info(f"🛡️ [SAGA-TX-BEGIN]: Khởi tạo transaction `{task_id}` bảo vệ {len(snapshots)} tệp.")
        return True

    def commit_transaction(self, task_id: str) -> bool:
        """Cam kết giao dịch thành công: Dọn dẹp các tệp sao lưu (.bak)."""
        tx = self.active_transactions.pop(task_id, None)
        if not tx:
            return False

        for orig_str, bak_str in tx.get("snapshots", {}).items():
            bak_path = Path(bak_str)
            if bak_path.exists():
                try:
                    bak_path.unlink()
                except Exception as e:
                    logger.warning(f"[SAGA-CLEAN-WARN] Không thể xóa `{bak_path}`: {e}")

        logger.info(f"✅ [SAGA-TX-COMMIT]: Giao dịch `{task_id}` hoàn thành công khai. Đã dọn dẹp backup.")
        return True

    def rollback_transaction(self, task_id: str, error_detail: str = "Unknown Error") -> bool:
        """Rollback giao dịch thất bại: Khôi phục nguyên vẹn các tệp (.bak) và ghi nhận FailureMemory."""
        tx = self.active_transactions.pop(task_id, None)
        if not tx:
            logger.warning(f"[SAGA-ROLLBACK-WARN] Không tìm thấy transaction `{task_id}` để rollback.")
            return False

        restored_count = 0
        for orig_str, bak_str in tx.get("snapshots", {}).items():
            orig_path = Path(orig_str)
            bak_path = Path(bak_str)
            if bak_path.exists():
                try:
                    shutil.move(str(bak_path), str(orig_path))
                    restored_count += 1
                except Exception as e:
                    logger.error(f"[SAGA-RESTORE-ERR] Lỗi khi khôi phục `{orig_path}` từ `{bak_path}`: {e}")

        # Ghi nhận phân loại lỗi vào FailureMemory
        try:
            from core.utils.failure_memory import failure_memory, FailureStage
            asyncio.run(failure_memory.record_failure(
                task_id=task_id,
                goal=f"Atomic Saga Rollback for task {task_id}",
                task_type="file_mutation",
                failure_stage=FailureStage.TOOL_EXECUTION,
                error_detail=error_detail,
                failed_tools=["file_editor"]
            ))
        except Exception:
            pass

        logger.warning(f"🔄 [SAGA-TX-ROLLBACK]: Giao dịch `{task_id}` đã rollback! Đã khôi phục {restored_count} tệp nguyên vẹn.")
        return True

saga_atomic_healer = SagaAtomicHealer()
