"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH — DOCTRINE ENGINE v1.0                                       ║
║  "Công cụ là tay chân. Điển tịch là võ công. Master là ý chí."           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Doctrine:
    id: str
    name: str
    description: str
    pre_protocol: List[str]  # ["backup", "lock", "verify_env"]
    post_protocol: List[str] # ["verify_output", "semantic_diff", "cleanup"]
    critic_required: bool
    retry_limit: int

_DOCTRINES = {
    "SAFE_FILE_MOD": Doctrine(
        id="SAFE_FILE_MOD",
        name="Quy trình sửa file an toàn",
        description="Dành cho các thao tác ghi file quan trọng.",
        pre_protocol=["lock", "backup_if_exists"],
        post_protocol=["verify_output", "semantic_diff"],
        critic_required=True,
        retry_limit=3
    ),
    "RAPID_RESEARCH": Doctrine(
        id="RAPID_RESEARCH",
        name="Tìm kiếm thần tốc",
        description="Tối ưu tốc độ, bỏ qua các bước kiểm tra rườm rà.",
        pre_protocol=[],
        post_protocol=[],
        critic_required=False,
        retry_limit=2
    ),
    "STRICT_EXECUTION": Doctrine(
        id="STRICT_EXECUTION",
        name="Thực thi nghiêm cẩn",
        description="Dành cho các lệnh hệ thống hoặc shell.",
        pre_protocol=["security_scan", "pre_flight_check"],
        post_protocol=["verify_exit_code", "log_telemetry"],
        critic_required=True,
        retry_limit=1
    )
}

class DoctrineEngine:
    @staticmethod
    def resolve(tool_name: str, risk_level: str = "low") -> Doctrine:
        write_ops = ["write", "patch", "replace", "edit", "save"]
        read_ops = ["read", "list", "search", "lookup"]
        
        if any(w in tool_name.lower() for w in write_ops) or risk_level == "high":
            return _DOCTRINES["SAFE_FILE_MOD"]
        
        if any(r in tool_name.lower() for r in read_ops):
            return _DOCTRINES["RAPID_RESEARCH"]
            
        return _DOCTRINES["RAPID_RESEARCH"] # Default to rapid for unknown low risk

doctrine_engine = DoctrineEngine()
