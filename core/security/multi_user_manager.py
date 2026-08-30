# -*- coding: utf-8 -*-
"""
👥 [MULTI-USER SOVEREIGNTY & FEDERATED IDENTITY v1.0]
File: core/security/multi_user_manager.py

Hệ Thống Đa Người Dùng & Cô Lập Bộ Nhớ Liên Bang (Trụ Cột 16):
  1. Multi-User Profile: Hồ sơ cá nhân hóa (Primary Master vs Collaborator vs Guest).
  2. Sandboxed Memory Isolation: Mỗi người dùng sở hữu namespace bộ nhớ và sở thích riêng biệt.
  3. Collaborative Session Grant: Master có quyền cấp phép truy cập phiên làm việc cụ thể.
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger("JKAI.MultiUserManager")


class UserAccessLevel(Enum):
    ROOT_MASTER = "ROOT_MASTER"        # Master tối cao toàn quyền
    COLLABORATOR = "COLLABORATOR"      # Người cộng tác (Quyền đọc/ghi trong dự án)
    GUEST_READER = "GUEST_READER"      # Khách vãng lai (Chỉ đọc)


@dataclass
class UserProfile:
    user_id: str
    display_name: str
    access_level: UserAccessLevel
    memory_namespace: str
    allowed_projects: Set[str] = field(default_factory=set)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class MultiUserSovereigntyManager:
    """
    👥 Động Cơ Điều Hành Danh Tính & Cô Lập Bộ Nhớ Đa Người Dùng
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.users: Dict[str, UserProfile] = {
            "master_root": UserProfile(
                user_id="master_root",
                display_name="Master LeeTrung",
                access_level=UserAccessLevel.ROOT_MASTER,
                memory_namespace="ns_master_root",
                allowed_projects={"*"},
                preferences={"style": "elite", "verbosity": "high"}
            )
        }
        # Bản đồ cấp quyền phiên làm việc (Session Grants): session_id -> Set[user_id]
        self.session_access_grants: Dict[str, Set[str]] = {}

    def register_collaborator(
        self,
        user_id: str,
        display_name: str,
        project_id: str,
        invited_by: str
    ) -> Dict[str, Any]:
        """Master mời và đăng ký người cộng tác mới vào dự án."""
        inviter = self.users.get(invited_by)
        if not inviter or inviter.access_level != UserAccessLevel.ROOT_MASTER:
            return {"success": False, "error": "Chỉ có Root Master mới có quyền mời cộng tác viên."}

        profile = UserProfile(
            user_id=user_id,
            display_name=display_name,
            access_level=UserAccessLevel.COLLABORATOR,
            memory_namespace=f"ns_{user_id}",
            allowed_projects={project_id}
        )
        self.users[user_id] = profile
        logger.info(f"👥 [MULTI-USER]: Master registered collaborator '{display_name}' ({user_id}) for project '{project_id}'.")
        return {
            "success": True,
            "user_id": user_id,
            "display_name": display_name,
            "namespace": profile.memory_namespace
        }

    def verify_user_session_access(self, user_id: str, session_id: str, project_id: str = "default") -> bool:
        """Kiểm tra quyền truy cập vào phiên làm việc."""
        user = self.users.get(user_id)
        if not user:
            return False

        # Root Master luôn có quyền truy cập
        if user.access_level == UserAccessLevel.ROOT_MASTER:
            return True

        # Kiểm tra theo danh sách dự án cho phép
        if "*" in user.allowed_projects or project_id in user.allowed_projects:
            return True

        # Kiểm tra quyền truy cập phiên cụ thể
        granted_users = self.session_access_grants.get(session_id, set())
        return user_id in granted_users


multi_user_manager = MultiUserSovereigntyManager()
