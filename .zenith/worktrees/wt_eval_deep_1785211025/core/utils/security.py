import os
import json
import logging
from typing import List

logger = logging.getLogger('SECURITY')

class SecurityEngine:
    """
    🛡️ JKAI ZENITH: SECURITY ENGINE
    Kiểm soát truy cập Vùng Đỏ (RED ZONE) và Lệnh Hạt nhân.
    """
    def __init__(self):
        self.nuclear_tools = ["self-destruct", "supreme_shutdown", "docker_wipe"]
        self._red_zones: List[str] = []
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        base_path = os.environ.get('INTELLIGENCE_DIR', '')
        if not base_path:
            from core.config import settings
            base_path = settings.INTELLIGENCE_DIR
        # Load from AEGIS GUARD manifest
        manifest_path = os.path.join(base_path, 'skills', 'CORE', 'ZENITH_AEGIS_GUARD', 'manifest.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    self._red_zones = manifest.get('red_zone_paths', [])
            except Exception as e:
                logger.warning(f"[SECURITY] Khong the load red zone paths: {e}")
        if not self._red_zones:
            self._red_zones = [".env", "config/", "node_modules/", "core/auth/", "intelligence/protocols/"]
        self._loaded = True

    def add_red_zone(self, path_pattern: str):
        self._ensure_loaded()
        if path_pattern not in self._red_zones:
            self._red_zones.append(path_pattern)

    def is_red_zone(self, target_path: str) -> bool:
        self._ensure_loaded()
        for zone in self._red_zones:
            if zone in target_path:
                return True
        return False

    def is_nuclear_tool(self, tool_name: str) -> bool:
        return any(nt in tool_name.lower() for nt in self.nuclear_tools)

security_engine = SecurityEngine()
