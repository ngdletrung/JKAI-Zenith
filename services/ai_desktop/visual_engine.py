# -*- coding: utf-8 -*-
"""
services/ai_desktop/visual_engine.py
[JKAI Level 2 Desktop OS Actuator - Visual Perception & Diff Verification Engine]:
Kế thừa tinh hoa từ:
  - bytedance/UI-TARS-desktop & showlab/computer_use_ootb: Visual Grounding & Set-of-Marks (SoM)
  - simular-ai/Agent-S: Visual Observation & Diff State Tracking
  - Jeomon/Windows-Use: Windows GDI PrintWindow capture without disturbing user cursor

Nguyên tắc an toàn (Zero-Trust & Host Isolation):
  - 100% NON-INVASIVE: Sử dụng Win32 PrintWindow / BitBlt trực tiếp trên Device Context (DC) của HWND mục tiêu.
  - Tuyệt đối KHÔNG chiếm chuột, KHÔNG di chuyển con trỏ vật lý của Host, KHÔNG can thiệp màn hình làm việc của Master.
  - Tính toán Visual Difference Hash (dHash 64-bit & Pixel SHA-256) để cung cấp bằng chứng khách quan cho Cổng M5-G3.
"""

import hashlib
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class WindowVisualSnapshot:
    """Ảnh chụp và chữ ký thị giác của một cửa sổ tại một thời điểm (Thuần Perception Evidence)."""
    hwnd: int
    width: int
    height: int
    pixel_hash: str
    dhash: str
    captured_at: float
    is_live_capture: bool
    som_marks: List[Dict[str, Any]] = field(default_factory=list)
    raw_bitmap_bytes: Optional[bytes] = None
    image_base64: str = ""
    snapshot_hash: str = ""  # Gắn chặt (bind) với UIA snapshot_hash
    expires_at: float = 0.0
    mime_type: str = "image/jpeg"
    is_dispatch_proof: bool = False  # BẤT BIẾN: Visual artifact không phải là dispatch proof của verifier

    def __post_init__(self):
        if not self.expires_at and self.captured_at:
            self.expires_at = self.captured_at + 0.5

    @property
    def is_expired(self) -> bool:
        import time
        return time.time() > self.expires_at

    @property
    def visual_hash(self) -> str:
        return self.pixel_hash


class VisualWindowCaptureEngine:
    """
    Engine chụp ảnh cửa sổ mục tiêu và xác thực biến đổi thị giác (Visual Perception & Diff Verification).
    Tuân thủ chính sách nén JPEG có kiểm soát, chặn buffer vô hạn và giới hạn dung lượng Base64.
    """

    MAX_IMAGE_WIDTH = 1280
    MAX_IMAGE_HEIGHT = 720
    JPEG_QUALITY = 65
    MAX_BASE64_BYTES = 1024 * 1024 * 2  # 2MB trần Base64
    MAX_RAW_BITMAP_BYTES = 1920 * 1080 * 4  # Giới hạn buffer bitmap thô
    DEFAULT_TTL_SECONDS = 0.5

    def __init__(self, is_live_mode: bool = True):
        self.is_live_mode = is_live_mode and (sys.platform == "win32")

    @staticmethod
    def validate_jpeg_payload(base64_str: str) -> bool:
        """Kiểm định tính hợp lệ của chuỗi Base64 và định dạng JPEG MIME (Magic bytes FF D8 FF)."""
        if not base64_str or not isinstance(base64_str, str):
            return False
        if len(base64_str) > VisualWindowCaptureEngine.MAX_BASE64_BYTES:
            return False
        try:
            import base64
            data = base64.b64decode(base64_str)
            if len(data) < 3 or data[:3] != b"\xff\xd8\xff":
                return False
            return True
        except Exception:
            return False

    def capture_window(
        self,
        hwnd: int,
        som_elements: Optional[Any] = None,
        snapshot_hash: str = "",
    ) -> WindowVisualSnapshot:
        """
        Chụp ảnh cửa sổ target thông qua Win32 PrintWindow / DC Memory Bitmap.
        Ràng buộc Set-of-Marks và ảnh với snapshot_hash của UIA.
        Nếu không có Win32 hoặc ở mock mode, tạo synthetic snapshot dựa trên window geometry.
        """
        import time
        now = time.time()

        # Trích xuất snapshot_hash từ UIATreeSnapshot nếu được truyền vào som_elements
        effective_snap_hash = snapshot_hash
        if not effective_snap_hash and hasattr(som_elements, "snapshot_hash"):
            effective_snap_hash = som_elements.snapshot_hash

        if self.is_live_mode and hwnd > 0:
            try:
                return self._capture_win32_window(hwnd, som_elements, now, effective_snap_hash)
            except Exception:
                pass

        # Synthetic fallback capture (cho Mock / Headless testing)
        return self._capture_synthetic(hwnd, som_elements, now, effective_snap_hash)

    def _capture_win32_window(
        self,
        hwnd: int,
        som_elements: Optional[Any],
        now: float,
        snapshot_hash: str = "",
    ) -> WindowVisualSnapshot:
        import win32gui
        import win32ui
        import win32con
        import ctypes

        if not win32gui.IsWindow(hwnd):
            raise ValueError(f"HWND {hwnd} is not a valid window")

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = max(1, right - left)
        height = max(1, bottom - top)

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # Cờ PW_RENDERFULLCONTENT = 2 (Windows 8.1+) giúp chụp đầy đủ cả hardware-accelerated content
        PW_RENDERFULLCONTENT = 2
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        if result == 0:
            # Fallback sang BitBlt thông thường
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmp_info = save_bitmap.GetInfo()
        bmp_bits = save_bitmap.GetBitmapBits(True)

        # Giải phóng GDI handles ngay lập tức để tránh rò rỉ GDI resources
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        # Tính pixel SHA-256
        pixel_hash = hashlib.sha256(bmp_bits).hexdigest()

        # Tính dHash (Difference Hash) 64-bit đơn giản từ raw bits
        dhash = self._compute_quick_dhash(bmp_bits, width, height)

        # Chuẩn hóa Set-of-Marks (SoM)
        marks = self.generate_som_from_uia(som_elements) if som_elements else []

        # Tạo JPEG base64 phục vụ render trên Mission Control HUD
        image_base64 = ""
        try:
            from PIL import Image
            import io
            import base64
            img = Image.frombuffer("RGB", (width, height), bmp_bits, "raw", "BGRX", 0, 1)
            if width > 1280 or height > 720:
                img.thumbnail((1280, 720), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=65)
            image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass

        return WindowVisualSnapshot(
            hwnd=hwnd,
            width=width,
            height=height,
            pixel_hash=pixel_hash,
            dhash=dhash,
            captured_at=now,
            is_live_capture=True,
            som_marks=marks,
            raw_bitmap_bytes=bmp_bits[:4096],
            image_base64=image_base64,
            snapshot_hash=snapshot_hash,
            expires_at=now + self.DEFAULT_TTL_SECONDS,
            is_dispatch_proof=False,
        )

    def capture_window_or_desktop(self, hwnd: Optional[int] = None) -> WindowVisualSnapshot:
        """Chụp ảnh cửa sổ chỉ định hoặc toàn bộ desktop nếu hwnd không hợp lệ."""
        import win32gui
        target_hwnd = hwnd if (hwnd and hwnd > 0 and win32gui.IsWindow(hwnd)) else win32gui.GetDesktopWindow()
        return self.capture_window(target_hwnd)

    def _capture_synthetic(
        self,
        hwnd: int,
        som_elements: Optional[Any],
        now: float,
        snapshot_hash: str = "",
    ) -> WindowVisualSnapshot:
        """Tạo visual snapshot giả lập có tính xác định cao cho mock test suite."""
        width = 800
        height = 600
        som_count = len(som_elements) if (som_elements and isinstance(som_elements, (list, tuple))) else 0
        synthetic_payload = f"SYNTHETIC_WINDOW_{hwnd}_{width}x{height}_{som_count}".encode("utf-8")
        pixel_hash = hashlib.sha256(synthetic_payload).hexdigest()
        dhash = hashlib.md5(synthetic_payload).hexdigest()[:16]

        marks = self.generate_som_from_uia(som_elements) if som_elements else []

        # Tạo synthetic placeholder JPEG base64
        synthetic_b64 = ""
        try:
            from PIL import Image
            import io
            import base64
            img = Image.new("RGB", (width, height), color=(24, 24, 32))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            synthetic_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass

        return WindowVisualSnapshot(
            hwnd=hwnd,
            width=width,
            height=height,
            pixel_hash=pixel_hash,
            dhash=dhash,
            captured_at=now,
            is_live_capture=False,
            som_marks=marks,
            raw_bitmap_bytes=synthetic_payload,
            image_base64=synthetic_b64,
            snapshot_hash=snapshot_hash,
            expires_at=now + self.DEFAULT_TTL_SECONDS,
            is_dispatch_proof=False,
        )

    @staticmethod
    def _compute_quick_dhash(bmp_bits: bytes, width: int, height: int) -> str:
        """
        Tính Difference Hash nhanh từ bitmap buffer.
        Lấy mẫu 64 điểm đại diện để sinh chuỗi 64-bit nhị phân thể hiện gradient sáng/tối.
        """
        if not bmp_bits or len(bmp_bits) < 64:
            return "0" * 16

        step = max(1, len(bmp_bits) // 64)
        samples = [bmp_bits[i] for i in range(0, min(len(bmp_bits), step * 64), step)][:64]

        bits = []
        for i in range(len(samples) - 1):
            bits.append("1" if samples[i] < samples[i + 1] else "0")
        bits.append("0")

        bitstring = "".join(bits)
        try:
            hex_hash = f"{int(bitstring, 2):016x}"
        except Exception:
            hex_hash = "0" * 16
        return hex_hash

    @classmethod
    def generate_som_from_uia(cls, elements_or_snapshot: Any) -> List[Dict[str, Any]]:
        """
        Sinh danh sách Set-of-Marks (SoM) từ UIA Tree Snapshot hoặc danh sách element nodes.
        Hỗ trợ đối tượng UIAElementNode, dict hoặc UIATreeSnapshot theo chuẩn UI-TARS & Agent-S.
        """
        if not elements_or_snapshot:
            return []

        raw_elements = []
        if hasattr(elements_or_snapshot, "elements"):
            raw_elements = elements_or_snapshot.elements
        elif isinstance(elements_or_snapshot, list):
            raw_elements = elements_or_snapshot

        marks = []
        for idx, el in enumerate(raw_elements, start=1):
            if hasattr(el, "automation_id"):
                mark = {
                    "mark_id": idx,
                    "name": getattr(el, "name", "") or "",
                    "control_type": getattr(el, "control_type", "") or "",
                    "automation_id": getattr(el, "automation_id", "") or "",
                    "rect": getattr(el, "rect", (0, 0, 0, 0)),
                    "center": getattr(el, "center", (0, 0)),
                }
            elif isinstance(el, dict):
                mark = {
                    "mark_id": idx,
                    "name": el.get("name", ""),
                    "control_type": el.get("control_type", ""),
                    "automation_id": el.get("automation_id", ""),
                    "rect": el.get("rect", [0, 0, 0, 0]),
                    "center": el.get("center", (0, 0)),
                }
            else:
                continue
            marks.append(mark)
        return marks

    @staticmethod
    def compute_visual_difference(
        snap_before: WindowVisualSnapshot,
        snap_after: WindowVisualSnapshot,
    ) -> Dict[str, Any]:
        """
        So sánh hai snapshot thị giác để xác định độ lệch (Visual Difference).
        """
        exact_match = (snap_before.pixel_hash == snap_after.pixel_hash)
        
        # Tính khoảng cách Hamming giữa hai dHash
        h1 = int(snap_before.dhash, 16) if snap_before.dhash else 0
        h2 = int(snap_after.dhash, 16) if snap_after.dhash else 0
        xor_val = h1 ^ h2
        hamming_dist = bin(xor_val).count("1")

        # Visual diff được xác nhận nếu pixel hash thay đổi
        diff_detected = not exact_match

        return {
            "diff_detected": diff_detected,
            "exact_pixel_match": exact_match,
            "hamming_distance": hamming_dist,
            "pixel_hash_before": snap_before.pixel_hash,
            "pixel_hash_after": snap_after.pixel_hash,
            "dhash_before": snap_before.dhash,
            "dhash_after": snap_after.dhash,
            "geometry_match": (
                snap_before.width == snap_after.width and snap_before.height == snap_after.height
            ),
        }
