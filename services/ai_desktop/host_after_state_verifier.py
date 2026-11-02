# -*- coding: utf-8 -*-
"""
services/ai_desktop/host_after_state_verifier.py
[JKAI INDEPENDENT AFTER-STATE VERIFIER]

Reads the target window buffer directly from Win32 after a mutation and compares it
against the expected state. It never trusts the value the actuator claims to have
sent, so a failed write can never be reported as DELIVERED_VERIFIED.
scripts/host_after_state_verifier.py re-exports this module for compatibility.
"""

import hashlib
import json
import sys
import time
from typing import Any, Dict, Tuple


class HostAfterStateVerifier:
    """
    Independent After-State Verifier.
    Độc lập với Actuator và Worker, chỉ đọc trạng thái để thẩm định kết quả.
    """

    def __init__(self):
        self._is_windows = sys.platform == "win32"
        self._user32 = None
        if self._is_windows:
            try:
                import ctypes
                self._user32 = ctypes.windll.user32
            except Exception:
                self._user32 = None

    TEXT_CONTROL_CLASSES = ("edit", "richeditd2dpt", "richedit50w")

    def _find_text_control(self, hwnd: int) -> int:
        """Resolve the text control (Notepad Edit/RichEditD2DPT, WordPad RICHEDIT50W)."""
        import ctypes
        from ctypes import wintypes

        result = []

        def _class_name(handle) -> str:
            buffer = ctypes.create_unicode_buffer(256)
            self._user32.GetClassNameW(handle, buffer, len(buffer))
            return buffer.value.lower()

        def _visit(child, _):
            if _class_name(child) in self.TEXT_CONTROL_CLASSES:
                result.append(child)
            return True

        if _class_name(hwnd) in self.TEXT_CONTROL_CLASSES:
            return hwnd
        for class_name in ("Edit", "RichEditD2DPT", "RICHEDIT50W"):
            child = self._user32.FindWindowExW(hwnd, 0, class_name, None)
            if child:
                return child

        enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_visit)
        ctypes.windll.user32.EnumChildWindows(wintypes.HWND(hwnd), enum_proc, 0)
        return result[0] if result else 0

    def read_notepad_buffer(self, hwnd: int) -> Tuple[bool, str]:
        """
        Đọc nội dung văn bản hiện tại từ text control của cửa sổ đích.
        Hỗ trợ Notepad (Edit/RichEditD2DPT) và WordPad (RICHEDIT50W).
        """
        if not self._is_windows or not self._user32:
            return False, "NON_WINDOWS_OR_NO_USER32"

        try:
            import ctypes
            target_hwnd = self._find_text_control(hwnd) or hwnd

            WM_GETTEXTLENGTH = 0x000E
            WM_GETTEXT = 0x000D

            length = self._user32.SendMessageW(target_hwnd, WM_GETTEXTLENGTH, 0, 0)
            if length < 0:
                return False, "GETTEXTLENGTH_FAILED"

            buffer = ctypes.create_unicode_buffer(length + 2)
            self._user32.SendMessageW(target_hwnd, WM_GETTEXT, length + 1, ctypes.byref(buffer))
            return True, buffer.value
        except Exception as e:
            return False, f"READ_ERROR: {e}"

    def capture_snapshot(self, hwnd: int, proc_name: str = "notepad.exe") -> Dict[str, Any]:
        """Chụp snapshot trạng thái hiện tại của target window."""
        now = time.time()
        success, text = self.read_notepad_buffer(hwnd)

        text_val = text if success else ""
        content_hash = hashlib.sha256(text_val.encode("utf-8")).hexdigest()

        return {
            "timestamp": now,
            "hwnd": hwnd,
            "proc_name": proc_name,
            "read_success": success,
            "text": text_val,
            "hash": content_hash,
            "error": None if success else text,
        }

    def verify_action_result(
        self,
        before_snapshot: Dict[str, Any],
        hwnd: int,
        expected_mutation_text: str,
        proc_name: str = "notepad.exe",
        timeout_seconds: float = 2.0,
        match_mode: str = "append"
    ) -> Dict[str, Any]:
        """
        So sánh trạng thái trước và sau khi thực thi hành động để thẩm định kết quả độc lập.
        match_mode="append": after == before + expected (gõ thêm ký tự).
        match_mode="exact":  after == expected (ghi đè toàn bộ nội dung).
        """
        if match_mode not in ("append", "exact"):
            raise ValueError(f"UNSUPPORTED_MATCH_MODE: {match_mode!r}")

        deadline = time.time() + timeout_seconds
        last_snapshot = None
        match_found = False
        before_text = before_snapshot.get("text", "")

        while time.time() <= deadline:
            last_snapshot = self.capture_snapshot(hwnd, proc_name=proc_name)
            if match_mode == "exact":
                expected_after = expected_mutation_text
            else:
                expected_after = before_text + expected_mutation_text
            if last_snapshot.get("read_success", False) and last_snapshot.get("text", "") == expected_after:
                match_found = True
                break
            time.sleep(0.05)

        after_text = last_snapshot.get("text", "") if last_snapshot else ""
        status = "VERIFIED_MATCH" if match_found else "STATE_MISMATCH"

        receipt = {
            "status": status,
            "timestamp": time.time(),
            "target_hwnd": hwnd,
            "proc_name": proc_name,
            "before_hash": before_snapshot.get("hash", ""),
            "after_hash": last_snapshot.get("hash", "") if last_snapshot else "",
            "expected_text_sha256": hashlib.sha256(expected_mutation_text.encode("utf-8")).hexdigest(),
            "before_length": len(before_text),
            "after_length": len(after_text),
            "read_success": bool(last_snapshot and last_snapshot.get("read_success", False)),
            "match": match_found,
            "match_mode": match_mode,
        }

        receipt_bytes = json.dumps(receipt, sort_keys=True).encode("utf-8")
        receipt["receipt_digest"] = hashlib.sha256(receipt_bytes).hexdigest()
        return receipt
