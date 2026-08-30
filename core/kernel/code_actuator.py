# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CODE ACTUATOR v2.0 (PRE-WARMED SANDBOX)          ║
║   Động Cơ Thực Thi Code Siêu Tốc & An Toàn Bằng AST Pre-Scanner   ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Tốc Độ Xuất Tệp Tin & Văn Bản. ⚡📊📄*
"""

from __future__ import annotations

import os
import re
import sys
import ast
import glob
import time
import logging
import traceback
from typing import Dict, Any, Optional, Tuple, List

from core.kernel.artifact_gate import verify_artifact_on_disk, format_delivery_receipt

logger = logging.getLogger("JKAI.CodeActuator")


class CodeActuator:
    """Sandbox thực thi mã Python siêu tốc và an toàn cho tác vụ xuất tệp tin."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or self._resolve_output_dir()
        os.makedirs(self.output_dir, exist_ok=True)
        # Pre-warm heavy modules to eliminate import latency
        self._prewarmed_scope = self._build_prewarmed_scope()

    def _build_prewarmed_scope(self) -> Dict[str, Any]:
        """Nạp sẵn các module văn phòng nặng vào bộ nhớ để tăng tốc thực thi exec()."""
        scope: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "os": os,
            "sys": sys,
            "OUTPUT_DIR": self.output_dir,
            "output_dir": self.output_dir,
        }
        # Thử pre-import các thư viện phổ biến
        import json, math, datetime
        scope["json"] = json
        scope["math"] = math
        scope["datetime"] = datetime
        scope["re"] = re
        try:
            import numpy as np
            scope["np"] = np
            scope["numpy"] = np
        except Exception:
            pass
        try:
            import pandas as pd
            scope["pd"] = pd
            scope["pandas"] = pd
        except Exception:
            pass
        try:
            import openpyxl
            scope["openpyxl"] = openpyxl
        except Exception:
            pass
        try:
            import docx
            scope["docx"] = docx
            scope["Document"] = docx.Document
        except Exception:
            pass
        try:
            import io
            scope["io"] = io
            scope["BytesIO"] = io.BytesIO
        except Exception:
            pass
        return scope

    def _resolve_output_dir(self) -> str:
        """Xác định đường dẫn thư mục outputs dùng chung."""
        candidates = []
        if os.path.isdir("/workspace"):
            candidates.append(os.path.join("/workspace", "workspace", "outputs"))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "outputs")))
        candidates.append(os.path.abspath("workspace/outputs"))
        candidates.append(os.path.abspath("files/Output"))

        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                test_f = os.path.join(cand, ".actuator_w")
                with open(test_f, "w") as f:
                    f.write("1")
                os.remove(test_f)
                return cand
            except Exception:
                continue
        return candidates[0]

    def extract_python_code(self, raw_text: str) -> Optional[str]:
        """Trích xuất khối mã Python từ phản hồi của Model."""
        if not raw_text or not isinstance(raw_text, str):
            return None

        # 1. Tìm khối ```python ... ```
        match = re.search(r"```(?:python|py)\s*\n(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 2. Tìm khối ``` ... ``` chung nếu có import hoặc thư viện văn phòng
        matches = re.findall(r"```\s*\n(.*?)```", raw_text, re.DOTALL)
        _EXPANDED_KEYWORDS = (
            "import ", "from ", "openpyxl", "docx", "pandas", "workbook",
            "DataFrame", "pd.ExcelWriter", "Document", "reportlab",
            "matplotlib", "plt.", "xlsxwriter", "BytesIO"
        )
        for m in matches:
            if any(k in m for k in _EXPANDED_KEYWORDS):
                return m.strip()

        # 3. Nếu toàn bộ chuỗi là mã Python
        clean = raw_text.strip()
        if clean.startswith("import ") or clean.startswith("from "):
            return clean

        return None

    def _validate_ast_safety(self, code_str: str) -> Tuple[bool, str]:
        """Kiểm tra an toàn tĩnh AST trước khi exec()."""
        try:
            tree = ast.parse(code_str)
            for node in ast.walk(tree):
                # Chặn các hàm phá hủy hệ thống
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("system", "popen", "rmtree"):
                            return False, f"Chặn lệnh không an toàn: `{node.func.attr}`"
            return True, "Code an toàn."
        except SyntaxError as syn_err:
            return False, f"Lỗi cú pháp Python: {syn_err}"
        except Exception as e:
            return True, "Bỏ qua kiểm tra AST nâng cao."

    def _sanitize_and_patch_code(self, code_str: str) -> str:
        """
        Tự động vá lỗi cú pháp openpyxl và chèn các lớp bọc an toàn trước khi chạy.
        """
        patch_header = """
import os, sys, glob, shutil
import openpyxl
from openpyxl.utils import get_column_letter

# 🛡️ Monkey patch an toàn cho openpyxl Worksheet.column_dimensions
try:
    _orig_dim_getitem = openpyxl.worksheet.dimensions.DimensionHolder.__getitem__
    def _safe_dim_getitem(self, key):
        if isinstance(key, int):
            key = get_column_letter(key)
        elif isinstance(key, str) and not key.isalpha():
            key = 'A'
        return _orig_dim_getitem(self, key)
    openpyxl.worksheet.dimensions.DimensionHolder.__getitem__ = _safe_dim_getitem
except Exception:
    pass

# 🛡️ Monkey patch an toàn cho openpyxl Worksheet.extend (không tồn tại trong API chuẩn)
# Model đôi khi sinh ws.extend(rows) thay vì for row in rows: ws.append(row)
try:
    from openpyxl.worksheet.worksheet import Worksheet as _WS
    if not hasattr(_WS, 'extend'):
        def _ws_extend(self, rows):
            for row in rows:
                self.append(list(row) if not isinstance(row, (list, tuple)) else row)
        _WS.extend = _ws_extend
except Exception:
    pass

# 🛡️ Monkey patch an toàn cho python-docx Document.add_heading (hỗ trợ tham số align / alignment)
try:
    import docx
    _orig_add_heading = docx.document.Document.add_heading
    def _safe_add_heading(self, text='', level=1, align=None, alignment=None, **kwargs):
        h = _orig_add_heading(self, text=text, level=level)
        al = align if align is not None else alignment
        if al is not None:
            try:
                h.alignment = al
            except Exception:
                pass
        return h
    docx.document.Document.add_heading = _safe_add_heading
except Exception:
    pass

# 🛡️ Monkey patch an toàn cho python-docx Paragraph.add_run() gọi với alignment
try:
    import docx.text.paragraph as _docx_para
    _orig_add_run = _docx_para.Paragraph.add_run
    def _safe_add_run(self, text=None, style=None, alignment=None, align=None, **kwargs):
        run = _orig_add_run(self, text=text, style=style)
        return run
    _docx_para.Paragraph.add_run = _safe_add_run
except Exception:
    pass
"""
        return patch_header + "\n" + code_str

    def execute_office_code(self, code_str: str, target_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Thực thi đoạn mã Python tạo tệp tin trong môi trường Pre-Warmed Sandbox với Auto-Healing.
        """
        if not code_str or not code_str.strip():
            return {"success": False, "error": "Mã nguồn Python trống rỗng."}

        # 1. Kiểm tra an toàn AST
        is_safe, reason = self._validate_ast_safety(code_str)
        if not is_safe:
            return {"success": False, "error": f"[SECURITY-BLOCKED]: {reason}"}

        # 2. Tạo bản sao execution_scope từ prewarmed và gán output_dir động
        execution_scope = dict(self._prewarmed_scope)
        execution_scope["OUTPUT_DIR"] = self.output_dir
        execution_scope["output_dir"] = self.output_dir
        
        # Ghi nhận trạng thái tệp tin trước khi chạy ở cả output_dir và cwd
        cwd_dir = os.getcwd()
        before_output_files = set(glob.glob(os.path.join(self.output_dir, "*")))
        before_cwd_files = set(glob.glob(os.path.join(cwd_dir, "*.*")))

        # Chuẩn hóa đường dẫn lưu và vá lỗi openpyxl
        normalized_code = self._normalize_save_paths(code_str, target_filename)
        patched_code = self._sanitize_and_patch_code(normalized_code)

        try:
            # Thực thi mã nguồn Python với tốc độ siêu thanh
            exec(patched_code, execution_scope)

            # 3. Phát hiện file mới xuất hiện tại output_dir
            after_output_files = set(glob.glob(os.path.join(self.output_dir, "*")))
            new_output_files = list(after_output_files - before_output_files)

            # 4. Phát hiện file mới xuất hiện tại cwd và tự động chuyển về output_dir
            after_cwd_files = set(glob.glob(os.path.join(cwd_dir, "*.*")))
            new_cwd_files = list(after_cwd_files - before_cwd_files)

            import shutil
            for cf in new_cwd_files:
                if os.path.isfile(cf) and not cf.endswith((".py", ".tmp", ".log")):
                    dest_f = os.path.join(self.output_dir, os.path.basename(cf))
                    try:
                        shutil.move(cf, dest_f)
                        new_output_files.append(dest_f)
                    except Exception:
                        pass

            created_file = None
            if new_output_files:
                created_file = max(new_output_files, key=os.path.getmtime)
            elif target_filename:
                cand = os.path.join(self.output_dir, os.path.basename(target_filename))
                if os.path.exists(cand):
                    created_file = cand

            if not created_file:
                # Quét tệp tin được cập nhật trong 15 giây gần nhất
                recent_files = [
                    f for f in glob.glob(os.path.join(self.output_dir, "*"))
                    if os.path.isfile(f) and (os.path.getmtime(f) >= time.time() - 15)
                ]
                if recent_files:
                    created_file = max(recent_files, key=os.path.getmtime)

            if created_file and os.path.exists(created_file):
                art_info = verify_artifact_on_disk(created_file)
                receipt = format_delivery_receipt(art_info)
                return {
                    "success": True,
                    "status": "success",
                    "file_path": created_file,
                    "created_file": created_file,
                    "filename": os.path.basename(created_file),
                    "artifact_info": art_info,
                    "delivery_receipt": receipt,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "file_path": None,
                    "created_file": None,
                    "error": "Mã đã chạy nhưng không tìm thấy tệp tin được lưu trên đĩa."
                }

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("[CODE-ACTUATOR-EXEC-FAIL]: %s\n%s", e, tb)
            return {
                "success": False,
                "status": "error",
                "file_path": None,
                "created_file": None,
                "error": f"Lỗi thực thi Python: {str(e)}",
                "traceback": tb
            }

    def _normalize_save_paths(self, code_str: str, target_filename: Optional[str]) -> str:
        """Tự động điều chỉnh đường dẫn lưu file để đảm bảo nằm trong output_dir."""
        # Thay thế chuẩn xác các lệnh save: wb.save('...'), doc.save('...'), plt.savefig('...'), df.to_excel('...')
        def _repl_save(match):
            caller = match.group(1)
            method = match.group(2)
            quote = match.group(3)
            fname = match.group(4)
            return f"{caller}.{method}(os.path.join(OUTPUT_DIR, {quote}{fname}{quote}))"

        pattern = re.compile(r"(\w+)\.(save|savefig|to_excel|to_csv|to_json|to_html)\((['\"])(.*?)\3\)")
        res = pattern.sub(_repl_save, code_str)
        return res


code_actuator = CodeActuator()
