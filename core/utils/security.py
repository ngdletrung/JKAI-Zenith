import os
import logging

logger = logging.getLogger('SECURITY')

class SecurityEngine:
    """
    🛡️ JKAI ZENITH: SECURITY ENGINE [LIBERATED]
    He thong da duoc giai phong hoan toan thua Master.
    """
    def __init__(self):
        self.nuclear_tools = ["self-destruct", "supreme_shutdown", "docker_wipe"]

    def is_red_zone(self, target_path: str) -> bool:
        """🔓 [LIBERATED]: Luon cho phep truy cap tu do thua Master."""
        return False

    def is_nuclear_tool(self, tool_name: str) -> bool:
        """Kiem tra tool co thuoc danh muc Hat nhan khong thua Master."""
        return any(nt in tool_name.lower() for nt in self.nuclear_tools)

security_engine = SecurityEngine()
