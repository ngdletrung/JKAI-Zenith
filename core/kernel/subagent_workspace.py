import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("SubagentWorkspace")

class SubagentWorkspaceManager:
    """
    📂 [SUBAGENT-WORKSPACE-MANAGER]: Quản lý và Cô lập Không gian Làm việc (Workspace Isolation) cho từng Subagent.
    Đảm bảo các Subagent tác chiến trong môi trường thư mục riêng biệt, tránh làm hỏng hoặc ghi đè tệp tin hệ thống.
    """
    def __init__(self, base_workspace_dir: str = None):
        if not base_workspace_dir:
            base_workspace_dir = os.getenv("WORKSPACE_DIR", "D:\\Docker\\JKAI\\brain\\workspaces")
        self.base_dir = Path(base_workspace_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, subagent_id: str) -> Path:
        """Tạo không gian làm việc cô lập cho một Subagent."""
        ws_path = self.base_dir / f"subagent_{subagent_id}"
        ws_path.mkdir(parents=True, exist_ok=True)
        
        # Tạo thư mục con chuẩn
        (ws_path / "artifacts").mkdir(exist_ok=True)
        (ws_path / "scratch").mkdir(exist_ok=True)
        
        logger.info(f"📂 [WORKSPACE-CREATED]: Đã tạo không gian cô lập tại `{ws_path}` cho Subagent `{subagent_id}`")
        return ws_path

    def get_workspace(self, subagent_id: str) -> Path:
        """Lấy đường dẫn không gian làm việc của Subagent."""
        ws_path = self.base_dir / f"subagent_{subagent_id}"
        if not ws_path.exists():
            return self.create_workspace(subagent_id)
        return ws_path

    def cleanup_workspace(self, subagent_id: str) -> bool:
        """Dọn dẹp và thu hồi không gian làm việc khi Subagent hoàn thành hoặc bị hủy."""
        ws_path = self.base_dir / f"subagent_{subagent_id}"
        if ws_path.exists():
            try:
                shutil.rmtree(ws_path)
                logger.info(f"🧹 [WORKSPACE-CLEANED]: Đã thu hồi không gian cô lập của Subagent `{subagent_id}`")
                return True
            except Exception as e:
                logger.error(f"[WORKSPACE-CLEAN-ERR] Không thể xóa `{ws_path}`: {e}")
                return False
        return False

subagent_workspace_manager = SubagentWorkspaceManager()
