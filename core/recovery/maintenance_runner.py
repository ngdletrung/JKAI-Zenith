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
    """Điểm duy nhất được cấp phép yêu cầu Kernel cấp Maintenance Grant."""

    @classmethod
    def authorize_maintenance_task(cls, task_name: str, target_file: str) -> Dict[str, Any]:
        """Xin grant và kiểm tra thẩm quyền cho một thao tác bảo trì.

        Hàm này chỉ thẩm quyền, không thực thi file — nơi gọi phải tự thực hiện
        sau khi được cho phép, để log không báo "đang chạy" khi chưa chạy gì.
        """
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
            logger.info("🛠️ [MAINTENANCE-AUTHORISED]: '%s' on %s với grant hợp lệ.", task_name, target_file)
            return {"authorized": True, "token_verified": True, "task": task_name}

        logger.warning("❌ [MAINTENANCE-REJECTED]: %s", check_res.get("reason"))
        return {"authorized": False, "token_verified": False, "reason": check_res.get("reason")}
