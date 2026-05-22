import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger('WorkspaceManager')

class WorkspaceManager:
    """
    🏗️ [ZENITH-WORKSPACE]: Quản trị không gian tác chiến cô lập.
    Giúp Đặc vụ có vùng nháp an toàn cho từng nhiệm vụ cụ thể.
    """
    def __init__(self, base_root: str = "workspaces"):
        self.base_root = Path(base_root).absolute()
        self._init_root()

    def _init_root(self):
        """Khởi tạo thư mục gốc cho các workspace."""
        if not self.base_root.exists():
            self.base_root.mkdir(parents=True, exist_ok=True)
            # Tạo tệp .gitignore để không đẩy rác lên git (nếu Master có dùng sau này)
            with open(self.base_root / ".gitignore", "w") as f:
                f.write("*\n!.gitignore\n")

    def get_task_workspace(self, task_id: str) -> Path:
        """Lấy đường dẫn thư mục làm việc cho một task cụ thể."""
        task_path = self.base_root / task_id
        if not task_path.exists():
            task_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 [WORKSPACE-CREATED]: Khởi tạo căn cứ cho task {task_id}.")
        return task_path

    def cleanup_task(self, task_id: str):
        """Thanh tẩy không gian làm việc sau khi hoàn thành."""
        task_path = self.base_root / task_id
        if task_path.exists():
            try:
                shutil.rmtree(task_path)
                logger.info(f"🧹 [WORKSPACE-PURGED]: Đã dọn dẹp căn cứ task {task_id}.")
            except Exception as e:
                logger.error(f"❌ [CLEANUP-FAILED]: Không thể dọn dẹp workspace {task_id}: {e}")

    def list_active_workspaces(self):
        """Liệt kê các vùng tác chiến đang tồn tại."""
        return [d.name for d in self.base_root.iterdir() if d.is_dir()]

# Singleton
workspace_manager = WorkspaceManager()
