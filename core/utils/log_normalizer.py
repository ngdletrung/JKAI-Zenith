# -*- coding: utf-8 -*-
"""
🧹 LOG NORMALIZER
Chuẩn hóa nội dung log truyền phát qua Mission Log, Thoughts và Telemetry.
"""

from __future__ import annotations

import re
from typing import Optional


def normalize_mission_log(tag: str, msg: str) -> Optional[str]:
    """
    Chuẩn hóa nội dung message trước khi phát tán lên Redis/WebSocket.
    Lọc bỏ các thông điệp rỗng hoặc format không hợp lệ.
    """
    if not msg or not isinstance(msg, str):
        return None
    
    clean_msg = msg.strip()
    if not clean_msg:
        return None
        
    return clean_msg


def format_thought(role: str, thought: str) -> str:
    """
    Định dạng luồng tư duy (thought stream) trước khi hiển thị cho Master.
    """
    if not thought:
        return ""
    return str(thought).strip()


def normalize_role_tag(role: str) -> str:
    """
    Chuẩn hóa tên vai trò (Role Tag).
    """
    return str(role).upper().strip() if role else "SYSTEM"
