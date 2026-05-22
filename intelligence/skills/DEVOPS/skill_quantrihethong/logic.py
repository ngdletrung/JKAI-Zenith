# =================================================================
# 🛠️ JKAI ZENITH: LOGIC QUẢN TRỊ HỆ THỐNG v31.0 (QUANTUM OPS)
# =================================================================

import os
import time
import shutil
from pathlib import Path
from core.config import settings

def ghi_tep_an_toan(path: str, content: str):
    """Ghi nội dung vào tệp tin với cơ chế Sao lưu tức thì."""
    try:
        path_obj = Path(path)
        if path_obj.exists():
            # 🛡️ [BACKUP-FIRST]: Tạo bản sao lưu trước khi ghi đè
            backup_dir = Path(settings.WORKSPACE_ROOT) / "archive" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{path_obj.name}.{int(time.time())}.bak"
            shutil.copy2(path, backup_path)
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "msg": "Ghi tệp an toàn thành công.", "backup": str(backup_path) if path_obj.exists() else None}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def xoa_tep_an_toan(path: str):
    """
    🗑️ [SOFT-DELETE]: Di chuyển tệp vào Thùng rác nơ-ron thay vì xóa vĩnh viễn.
    """
    try:
        src = Path(path)
        if not src.exists():
            return {"status": "error", "msg": "Tệp tin không tồn tại."}
            
        trash_dir = Path(settings.WORKSPACE_ROOT) / "archive" / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        
        dest = trash_dir / f"{src.name}.{int(time.time())}.trash"
        shutil.move(str(src), str(dest))
        
        return {
            "status": "success",
            "msg": f"💎 [TRASHED]: Đã di chuyển `{src.name}` vào Thùng rác nơ-ron.",
            "trash_path": str(dest)
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def phuc_hoi_tep(trash_filename: str, original_path: str):
    """
    🚑 [RESTORE]: Khôi phục tệp tin từ Thùng rác nơ-ron.
    """
    try:
        trash_path = Path(settings.WORKSPACE_ROOT) / "archive" / "trash" / trash_filename
        if not trash_path.exists():
            return {"status": "error", "msg": "Không tìm thấy tệp trong thùng rác."}
            
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.move(str(trash_path), original_path)
        return {"status": "success", "msg": f"✅ Đã khôi phục tệp về: {original_path}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def thong_ke_dung_luong(path: str = None):
    """📊 [TELEMETRY]: Thống kê dung lượng lưu trữ thực tế."""
    try:
        path = path or settings.WORKSPACE_ROOT
        total, used, free = shutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "percent_used": (used / total) * 100
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def liet_ke_thu_muc_elite(path: str = "."):
    """Liệt kê danh sách tệp với thông tin dung lượng và ngày sửa đổi."""
    try:
        p = Path(path)
        details = []
        for item in p.iterdir():
            mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item.stat().st_mtime))
            size = item.stat().st_size if item.is_file() else 0
            type_str = "DIR " if item.is_dir() else "FILE"
            details.append(f"[{type_str}] {item.name:30} | {size:10} bytes | {mtime}")
        return "\n".join(details)
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"
