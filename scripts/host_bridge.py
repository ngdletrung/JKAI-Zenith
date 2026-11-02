# -*- coding: utf-8 -*-
"""
scripts/host_bridge.py
[JKAI ZENITH: HOST SATELLITE READ-ONLY WORKER v36.0]
Tiến trình Quan sát Độc lập (Pure Read-Only Host Satellite):
1. Telemetry phần cứng chuẩn Windows NT Kernel PDH (CPU, RAM, GPU, VRAM, Disk, Ethernet Link Speed).
2. Native WebSocket uplink 1.0s/lần cho Dashboard http://localhost:9999/.
3. Nhận thức thị giác thụ động (Passive Observation): MSS Screen Capture, UIA3 Tree Inspection, Fast Find.
4. Ranh giới bảo mật nghiêm ngặt (Strict Read-Only Boundary):
   - Bind duy nhất trên 127.0.0.1 (Local Loopback).
   - Tuyệt đối KHÔNG có endpoint /terminal (ngăn chặn raw shell).
   - Tuyệt đối KHÔNG có endpoint mutation (click, type, move chuyển sang mutation worker riêng).
   - CORS giới hạn nghiêm ngặt cho Mission Control (9998, 9999).
"""

import asyncio
import base64
import ctypes
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import mss
import mss.tools
import psutil
import uvicorn
import win32api
import win32con
import win32gui
import win32pdh
import win32process
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Thêm đường dẫn root để import services.ai_desktop
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ai_desktop import (
    NativeWindowInspector,
    UIATreeInspector,
    VisualWindowCaptureEngine,
)
from services.ai_desktop.host_bridge_stream_guard import HostBridgeStreamGuard, WebSocketSecurityException
from core.security.runtime_secrets import (
    authorize_bearer,
    ensure_runtime_tokens,
    fingerprint,
    get_secret,
)

def ensure_interactive_desktop():
    try:
        h_desk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
        if not h_desk:
            h_desk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            ctypes.windll.user32.SetThreadDesktop(h_desk)
    except Exception:
        pass

ensure_interactive_desktop()

app = FastAPI(
    title="JKAI Zenith Host Satellite Read-Only Worker v36.0",
    description="Dedicated Read-Only Telemetry & Passive Perception Service for JKAI Zenith"
)

# CORS giới hạn nghiêm ngặt, loại bỏ hoàn toàn wildcard "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:9998",
        "http://localhost:9998",
        "http://127.0.0.1:9999",
        "http://localhost:9999",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Khởi tạo PDH Query cho CPU, GPU, VRAM, Disk, Network toàn cục
try:
    perf_query = win32pdh.OpenQuery()
    cpu_counter = win32pdh.AddCounter(perf_query, r"\Processor Information(_Total)\% Processor Utility")
    gpu_counter = win32pdh.AddCounter(perf_query, r"\GPU Engine(*engtype_3D)\Utilization Percentage")
    vram_counter = win32pdh.AddCounter(perf_query, r"\GPU Adapter Memory(*)\Dedicated Usage")
    disk_counter = win32pdh.AddCounter(perf_query, r"\PhysicalDisk(_Total)\% Disk Time")
    net_counter = win32pdh.AddCounter(perf_query, r"\Network Interface(*)\Bytes Total/sec")
    net_bw_counter = win32pdh.AddCounter(perf_query, r"\Network Interface(*)\Current Bandwidth")
    win32pdh.CollectQueryData(perf_query)
except Exception:
    perf_query = None

# [RUNTIME-SECRETS] JKAI tự sinh token vận chuyển; host_bridge là writer duy nhất.
# Container đọc cùng file qua mount read-only /shared/secrets. Không có token => fail-closed.
try:
    _secrets_bootstrap = ensure_runtime_tokens()
    _ws_token = get_secret("SATELLITE_WS_TOKEN")
    print(
        f"[RUNTIME-SECRETS] status={_secrets_bootstrap.get('status')} "
        f"path={_secrets_bootstrap.get('path')} ws_fp={fingerprint(_ws_token) if _ws_token else 'NONE'}"
    )
except OSError as _secrets_err:
    print(f"[RUNTIME-SECRETS] WARN: không ghi được file token ({_secrets_err}) — protected routes fail-closed.")


def _presented_token(request: Request) -> str:
    for header in ("X-AKAI-TOKEN", "X-Host-Bridge-Token"):
        value = (request.headers.get(header) or "").strip()
        if value:
            return value
    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


@app.middleware("http")
async def verify_akai_token(request: Request, call_next):
    # Public endpoints cho Frontend Telemetry & Health Checks
    public_paths = ("/status", "/health", "/telemetry", "/ws", "/docs", "/openapi.json")
    if request.url.path in public_paths:
        return await call_next(request)

    expected = get_secret("SATELLITE_AUTH_TOKEN") or get_secret("AKAI_SATELLITE_TOKEN")
    ok, code = authorize_bearer(_presented_token(request), expected)
    if not ok:
        from fastapi.responses import JSONResponse

        status_code = 503 if code == "AUTH_NOT_CONFIGURED" else 403
        return JSONResponse(
            content={
                "error": code,
                "detail": (
                    "Host bridge chưa có SATELLITE_AUTH_TOKEN — protected routes fail-closed."
                    if code == "AUTH_NOT_CONFIGURED"
                    else "TRUY CẬP TRÁI PHÉP: token host bridge không hợp lệ."
                ),
            },
            status_code=status_code,
        )
    return await call_next(request)

window_inspector = NativeWindowInspector()
tree_inspector = UIATreeInspector(is_live_mode=True)
visual_engine = VisualWindowCaptureEngine(is_live_mode=True)
stream_guard = HostBridgeStreamGuard()

STREAM_ELEMENT_LIMIT = 40

def serialize_stream_elements(elements: Any, limit: int = STREAM_ELEMENT_LIMIT) -> list:
    """
    Serialize UIA elements cho Read-Only Stream.
    Tuyệt đối không phát tán el.value ra ngoài (có thể chứa mật khẩu/PII).
    """
    return [
        {
            "ref": el.ref,
            "name": el.name,
            "control_type": el.control_type,
            "automation_id": el.automation_id,
            "rect": list(el.rect),
            "center": list(el.center),
            "is_enabled": el.is_enabled,
        }
        for el in list(elements)[:limit]
    ]

# ----------------- TELEMETRY & HARDWARE PULSE -----------------

_host_cpu_window = []

def sample_telemetry_dict():
    """Truy vấn dữ liệu phần cứng trực tiếp từ NT Kernel PDH (Chuẩn Task Manager 100%)."""
    global _host_cpu_window
    cpu = 0.0
    gpu = 0.0
    vram_mb = 0
    vram_pct = 0.0
    disk = 0.0
    net_kbps = 0.0
    net_pct = 0.0
    link_speed_mbps = 1000.0
    net_iface = "Ethernet"

    if perf_query is not None:
        try:
            win32pdh.CollectQueryData(perf_query)
            try:
                cpu_raw = win32pdh.GetFormattedCounterValue(cpu_counter, win32pdh.PDH_FMT_DOUBLE)[1]
                val = min(max(cpu_raw, 0.0), 100.0)
                _host_cpu_window.append(val)
                if len(_host_cpu_window) > 3:
                    _host_cpu_window.pop(0)
                cpu = round(sum(_host_cpu_window) / len(_host_cpu_window), 1)
            except Exception:
                cpu = round(psutil.cpu_percent(interval=None), 1)

            try:
                vals_gpu = win32pdh.GetFormattedCounterArray(gpu_counter, win32pdh.PDH_FMT_DOUBLE)
                gpu = round(min(sum(v for v in vals_gpu.values() if v is not None), 100.0), 1)
            except Exception:
                gpu = 0.0

            try:
                vals_vram = win32pdh.GetFormattedCounterArray(vram_counter, win32pdh.PDH_FMT_LARGE)
                vram_bytes = max(vals_vram.values()) if vals_vram else 0
                vram_mb = int(vram_bytes / (1024 * 1024))
                vram_pct = round(min((vram_mb / 8192) * 100.0, 100.0), 1)
            except Exception:
                vram_mb = 0
                vram_pct = 0.0

            try:
                disk_raw = win32pdh.GetFormattedCounterValue(disk_counter, win32pdh.PDH_FMT_DOUBLE)[1]
                disk = round(min(max(disk_raw, 0.0), 100.0), 1)
            except Exception:
                disk = 0.0

            try:
                net_vals = win32pdh.GetFormattedCounterArray(net_counter, win32pdh.PDH_FMT_DOUBLE)
                bw_vals = win32pdh.GetFormattedCounterArray(net_bw_counter, win32pdh.PDH_FMT_LARGE)
                
                total_bytes = 0.0
                max_iface_bytes = -1.0
                active_iface_name = "Ethernet"

                for if_name, bts in net_vals.items():
                    if bts is not None:
                        total_bytes += bts
                        if bts > max_iface_bytes:
                            max_iface_bytes = bts
                            active_iface_name = if_name

                net_kbps = round((total_bytes * 8) / 1000, 1)

                bw_bps = bw_vals.get(active_iface_name, 0)
                if bw_bps <= 0:
                    for if_name, bw in bw_vals.items():
                        if bw and bw > bw_bps:
                            bw_bps = bw
                            if max_iface_bytes <= 0:
                                active_iface_name = if_name

                if bw_bps > 0:
                    link_speed_mbps = round(bw_bps / 1_000_000, 1)
                    usage_raw = ((total_bytes * 8) / bw_bps) * 100.0
                    net_pct = round(min(100.0, max(1.5 if total_bytes > 0 else 0.0, usage_raw)), 1)
                else:
                    link_speed_mbps = 1000.0
                    net_pct = round(min(100.0, max(1.5 if net_kbps > 0 else 0.0, (net_kbps / 10000) * 100.0)), 1)
                
                net_iface = active_iface_name
            except Exception:
                net_kbps = 0.0
                net_pct = 0.0
                link_speed_mbps = 1000.0
                net_iface = "Ethernet"
        except Exception:
            cpu = round(psutil.cpu_percent(interval=None), 1)
    else:
        cpu = round(psutil.cpu_percent(interval=None), 1)

    ram = round(psutil.virtual_memory().percent, 1)

    return {
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu,
        "vram_mb": vram_mb,
        "vram_total_mb": 8192,
        "vram_pct": vram_pct,
        "disk": disk,
        "net_kbps": net_kbps,
        "net_pct": net_pct,
        "link_speed_mbps": link_speed_mbps,
        "net_iface": net_iface,
        "ts": time.time()
    }

@app.get("/status")
@app.get("/health")
async def status():
    return {
        "status": "online",
        "service": "JKAI Zenith Host Satellite Read-Only Worker",
        "version": "v36.0",
        "mode": "HOST_READ_ONLY_OBSERVE",
        "mutation_allowed": False,
        "terminal_allowed": False,
        "message": "Pure Read-Only Satellite is online and secure."
    }

@app.get("/telemetry")
async def get_telemetry():
    try:
        return sample_telemetry_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_telemetry(websocket: WebSocket):
    """Direct Native WebSocket Uplink to Chrome Browser for Sub-Millisecond Realtime Telemetry."""
    await websocket.accept()
    try:
        while True:
            data = sample_telemetry_dict()
            await websocket.send_json(data)
            await asyncio.sleep(1.0)
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ----------------- PASSIVE OBSERVATION (READ-ONLY) -----------------

class ScreenshotRequest(BaseModel):
    hwnd: Optional[int] = None
    mark_som: bool = False

@app.post("/screenshot")
async def capture_screenshot(req: ScreenshotRequest):
    """Chụp ảnh màn hình thuần quan sát (Read-Only)."""
    ensure_interactive_desktop()
    try:
        snap = visual_engine.capture_window_or_desktop(hwnd=req.hwnd)
        result = {
            "status": "success",
            "hwnd": snap.hwnd,
            "width": snap.width,
            "height": snap.height,
            "image_base64": snap.image_base64,
            "captured_at": snap.captured_at,
            "visual_hash": snap.visual_hash
        }
        if req.mark_som:
            # Sinh Set-of-Marks thuần quan sát
            windows = window_inspector.inspect_window_elements(req.hwnd or win32gui.GetDesktopWindow())
            som_elements = [
                {
                    "name": w.name,
                    "control_type": w.control_type,
                    "rect": list(w.rect),
                    "center": list(w.center)
                }
                for w in windows[:30]
            ]
            result["som_marks"] = VisualWindowCaptureEngine.generate_som_from_uia(som_elements)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/windows")
async def list_windows() -> Dict[str, Any]:
    """Liệt kê danh sách tất cả các cửa sổ đang hiển thị trên Desktop của Master (Read-Only)."""
    windows = []
    fg_hwnd = win32gui.GetForegroundWindow()

    def enum_cb(h, _):
        if win32gui.IsWindowVisible(h):
            title = win32gui.GetWindowText(h).strip()
            rect = win32gui.GetWindowRect(h)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if title and width > 100 and height > 100:
                _, p = win32process.GetWindowThreadProcessId(h)
                try:
                    p_name = psutil.Process(p).name()
                except Exception:
                    p_name = "unknown"
                windows.append({
                    "hwnd": h,
                    "title": title,
                    "process_name": p_name,
                    "pid": p,
                    "rect": list(rect),
                    "is_foreground": (h == fg_hwnd),
                    "is_minimized": bool(win32gui.IsIconic(h)),
                })
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
    return {
        "status": "SUCCESS",
        "count": len(windows),
        "windows": windows,
        "timestamp": time.time()
    }

@app.get("/observe")
async def observe_window(hwnd: int):
    """Quan sát và bóc tách cây phần tử Native COM UIA3 của một cửa sổ cụ thể (Read-Only)."""
    ensure_interactive_desktop()
    try:
        snap = tree_inspector.inspect_tree(hwnd)
        som_marks = VisualWindowCaptureEngine.generate_som_from_uia(snap)
        return {
            "status": "success",
            "hwnd": hwnd,
            "elements_count": snap.elements_count,
            "snapshot_hash": snap.snapshot_hash,
            "som_marks": som_marks,
            "engine": snap.engine,
            "elements": [
                {
                    "ref": el.ref,
                    "name": el.name,
                    "control_type": el.control_type,
                    "automation_id": el.automation_id,
                    "rect": list(el.rect),
                    "center": list(el.center),
                    "is_enabled": el.is_enabled,
                    "value": el.value,
                }
                for el in snap.elements[:50]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/desktop_stream")
async def websocket_desktop_stream(websocket: WebSocket):
    """
    WebSocket stream thời gian thực phục vụ Mission Control Desktop Operator HUD:
    Phát sóng ảnh chụp cửa sổ + Bounding Box Set-of-Marks + Cây phần tử UIA (1.0 fps, Pure Read-Only).
    Được bảo vệ nghiêm ngặt bởi HostBridgeStreamGuard (Chống mọi lệnh mutation, xác thực token/session).
    """
    await websocket.accept()
    import uuid
    conn_id = f"conn_{uuid.uuid4().hex[:12]}"
    # Không có token/session mặc định: client phải cung cấp cả hai, nếu thiếu thì
    # HostBridgeStreamGuard từ chối (WS_AUTH_REQUIRED / WS_UNKNOWN_SESSION_REJECTED).
    token = websocket.query_params.get("token")
    session_id = websocket.query_params.get("session_id")
    origin = websocket.headers.get("origin")

    try:
        stream_guard.register_connection(conn_id, token, origin, session_id)
    except WebSocketSecurityException as sec_err:
        await websocket.send_json({"type": "error", "code": sec_err.code, "reason": sec_err.reason})
        await websocket.close(code=1008)
        return

    target_hwnd = None
    try:
        while True:
            # Nhận lệnh điều khiển (subscribe/ping) từ Client nếu có (non-blocking)
            try:
                raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                try:
                    res = stream_guard.filter_incoming_message(conn_id, raw_msg)
                    if res.get("type") == "subscribe":
                        target_hwnd = res["data"].get("hwnd")
                    elif res.get("type") == "ping":
                        await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
                except WebSocketSecurityException as msg_err:
                    await websocket.send_json({"type": "error", "code": msg_err.code, "reason": msg_err.reason})
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            ensure_interactive_desktop()
            curr_hwnd = target_hwnd if (target_hwnd and win32gui.IsWindow(target_hwnd)) else win32gui.GetForegroundWindow()
            if not curr_hwnd or not win32gui.IsWindow(curr_hwnd):
                curr_hwnd = win32gui.GetDesktopWindow()

            t_start = time.perf_counter()
            snap_visual = visual_engine.capture_window_or_desktop(hwnd=curr_hwnd)
            snap_uia = tree_inspector.inspect_tree(curr_hwnd)
            som_marks = VisualWindowCaptureEngine.generate_som_from_uia(snap_uia)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            title = win32gui.GetWindowText(curr_hwnd) or "Desktop"
            _, pid = win32process.GetWindowThreadProcessId(curr_hwnd)
            try:
                p_name = psutil.Process(pid).name()
            except Exception:
                p_name = "unknown"

            frame_payload = {
                "type": "desktop_frame",
                "hwnd": curr_hwnd,
                "window_title": title,
                "process_name": p_name,
                "pid": pid,
                "width": snap_visual.width,
                "height": snap_visual.height,
                "image_base64": snap_visual.image_base64,
                "visual_hash": snap_visual.pixel_hash[:16],
                "snapshot_hash": snap_uia.snapshot_hash[:16],
                "latency_ms": round(t_elapsed_ms, 2),
                "elements_count": snap_uia.element_count,
                "som_marks": som_marks[:40],
                "elements": serialize_stream_elements(snap_uia.elements),
                "timestamp": time.time()
            }

            await websocket.send_json(frame_payload)
            await asyncio.sleep(1.0)
    except Exception:
        pass
    finally:
        stream_guard.unregister_connection(conn_id)
        try:
            await websocket.close()
        except Exception:
            pass

@app.post("/actuator/fast_find")
async def api_fast_find(target_name: str, control_type: Optional[str] = None, hwnd: Optional[int] = None):
    """Fast-Path Semantic Query (<3ms) tìm kiếm phần tử giao diện bằng UIA3 (Thuần Read-Only)."""
    ensure_interactive_desktop()
    result = tree_inspector.fast_find_element(target_name, control_type=control_type, hwnd=hwnd)
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("JKAI ZENITH HOST SATELLITE READ-ONLY WORKER v36.0")
    print("Bound: 127.0.0.1:9997 (Strict Read-Only Mode)")
    print("=" * 60)
    # Ràng buộc nghiêm ngặt chỉ lắng nghe trên 127.0.0.1 (không mở ra 0.0.0.0)
    uvicorn.run(app, host="127.0.0.1", port=9997)
