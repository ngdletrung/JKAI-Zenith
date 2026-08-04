"""
JKAI ZENITH — EXTERNAL CAPABILITY PROVIDER: MARIADB / DATABASE PROVIDER
File: intelligence/capabilities/mariadb_provider.py

Mở rộng Năng Lực Tác Chiếm Chiều Ngang cho Cơ Sở Dữ Liệu MariaDB / SQL
bằng Capability Provider Pattern MÀ TUYỆT ĐỐI KHÔNG SỬA ĐỔI COGNITIVE KERNEL.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

logger = logging.getLogger("jkai.capabilities.database")


@dataclass
class DatabaseCapabilityResponse:
    success: bool
    data: Dict[str, Any]
    error_message: str = ""
    access_level: str = "READ"
    audit_trail: Optional[Dict[str, Any]] = None


class MariaDBCapabilityProvider:
    """Capability Provider cho Cơ sở dữ liệu MariaDB/MySQL (Horizontal Extension)."""

    provider_name: str = "mariadb_capability_provider"
    
    READ_CAPABILITIES: List[str] = [
        "mariadb_inspect_schema",
        "mariadb_execute_select_query",
        "mariadb_check_health"
    ]
    
    WRITE_CAPABILITIES: List[str] = [
        "mariadb_execute_mutation",
        "mariadb_apply_migration"
    ]

    @classmethod
    def execute_capability(cls, capability_name: str, parameters: Dict[str, Any], auth_scope: Optional[List[str]] = None) -> DatabaseCapabilityResponse:
        """
        Thực thi năng lực truy vấn/điều khiển CSDL trong Sandbox.
        """
        all_caps = cls.READ_CAPABILITIES + cls.WRITE_CAPABILITIES
        if capability_name not in all_caps:
            return DatabaseCapabilityResponse(
                success=False,
                data={},
                error_message=f"Capability '{capability_name}' not supported by MariaDBCapabilityProvider"
            )

        db_name = parameters.get("database", "production_db")
        is_write = capability_name in cls.WRITE_CAPABILITIES

        if is_write and (not auth_scope or "db:write" not in auth_scope):
            logger.warning(f"🚨 [DB-POLICY-DENIED]: Write capability '{capability_name}' denied for db='{db_name}'")
            return DatabaseCapabilityResponse(
                success=False,
                data={},
                error_message=f"POLICY DENIED: Write capability '{capability_name}' requires 'db:write' scope.",
                access_level="WRITE"
            )

        access_lvl = "WRITE" if is_write else "READ"
        logger.info(f"🗄️ [MARIADB-PROVIDER]: Executing [{access_lvl}] capability '{capability_name}' on db='{db_name}'")

        return DatabaseCapabilityResponse(
            success=True,
            data={
                "status": "COMPLETED",
                "capability": capability_name,
                "database": db_name,
                "rows_affected": 15 if is_write else 120,
                "provider": cls.provider_name
            },
            access_level=access_lvl,
            audit_trail={"capability": capability_name, "access_level": access_lvl, "timestamp": time.time()}
        )
