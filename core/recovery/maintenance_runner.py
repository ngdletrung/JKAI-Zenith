# -*- coding: utf-8 -*-
"""
core/recovery/maintenance_runner.py
JKAI — System Maintenance Runner (Tiến Trình Bảo Trì Hệ Thống Duy Nhất Có Thẩm Quyền Nhận Grant)
"""

from __future__ import annotations
import os
import logging
from typing import Optional, Dict, Any

from core.security.negative_list_enforcer import KernelGrantIssuer, NegativeListEnforcer

logger = logging.getLogger("jkai.recovery.maintenance")


class MaintenanceRunner:
    """Tiến trình bảo trì hợp lệ duy nhất được cấp phép nhận Maintenance Grant."""

    @classmethod
    def execute_maintenance_task(cls, task_name: str, target_file: str) -> Dict[str, Any]:
        """Thực thi tác vụ bảo trì (ví dụ nén/xoay vòng file log)."""
        # Cấp token bảo trì hợp lệ 30s từ Kernel
        token = KernelGrantIssuer.issue_maintenance_grant(
            scope="audit_maintenance",
            ttl_seconds=30
        )

        # Kiểm tra thẩm quyền qua NegativeListEnforcer
        check_res = NegativeListEnforcer.check_file_mutation(
            target_path=target_file,
            action="OVERWRITE",
            caller_role="SYSTEM_MAINTENANCE",
            grant_token=token
        )

        if check_res.get("allowed"):
            logger.info("🛠️ [MAINTENANCE-RUNNER]: Executing '%s' on %s with verified grant.", task_name, target_file)
            return {"success": True, "token_verified": True, "task": task_name}
        else:
            logger.warning("❌ [MAINTENANCE-REJECTED]: %s", check_res.get("reason"))
            return {"success": False, "token_verified": False, "reason": check_res.get("reason")}
