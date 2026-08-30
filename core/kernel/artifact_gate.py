# -*- coding: utf-8 -*-
"""
📁 ARTIFACT GATE & DELIVERY RECEIPT GENERATOR
File: core/kernel/artifact_gate.py

Thực thi chuẩn Anti-Rationalization từ Agent Brain & Native Delivery Receipt từ DeerFlow 2.0:
1. Kiểm tra vật lý tệp tin trên đĩa (Tồn tại, đúng loại tệp, dung lượng > 0 bytes).
2. Tạo mã băm SHA-256 xác thực tính toàn vẹn (Integrity Proof).
3. Định dạng Biên lai Bàn giao (Delivery Receipt) hiển thị rõ ràng, gọn gàng cho User.
"""

from __future__ import annotations

import os
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("JKAI.ArtifactGate")


def verify_artifact_on_disk(file_path: str, min_bytes: int = 1) -> Dict[str, Any]:
    """
    Kiểm tra sự tồn tại vật lý và dung lượng của tệp tin trên đĩa.
    Trả về dict chứa trạng thái xác thực và metadata.
    """
    if not file_path or not isinstance(file_path, str):
        return {
            "verified": False,
            "reason": "Đường dẫn tệp tin trống hoặc không hợp lệ.",
            "file_path": str(file_path),
            "size_bytes": 0,
            "size_formatted": "0 B",
            "checksum": ""
        }

    # Chuẩn hóa đường dẫn
    clean_path = file_path.strip().strip("'").strip('"')
    
    # Kiểm tra tồn tại
    if not os.path.exists(clean_path):
        return {
            "verified": False,
            "reason": f"Tệp tin '{clean_path}' không tồn tại trên hệ thống tệp.",
            "file_path": clean_path,
            "size_bytes": 0,
            "size_formatted": "0 B",
            "checksum": ""
        }

    if not os.path.isfile(clean_path):
        return {
            "verified": False,
            "reason": f"Đường dẫn '{clean_path}' là thư mục, không phải tệp tin.",
            "file_path": clean_path,
            "size_bytes": 0,
            "size_formatted": "0 B",
            "checksum": ""
        }

    # Kiểm tra kích thước
    try:
        size = os.path.getsize(clean_path)
    except Exception as e:
        return {
            "verified": False,
            "reason": f"Không thể đọc kích thước tệp '{clean_path}': {e}",
            "file_path": clean_path,
            "size_bytes": 0,
            "size_formatted": "0 B",
            "checksum": ""
        }

    if size < min_bytes:
        return {
            "verified": False,
            "reason": f"Tệp tin '{clean_path}' rỗng (0 bytes), quá trình tạo tệp chưa hoàn tất.",
            "file_path": clean_path,
            "size_bytes": size,
            "size_formatted": "0 B",
            "checksum": ""
        }

    # Định dạng dung lượng
    size_formatted = _format_bytes(size)

    # Tính checksum SHA-256 nếu file <= 50MB
    checksum = ""
    if size <= 50 * 1024 * 1024:
        try:
            h = hashlib.sha256()
            with open(clean_path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            checksum = h.hexdigest()[:16]
        except Exception:
            checksum = ""

    filename = os.path.basename(clean_path)
    return {
        "verified": True,
        "reason": "Tệp tin tồn tại hợp lệ trên đĩa và có dung lượng.",
        "file_path": clean_path,
        "filename": filename,
        "size_bytes": size,
        "size_formatted": size_formatted,
        "checksum": checksum,
    }


def format_delivery_receipt(artifact_info: Dict[str, Any]) -> str:
    """Định dạng Biên lai Bàn giao (Native Delivery Receipt) chuẩn Markdown kèm link tải."""
    if not artifact_info or not artifact_info.get("verified"):
        return ""

    filename = artifact_info.get("filename", "document")
    size_str = artifact_info.get("size_formatted", "N/A")
    filepath = artifact_info.get("file_path", "")
    checksum = artifact_info.get("checksum", "")

    receipt = (
        f"\n\n📁 **Biên Lai Bàn Giao Tệp:**\n"
        f"- **Tên tệp:** `{filename}`\n"
        f"- **Kích thước:** `{size_str}`\n"
        f"- **Trạng thái:** ✅ Đã tạo thành công & xác thực vật lý trên đĩa (SHA256: `{checksum}`)\n"
        f"- 📥 **Tải về ngay:** [👉 Bấm vào đây để tải file `{filename}`](/outputs/{filename})\n"
    )
    return receipt


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
