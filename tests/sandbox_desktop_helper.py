# -*- coding: utf-8 -*-
"""In-desktop helper for IsolatedDesktopSandbox live tests.

Windows scopes HWNDs to the desktop that owns them: a thread on the Default
desktop cannot read, post to, or inspect a window created inside another
desktop. The sandbox therefore launches this helper with lpDesktop set to the
isolated desktop, and every Win32/UIA operation runs here.

Usage:
    python -m tests.sandbox_desktop_helper '<json request>'

The helper writes exactly one JSON line to stdout: {"ok": true, ...} or
{"ok": false, "error": "..."}.
"""

import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _resolve_text_control(hwnd: int) -> int:
    """Trả về Edit/RichEdit con nếu hwnd là cửa sổ top-level (Notepad)."""
    import win32gui

    text_classes = ("edit", "richeditd2dpt", "richedit50w")
    if (win32gui.GetClassName(hwnd) or "").lower() in text_classes:
        return hwnd
    for class_name in ("Edit", "RichEditD2DPT", "RICHEDIT50W"):
        child = win32gui.FindWindowEx(hwnd, 0, class_name, None)
        if child:
            return child
    found = []

    def visit(child, _):
        if (win32gui.GetClassName(child) or "").lower() in text_classes:
            found.append(child)
        return True

    win32gui.EnumChildWindows(hwnd, visit, 0)
    return found[0] if found else hwnd


def _read_edit_text(hwnd: int) -> str:
    import ctypes

    user32 = ctypes.windll.user32
    length = user32.SendMessageW(hwnd, 0x000E, 0, 0)
    if length < 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 2)
    user32.SendMessageW(hwnd, 0x000D, length + 1, buf)
    return buf.value


def _window_state(hwnd: int) -> dict:
    import win32gui
    import win32process

    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return {
        "hwnd": int(hwnd),
        "pid": int(pid),
        "is_window": bool(win32gui.IsWindow(hwnd)),
        "title": win32gui.GetWindowText(hwnd),
        "class_name": win32gui.GetClassName(hwnd),
    }


def _op_read_window(req: dict) -> dict:
    return {"window": _window_state(int(req["hwnd"]))}


def _op_send_text(req: dict) -> dict:
    import win32con
    import win32gui

    hwnd = int(req["hwnd"])
    before = _window_state(hwnd)
    ret = win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, 0, str(req["text"]))
    after = _window_state(hwnd)
    return {"ret": int(ret), "before": before, "after": after}


def _op_get_text(req: dict) -> dict:
    hwnd = int(req["hwnd"])
    control = _resolve_text_control(hwnd)
    return {
        "text": _read_edit_text(control),
        "control_hwnd": int(control),
        "window": _window_state(hwnd),
    }


def _op_actuator(req: dict) -> dict:
    from services.ai_desktop import (
        DesktopActRequest,
        DesktopOSActuator,
        DesktopSecurityGate,
        NativeWindowsMouseAdapter,
        NativeWindowInspector,
    )

    if req.get("allow_python"):
        import os

        allowed = {Path(sys.executable).name.lower(), "python.exe"}
        DesktopSecurityGate.DEFAULT_ALLOWLIST_PROCESSES |= allowed
    DesktopSecurityGate.reset_consumed_tokens()

    hwnd = int(req["hwnd"])
    pid = int(req.get("pid") or 0)
    inspector = NativeWindowInspector()
    win_info = inspector.get_window_info(hwnd)

    coords = req.get("target_coords")
    if coords is None:
        rect = win_info.get("rect", (0, 0, 100, 100))
        coords = [(rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2]

    action = str(req.get("action", "click"))
    expected_postcondition = str(req.get("expected_postcondition", "control_state"))
    execution_mode = str(req.get("execution_mode", "background_message"))
    target_name = req.get("target_name")

    token = DesktopSecurityGate.issue_approval_token(
        hwnd=hwnd,
        process_name=win_info["process_name"],
        target_name=target_name or "Custom Coordinate",
        action=action,
        pid=pid,
        execution_mode=execution_mode,
        expected_postcondition=expected_postcondition,
    )
    request = DesktopActRequest(
        action=action,
        target_hwnd=hwnd,
        target_name=target_name,
        target_coords=tuple(coords),
        text=req.get("text"),
        approval_token=token,
        execution_mode=execution_mode,
        expected_postcondition=expected_postcondition,
    )
    actuator = DesktopOSActuator(
        mouse_adapter=NativeWindowsMouseAdapter(),
        window_inspector=inspector,
    )
    result = actuator.execute_action(request)
    return {
        "status": result.status,
        "msg": result.msg,
        "evidence": result.evidence,
        "process_name": win_info.get("process_name"),
        "rect": list(win_info.get("rect", ())),
        "coords": list(coords),
    }


def _op_uia(req: dict) -> dict:
    from services.ai_desktop.uia_tree_inspector import UIATreeInspector

    hwnd = int(req["hwnd"])
    snapshot = UIATreeInspector(is_live_mode=True).inspect_tree(hwnd)
    return {
        "hwnd": int(snapshot.hwnd),
        "engine": snapshot.engine,
        "element_count": int(snapshot.element_count),
        "snapshot_hash": snapshot.snapshot_hash,
        "elements": [
            {
                "ref": element.ref,
                "name": element.name,
                "control_type": element.control_type,
                "automation_id": element.automation_id,
                "class_name": element.class_name,
                "rect": list(element.rect),
                "center": list(element.center),
                "value": element.value,
                "supported_patterns": list(element.supported_patterns),
            }
            for element in snapshot.elements
        ],
    }


def _op_uia_scroll(req: dict) -> dict:
    """Read ScrollPattern state of one allowlisted element (read-only observer)."""
    import comtypes
    import comtypes.client
    from comtypes.gen.UIAutomationClient import (
        CUIAutomation,
        IUIAutomation,
        IUIAutomationScrollPattern,
    )

    PATTERN_SCROLL = 10004
    TREE_SCOPE_DESCENDANTS = 0x4

    hwnd = int(req["hwnd"])
    identifier = str(req.get("identifier", "")).strip().casefold()
    if not identifier:
        raise ValueError("identifier is required")

    comtypes.CoInitialize()
    try:
        uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        root = uia.ElementFromHandle(hwnd)
        descendants = root.FindAll(TREE_SCOPE_DESCENDANTS, uia.CreateTrueCondition())
        matches = []
        for index in range(descendants.Length):
            element = descendants.GetElement(index)
            name = str(element.CurrentName or "")
            automation_id = str(element.CurrentAutomationId or "")
            if identifier in (name.casefold(), automation_id.casefold()):
                matches.append((element, name, automation_id))
        if len(matches) != 1:
            return {
                "found": False,
                "match_count": len(matches),
                "error": "ELEMENT_NOT_FOUND" if not matches else "ELEMENT_AMBIGUOUS",
            }
        element, name, automation_id = matches[0]
        try:
            pointer = element.GetCurrentPattern(PATTERN_SCROLL)
        except Exception:
            pointer = None
        if not pointer:
            return {
                "found": True,
                "name": name,
                "automation_id": automation_id,
                "scroll_supported": False,
            }
        pattern = pointer.QueryInterface(IUIAutomationScrollPattern)
        return {
            "found": True,
            "name": name,
            "automation_id": automation_id,
            "scroll_supported": True,
            "vertical_percent": float(pattern.CurrentVerticalScrollPercent),
            "horizontal_percent": float(pattern.CurrentHorizontalScrollPercent),
            "vertically_scrollable": bool(pattern.CurrentVerticallyScrollable),
            "horizontally_scrollable": bool(pattern.CurrentHorizontallyScrollable),
        }
    finally:
        try:
            comtypes.CoUninitialize()
        except Exception:
            pass


def _op_scroll_info(req: dict) -> dict:
    """Win32 GetScrollInfo(SB_VERT/SB_HORZ) — exact integer scroll positions."""
    import ctypes
    from ctypes import wintypes

    class _SCROLLINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("fMask", wintypes.UINT),
            ("nMin", ctypes.c_int),
            ("nMax", ctypes.c_int),
            ("nPage", wintypes.UINT),
            ("nPos", ctypes.c_int),
            ("nTrackPos", ctypes.c_int),
        ]

    SIF_ALL = 0x17
    SB_VERT, SB_HORZ = 1, 0
    user32 = ctypes.windll.user32

    root = int(req["hwnd"])
    hwnd = int(req.get("control_hwnd") or 0) or _resolve_text_control(root)

    def _read(bar: int) -> dict:
        info = _SCROLLINFO()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = SIF_ALL
        if not user32.GetScrollInfo(hwnd, bar, ctypes.byref(info)):
            return {"available": False}
        return {
            "available": True,
            "min": int(info.nMin),
            "max": int(info.nMax),
            "page": int(info.nPage),
            "pos": int(info.nPos),
            "track_pos": int(info.nTrackPos),
        }

    return {"hwnd": hwnd, "vertical": _read(SB_VERT), "horizontal": _read(SB_HORZ)}


def _op_visual_diff(req: dict) -> dict:
    from services.ai_desktop.visual_engine import VisualWindowCaptureEngine
    from services.ai_desktop.window_message_adapter import WindowMessageAdapter

    hwnd = int(req["hwnd"])
    engine = VisualWindowCaptureEngine(is_live_mode=True)
    before = engine.capture_window(hwnd)
    target = _resolve_text_control(hwnd)
    WindowMessageAdapter().send_text(target, str(req["text"]))
    time.sleep(0.3)
    after = engine.capture_window(hwnd)
    diff = engine.compute_visual_difference(before, after)
    return {
        "before": {
            "is_live_capture": bool(before.is_live_capture),
            "width": before.width,
            "height": before.height,
            "pixel_hash": before.pixel_hash,
            "dhash": before.dhash,
        },
        "after": {
            "is_live_capture": bool(after.is_live_capture),
            "width": after.width,
            "height": after.height,
            "pixel_hash": after.pixel_hash,
            "dhash": after.dhash,
        },
        "diff": diff,
        "target_hwnd": int(target),
    }


def _op_capture(req: dict) -> dict:
    from services.ai_desktop.visual_engine import VisualWindowCaptureEngine

    hwnd = int(req["hwnd"])
    snap = VisualWindowCaptureEngine(is_live_mode=True).capture_window(hwnd)
    return {
        "hwnd": int(snap.hwnd),
        "width": int(snap.width),
        "height": int(snap.height),
        "pixel_hash": snap.pixel_hash,
        "dhash": snap.dhash,
        "is_live_capture": bool(snap.is_live_capture),
        "has_bitmap": snap.raw_bitmap_bytes is not None,
        "raw_bitmap_bytes_len": len(snap.raw_bitmap_bytes or b""),
    }


def _op_som(req: dict) -> dict:
    from services.ai_desktop.uia_tree_inspector import UIATreeInspector
    from services.ai_desktop.visual_engine import VisualWindowCaptureEngine

    hwnd = int(req["hwnd"])
    snapshot = UIATreeInspector(is_live_mode=True).inspect_tree(hwnd)
    marks = VisualWindowCaptureEngine.generate_som_from_uia(snapshot)
    return {
        "hwnd": int(snapshot.hwnd),
        "engine": snapshot.engine,
        "element_count": int(snapshot.element_count),
        "snapshot_hash": snapshot.snapshot_hash,
        "som_marks": marks,
    }


def run_in_sandbox(sandbox, request: dict, timeout: float = 40) -> dict:
    """Chạy một op của helper trong sandbox và trả về payload ``result``."""
    import json as _json

    proc = sandbox.spawn_process(
        [sys.executable, "-m", "tests.sandbox_desktop_helper", _json.dumps(request)]
    )
    out, err = proc.communicate(timeout=timeout)
    payload = None
    for line in reversed((out or "").strip().splitlines()):
        try:
            payload = _json.loads(line)
            break
        except Exception:
            continue
    assert payload is not None, f"Helper không trả JSON. rc={proc.returncode} out={out!r} err={err!r}"
    assert payload.get("ok") is True, payload
    return payload["result"]


OPS = {
    "read_window": _op_read_window,
    "send_text": _op_send_text,
    "get_text": _op_get_text,
    "actuator": _op_actuator,
    "uia": _op_uia,
    "uia_scroll": _op_uia_scroll,
    "capture": _op_capture,
    "scroll_info": _op_scroll_info,
    "som": _op_som,
    "visual_diff": _op_visual_diff,
}


def main() -> int:
    try:
        request = json.loads(sys.argv[1])
        op = OPS[str(request["op"])]
        result = op(request)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=True), flush=True)
        return 0
    except Exception as exc:
        import traceback

        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()[-2000:],
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
