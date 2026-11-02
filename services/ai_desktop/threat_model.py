# -*- coding: utf-8 -*-
"""
services/ai_desktop/threat_model.py
[M5-G0 & M5-G4] Threat Model, Process Allowlist, Window Boundary Guard,
Elevated Window Blocker & Desktop Mutation Approval Gate.
Thiết kế theo chuẩn SDS v28.27.0 và OpenCode M5 Gate Specification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple


class DesktopSecurityViolation(Exception):
    """Ngoại lệ khi vi phạm ranh giới an toàn Desktop OS (M5-G0)."""
    pass


def get_desktop_secret_key() -> bytes:
    """Lấy secret key cho Desktop Approval Gate HMAC."""
    key_str = os.getenv("JKAI_DESKTOP_SECRET_KEY", "").strip()
    if key_str:
        return key_str.encode("utf-8")
    is_test_env = (
        os.getenv("JKAI_TEST_MODE", "1").lower() in ("1", "true")
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if is_test_env:
        return b"jkai_desktop_sovereign_approval_gate_2026"
    raise RuntimeError("SECURITY_CRITICAL: JKAI_DESKTOP_SECRET_KEY is missing. Production execution aborted.")


class DesktopSecurityGate:

    @classmethod
    def reset_consumed_tokens(cls) -> None:
        cls._consumed_tokens.clear()
    """
    Cổng phòng vệ an toàn hệ điều hành Desktop Windows (M5-G0 & M5-G4).
    Ngăn chặn tuyệt đối việc AI click nhầm vào các cửa sổ nhạy cảm, elevated UAC,
    hoặc các tiến trình quản trị hệ thống; đồng thời quản lý One-Time Approval Token chống Replay.
    """

    # Danh sách tiến trình cấm tuyệt đối (Blacklist bất khả xâm phạm)
    STRICTLY_DENIED_PROCESSES: Set[str] = {
        "taskmgr.exe",
        "regedit.exe",
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "consent.exe",           # UAC Elevation Prompt
        "credentialuibroker.exe", # Windows Credentials Prompt
        "logonui.exe",            # Windows Logon / Lock Screen
        "services.msc",
        "mmc.exe",
        "gpedit.msc",
        "secpol.msc",
    }

    # Danh sách tiêu đề cửa sổ cấm (Security / Admin Windows)
    DENIED_WINDOW_TITLE_KEYWORDS: List[str] = [
        "user account control",
        "quản trị viên",
        "administrator",
        "registry editor",
        "task manager",
        "windows security",
        "bảo mật windows",
        "lock screen",
    ]

    # Danh mục tiến trình mặc định được phê duyệt (Safe Sandbox Allowlist)
    DEFAULT_ALLOWLIST_PROCESSES: Set[str] = {
        "notepad.exe",
        "calc.exe",
        "calculatorapp.exe",
        "win32calc.exe",
        "mspaint.exe",
        "explorer.exe",
        "chrome.exe",
        "msedge.exe",
    }

    # One-Time Token anti-replay storage
    _consumed_tokens: Set[str] = set()

    @classmethod
    def validate_process_scope(
        cls,
        process_name: str,
        allowlist: Optional[Set[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Kiểm tra danh tính tiến trình mục tiêu.
        Fail-Closed nếu tiến trình nằm trong Blacklist hoặc ngoài Allowlist.
        """
        proc_clean = (process_name or "").strip().lower()
        if not proc_clean:
            return False, "DENY: Tên tiến trình rỗng, vi phạm nguyên tắc định danh an toàn."

        if proc_clean in cls.STRICTLY_DENIED_PROCESSES:
            return False, f"SECURITY_DENIAL: Tiến trình '{proc_clean}' thuộc Blacklist cấm tuyệt đối (M5-G0)."

        active_allowlist = allowlist or cls.DEFAULT_ALLOWLIST_PROCESSES
        if proc_clean not in active_allowlist:
            return False, f"SCOPE_DENIAL: Tiến trình '{proc_clean}' không nằm trong Allowlist được phê duyệt."

        return True, "AUTHORIZED"

    @classmethod
    def validate_window_title(cls, window_title: str) -> Tuple[bool, str]:
        """Kiểm tra tiêu đề cửa sổ, ngăn chặn tương tác trên các hộp thoại quản trị / UAC."""
        title_clean = (window_title or "").strip().lower()
        for kw in cls.DENIED_WINDOW_TITLE_KEYWORDS:
            if kw in title_clean:
                return False, f"SECURITY_DENIAL: Cửa sổ '{window_title}' chứa từ khóa cấm '{kw}' (M5-G0)."
        return True, "AUTHORIZED"

    @classmethod
    def validate_elevation(cls, is_elevated: bool) -> Tuple[bool, str]:
        """
        [CHỐNG ELEVATED EXPLOIT]: Cấm tuyệt đối thao tác trên các cửa sổ đang chạy
        dưới quyền quản trị viên cấp cao (Elevated Administrator).
        """
        if is_elevated:
            return False, "SECURITY_DENIAL: Cửa sổ đang chạy với quyền Administrator (Elevated) bị cấm tuyệt đối (M5-G0)."
        return True, "AUTHORIZED"

    @classmethod
    def validate_coordinates_within_screen(
        cls,
        x: int,
        y: int,
        screen_width: int,
        screen_height: int,
        min_x: int = 0,
        min_y: int = 0,
    ) -> bool:
        """Kiểm tra tọa độ chuột không được bay ra ngoài giới hạn màn hình thực tế."""
        if not (min_x <= x < min_x + screen_width):
            return False
        if not (min_y <= y < min_y + screen_height):
            return False
        return True

    @classmethod
    def validate_coordinates_within_window(
        cls,
        x: int,
        y: int,
        window_rect: Tuple[int, int, int, int],  # (left, top, right, bottom)
    ) -> bool:
        """
        [CHỐNG TRƯỢT TỌA ĐỘ]: Ràng buộc cứng tọa độ thao tác chuột PHẢI nằm gọn
        bên trong hình chữ nhật BoundingBox của cửa sổ đích.
        Nếu chuột trượt ra ngoài cửa sổ ứng dụng -> Hủy lệnh tức thì.
        """
        left, top, right, bottom = window_rect
        if right <= left or bottom <= top:
            return False
        return (left <= x <= right) and (top <= y <= bottom)

    # ── M5-G4: DESKTOP MUTATION APPROVAL TOKEN ENGINE ──

    @classmethod
    def issue_approval_token(
        cls,
        hwnd: int,
        process_name: str,
        target_name: str,
        action: str,
        pid: int = 0,
        execution_mode: str = "visual",
        target_identity: Optional[str] = None,
        expected_postcondition: Optional[str] = None,
        validity_seconds: int = 60,
    ) -> str:
        """
        Cấp thẻ chữ ký số phê duyệt (Signed One-Time Token) cho hành động Mutation Desktop.
        Ràng buộc chặt chẽ HWND, PID, Process Name, Target Name, Action, Mode, Identity và Expected Postcondition.
        """
        secret = get_desktop_secret_key()
        now = int(time.time())
        exp = now + validity_seconds
        import uuid
        payload = {
            "hwnd": hwnd,
            "pid": pid,
            "proc": process_name.lower().strip(),
            "target": target_name.strip(),
            "act": action.lower().strip(),
            "mode": execution_mode.lower().strip(),
            "identity": (target_identity or "").strip(),
            "postcond": (expected_postcondition or "").strip(),
            "iat": now,
            "exp": exp,
            "nonce": uuid.uuid4().hex[:12],
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        raw_token = f"{base64.urlsafe_b64encode(payload_bytes).decode('utf-8')}.{sig}"
        return raw_token

    @classmethod
    def decode_token_payload(cls, token: str) -> Optional[Dict[str, Any]]:
        """Giải mã an toàn payload của token mà không tiêu thụ (dùng để tra cứu expectation)."""
        if not token or "." not in token:
            return None
        payload_b64, _ = token.split(".", 1)
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None

    @classmethod
    def verify_approval_token(
        cls,
        token: str,
        expected_hwnd: int,
        expected_proc: str,
        expected_target: str,
        expected_action: str,
        expected_pid: int = 0,
        expected_mode: str = "visual",
        expected_identity: Optional[str] = None,
        expected_postcondition: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Xác minh chữ ký số, tính toàn vẹn, hạn dùng và chống Replay Attack cho Token.
        """
        if not token or "." not in token:
            return False, "TOKEN_INVALID: Chuỗi token không đúng cấu trúc."

        if token in cls._consumed_tokens:
            return False, "TOKEN_REPLAY_ATTACK: Token này đã được sử dụng một lần trước đó."

        payload_b64, sig = token.split(".", 1)
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return False, "TOKEN_CORRUPTED: Không thể giải mã payload."

        secret = get_desktop_secret_key()
        expected_sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False, "TOKEN_FORGERY: Chữ ký HMAC không hợp lệ."

        now = int(time.time())
        if now > payload.get("exp", 0):
            return False, "TOKEN_EXPIRED: Token phê duyệt đã hết hạn."

        # Ràng buộc chặt chẽ thông số
        if payload.get("hwnd") != expected_hwnd:
            return False, f"TOKEN_BINDING_MISMATCH: HWND {payload.get('hwnd')} != {expected_hwnd}"

        if payload.get("proc") != expected_proc.lower().strip():
            return False, f"TOKEN_BINDING_MISMATCH: Process {payload.get('proc')} != {expected_proc}"

        # [TARGET BINDING ENFORCEMENT]: Khóa chặt tên phần tử mục tiêu
        actual_target = payload.get("target", "")
        if actual_target != expected_target.strip():
            return False, f"TOKEN_BINDING_MISMATCH: Target '{actual_target}' != '{expected_target}'"

        actual_pid = payload.get("pid", 0)
        if expected_pid > 0:
            if not actual_pid or actual_pid != expected_pid:
                return False, f"TOKEN_BINDING_MISMATCH: PID {actual_pid} != {expected_pid}"
        elif actual_pid > 0 and expected_pid == 0:
            return False, f"TOKEN_BINDING_MISMATCH: Token co PID {actual_pid} nhung expected_pid=0"

        if payload.get("act") != expected_action.lower().strip():
            return False, f"TOKEN_BINDING_MISMATCH: Action {payload.get('act')} != {expected_action}"

        # [MODE BINDING ENFORCEMENT]: Khóa chặt chế độ thực thi (Visual vs Background)
        actual_mode = payload.get("mode", "visual").lower().strip()
        expected_mode_clean = (expected_mode or "visual").lower().strip()
        if actual_mode != expected_mode_clean:
            return False, f"TOKEN_BINDING_MISMATCH: Mode '{actual_mode}' != '{expected_mode_clean}'"

        # [TARGET IDENTITY BINDING ENFORCEMENT]
        if expected_identity:
            actual_identity = payload.get("identity", "").strip()
            if actual_identity and actual_identity != expected_identity.strip():
                return False, f"TOKEN_BINDING_MISMATCH: Target Identity '{actual_identity}' != '{expected_identity}'"

        # [POSTCONDITION EXPECTATION BINDING ENFORCEMENT]
        if expected_postcondition:
            actual_postcond = payload.get("postcond", "").strip()
            if actual_postcond and actual_postcond != expected_postcondition.strip():
                return False, f"TOKEN_BINDING_MISMATCH: Expected Postcondition '{actual_postcond}' != '{expected_postcondition}'"

        # Tiêu thụ token (One-Time Token invariant)
        cls._consumed_tokens.add(token)
        return True, "AUTHORIZED"

