import os
import re
import logging
from pathlib import Path

# 🛰️ JKAI ZENITH: PATH MANAGER (SOVEREIGN COORDINATES) v1.0
# Nhiệm vụ: Thông dịch rule_paths.md thành tọa độ thực thi.

logger = logging.getLogger("jkai.core.path_manager")

class PathManager:
    def __init__(self):
        self.paths = {}
        self.last_sync = 0
        # Tọa độ gốc
        self.workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.protocol_path = os.path.join(self.workspace_root, "intelligence", "path_rules.md")
        self._sync()

    def _sync(self):
        """Đồng bộ hóa với rule_paths.md."""
        if not os.path.exists(self.protocol_path):
            return

        mtime = os.path.getmtime(self.protocol_path)
        if mtime <= self.last_sync:
            return

        try:
            with open(self.protocol_path, "r", encoding="utf-8") as f:
                content = f.read()

            matches = re.findall(r"\|\s*\*\*([A-Z0-9_]+)\*\*\s*\|\s*`([^`]+)`\s*\|", content)
            
            new_paths = {}
            normalized_root = self.workspace_root.lower().replace("\\", "/")
            legacy_root = "d:/docker/jkai"

            for var, path in matches:
                input_path_norm = path.lower().replace("\\", "/")
                
                if input_path_norm.startswith(normalized_root):
                    suffix = input_path_norm[len(normalized_root):]
                    final_path = self.workspace_root + suffix
                elif input_path_norm.startswith(legacy_root):
                    suffix = input_path_norm[len(legacy_root):]
                    final_path = self.workspace_root + suffix
                else:
                    final_path = os.path.join(self.workspace_root, path)
                
                new_paths[var] = os.path.normpath(final_path)
            
            self.paths = new_paths
            self.last_sync = mtime
            logger.debug(f"✅ [PATH-SYNC]: Updated {len(self.paths)} coordinates.")
        except Exception as e:
            logger.error(f"❌ [PATH-SYNC-ERR]: {e}")

    def get(self, variable_name: str, default: str = None) -> str:
        """Truy xuất tọa độ."""
        self._sync()
        return self.paths.get(variable_name, default)

# 🚀 Singleton
_instance = PathManager()

def get(variable_name: str, default: str = None) -> str:
    return _instance.get(variable_name, default)

def get_root() -> str:
    return _instance.workspace_root
