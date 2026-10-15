import os
import sys
import subprocess
import json
import shutil
import asyncio
import ast
import time
import hashlib
import re
import shlex
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from core.utils.security_audit import auditor
from core.utils.engine import engine

# ⚙️ [ZENITH-SYSTEM-CORE]: Hệ vận động cốt lõi của JKAI.

def _resolve_target_path(target_path: str) -> str:
    """Chuẩn hóa và chuyển đổi đường dẫn /workspace sang đường dẫn thực tế nếu chạy ngoài container."""
    if not target_path:
        return ""
    p = str(target_path).replace("\\", "/").strip()
    if p.startswith("/workspace"):
        if not os.path.exists("/workspace") or not os.path.isdir("/workspace"):
            try:
                from core.utils.project_workspace import get_jkai_workspace_root
                ws_root = str(get_jkai_workspace_root()).replace("\\", "/").rstrip("/")
                rel = p[len("/workspace"):].lstrip("/")
                p = f"{ws_root}/{rel}" if rel else ws_root
            except Exception:
                pass
    return os.path.normpath(p)

PROTECTED_PATTERNS = [
    ".env", ".git", "credential", "secrets", ".key", ".pem", "id_rsa",
    "/etc/shadow", "/etc/passwd", "/etc/sudoers"
]

def _ensure_tools_importable() -> None:
    """Bao dam `import tools.*` hoat dong trong moi container (brain/executor/host).

    Mot so container chi mount/goi thu vien `core` ma khong co `tools` tren
    sys.path -> ModuleNotFoundError -> LOCAL-DIRECT-FAIL -> don viec sang
    HTTP executor mot cach khong can thiet. Ham nay chen workspace root vao
    sys.path (neu thieu) truoc moi lan import tools.*.
    """
    try:
        import tools.web_search  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    try:
        from core.utils.project_workspace import get_jkai_workspace_root
        root = str(get_jkai_workspace_root())
    except Exception:
        try:
            root = str(Path(__file__).resolve().parents[4])
        except Exception:
            return
    try:
        if root and root not in sys.path and os.path.isdir(root):
            sys.path.insert(0, root)
        if "tools" in sys.modules:
            tools_mod = sys.modules["tools"]
            ws_tools = os.path.join(root, "tools")
            if os.path.isdir(ws_tools) and hasattr(tools_mod, "__path__") and ws_tools not in tools_mod.__path__:
                tools_mod.__path__.append(ws_tools)
    except Exception:
        pass

FORBIDDEN_SYSTEM_ROOTS = [
    "/", "c:", "c:/", "c:\\", "~", "~/", "d:", "d:/"
]

def _guard_path_internal(target_path: str) -> Optional[str]:
    """Kiểm tra đường dẫn nhạy cảm hoặc nguy hiểm trước khi tác động."""
    if not target_path or not str(target_path).strip():
        return "Đường dẫn không được rỗng."
    resolved = _resolve_target_path(target_path)
    norm = str(resolved).replace("\\", "/").strip().lower()
    
    # Chặn root trực tiếp
    if norm in FORBIDDEN_SYSTEM_ROOTS:
        return f"Thao tác trên thư mục gốc/hệ thống '{target_path}' bị nghiêm cấm để bảo vệ an toàn."

    for pat in PROTECTED_PATTERNS:
        if pat in norm:
            return f"Truy cập tệp/thư mục '{target_path}' bị từ chối do chính sách bảo vệ an ninh ({pat})."

    # Kiểm tra đường dẫn hệ điều hành nhạy cảm
    try:
        abs_norm = os.path.abspath(resolved).replace("\\", "/").lower()
        for froot in ["c:/windows", "c:/program files", "c:/program files (x86)", "/etc", "/boot", "/sys", "/proc"]:
            if abs_norm == froot or abs_norm.startswith(froot + "/"):
                return f"Thao tác trên đường dẫn hệ thống nhạy cảm '{target_path}' bị từ chối ({froot})."
    except Exception:
        pass

    return None

def _calculate_sha256(filepath: str) -> str:
    """Tính toán mã băm SHA-256 thực chứng của tệp trên đĩa."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def _write_atomic_sync(target_path: str, content: str) -> str:
    """Ghi nguyên tử (Atomic Write) qua tệp tạm rồi đổi tên bằng os.replace."""
    dir_name = os.path.dirname(target_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    temp_file = os.path.join(dir_name, f".tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(temp_file, "w", encoding="utf-8", newline="") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, target_path)
    except Exception:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        raise
    return target_path

def _create_backup(target_path: str) -> Optional[str]:
    """Tự động sao lưu tệp trước khi can thiệp (C3/M0)."""
    if os.path.exists(target_path) and os.path.isfile(target_path):
        backup_path = f"{target_path}.bak.{int(time.time())}"
        shutil.copy2(target_path, backup_path)
        return backup_path
    return None


async def list_dir(path: str = "", directory_path: str = "", DirectoryPath: str = "", task_id: str = "sys", **kwargs):
    """📂 [SCOUTING]: Liệt kê danh sách tệp tin và thư mục."""
    target_path = _resolve_target_path(DirectoryPath or directory_path or path or kwargs.get("DirectoryPath") or kwargs.get("path") or ".")
    try:
        items = os.listdir(target_path)
        result = []
        for item in items:
            full_path = os.path.join(target_path, item)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            result.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": size
            })
        return {"status": "success", "path": os.path.abspath(target_path), "items": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def view_file(
    path: str = "",
    file_path: str = "",
    AbsolutePath: str = "",
    start_line: int = 1,
    end_line: int = 500,
    outline: bool = False,
    task_id: str = "sys",
    **kwargs,
):
    """👁️ [VISION]: Đọc nội dung tệp tin theo khoảng dòng (start_line..end_line) hoặc xem mục lục AST (outline=True)."""
    raw_path = path or file_path or AbsolutePath or kwargs.get("AbsolutePath") or kwargs.get("TargetFile") or ""
    target_path = _resolve_target_path(raw_path)
    s_line = int(kwargs.get("StartLine") or start_line or 1)
    e_line = int(kwargs.get("EndLine") or end_line or 500)
    want_outline = bool(outline or kwargs.get("outline", False))
    try:
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}

        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
        lines = raw_text.splitlines(keepends=True)
        total_lines = len(lines)

        if want_outline:
            if target_path.endswith(".py"):
                from core.utils.ast_code_auditor import extract_python_file_outline
                outline_text = extract_python_file_outline(raw_text, filename=target_path)
            else:
                headings = [
                    f"[L{idx}] {ln.strip()}"
                    for idx, ln in enumerate(lines, 1)
                    if ln.lstrip().startswith(("#", "def ", "class ", "function ", "export "))
                ]
                outline_text = "\n".join(headings[:200]) if headings else f"[L1-L{total_lines}] ({total_lines} lines)"
            return {
                "status": "success",
                "path": os.path.abspath(target_path),
                "total_lines": total_lines,
                "outline": outline_text,
                "content": outline_text,
            }

        s_idx = max(1, s_line)
        e_idx = min(total_lines, max(s_idx, e_line)) if total_lines > 0 else 0
        content = "".join(lines[s_idx - 1 : e_idx]) if total_lines > 0 else ""
        return {
            "status": "success",
            "path": os.path.abspath(target_path),
            "start_line": s_idx,
            "end_line": e_idx,
            "total_lines": total_lines,
            "has_more": e_idx < total_lines,
            "content": content,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}


async def view_file_outline(path: str = "", file_path: str = "", AbsolutePath: str = "", task_id: str = "sys", **kwargs):
    """🗺️ [AST-OUTLINE]: Xem nhanh mục lục cấu trúc Classes/Functions kèm số dòng [Lstart-Lend] của tệp tin."""
    return await view_file(
        path=path,
        file_path=file_path,
        AbsolutePath=AbsolutePath,
        outline=True,
        task_id=task_id,
        **kwargs,
    )


async def write_to_file(path: str = "", file_path: str = "", TargetFile: str = "", target_path: str = "", content: str = "", CodeContent: str = "", target_content: str = "", overwrite: bool = True, task_id: str = "sys", **kwargs):
    """✍️ [CREATION - M0 ATOMIC WRITE]: Kiến tạo tệp tin mới với Atomic Write, Auto-Backup, SHA-256 & ACI Diagnostics."""
    raw_path = target_path or path or file_path or TargetFile or kwargs.get("TargetFile") or ""
    target_path = _resolve_target_path(raw_path)
    target_content = target_content or content or CodeContent or kwargs.get("CodeContent") or ""
    try:
        guard_err = _guard_path_internal(target_path)
        if guard_err:
            return {"status": "error", "msg": guard_err}

        exists_before = os.path.exists(target_path)
        if exists_before and not overwrite:
            return {"status": "error", "msg": f"File '{target_path}' đã tồn tại. Dùng overwrite=True để ghi đè."}
        
        # 🔬 [AST + SYMTABLE ACI PRE-VALIDATION]: Chặn đứng lỗi cú pháp & chẩn đoán undefined_name/broken_import (<15ms)
        aci_diag = None
        if target_path.endswith(".py") and target_content:
            try:
                ast.parse(target_content)
            except SyntaxError as syn_err:
                return {
                    "status": "error",
                    "msg": f"AST Syntax Error: Mã nguồn Python gây lỗi cú pháp ({syn_err}). Thao tác ghi bị từ chối."
                }
            try:
                from core.utils.ast_code_auditor import analyze_python_aci_diagnostics
                aci_diag = analyze_python_aci_diagnostics(target_content, filename=target_path)
            except Exception:
                aci_diag = None

        # 🛡️ [SECURITY-AUDIT]: Thẩm định an ninh trước khi ghi file
        report = auditor.audit_diff(target_content)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định tệp `{target_path}`:\n{log_msg}", task_id)

        # 💾 [AUTO-BACKUP]: Tự động sao lưu bản ghi cũ trước khi ghi đè (C3/M0)
        backup_path = None
        if exists_before:
            try:
                backup_path = _create_backup(target_path)
                if backup_path:
                    engine.publish_mission_log("INFO", f"Đã tự động sao lưu tệp `{target_path}` thành `{backup_path}`.", task_id)
            except Exception as b_err:
                engine.publish_mission_log("WARN", f"Không thể tạo backup cho `{target_path}`: {b_err}", task_id)

        # ⚛️ [ATOMIC-WRITE]: Ghi an toàn qua file tạm và atomic rename
        _write_atomic_sync(target_path, target_content)

        # 🔍 [PHYSICAL-VERIFICATION]: Kiểm chứng mã băm SHA-256 trên đĩa
        sha256_hash = _calculate_sha256(target_path)
        file_size = os.path.getsize(target_path)

        engine.publish_mission_log("ACTION", f"Ghi tệp thành công `{target_path}` (SHA256: {sha256_hash[:12]}..., Size: {file_size}B)", task_id)

        blast_impact = None
        if str(target_path).endswith(".py"):
            try:
                from core.utils.repo_map import notify_workspace_file_mutation
                blast_impact = notify_workspace_file_mutation(
                    target_path,
                    action="write_to_file",
                    task_id=task_id,
                    sha256=sha256_hash,
                )
            except Exception:
                blast_impact = None

        msg = f"Đã kiến tạo tệp `{target_path}` thành công."
        if aci_diag and (aci_diag.get("undefined_names") or aci_diag.get("broken_imports")):
            msg += (
                f"\n⚠️ [ACI-GUARDED-EDIT]: Phát hiện cảnh báo tĩnh — "
                f"undefined_names={aci_diag.get('undefined_names')}, "
                f"broken_imports={aci_diag.get('broken_imports')}."
            )
        if blast_impact and (
            blast_impact.get("broken_downstream_imports")
            or blast_impact.get("signature_changes")
        ):
            msg += (
                f"\n⚠️ [BLAST-RADIUS-WARNING]: Phát hiện phụ thuộc liên file bị ảnh hưởng sau khi ghi — "
                f"broken_downstream_imports={blast_impact.get('broken_downstream_imports')}, "
                f"signature_changes={blast_impact.get('signature_changes')}."
            )

        out_payload = {
            "status": "success",
            "msg": msg,
            "path": os.path.abspath(target_path),
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "backup_path": backup_path,
            "atomic": True,
        }
        if aci_diag is not None:
            out_payload["aci_diagnostics"] = aci_diag
        if blast_impact is not None:
            out_payload["blast_radius_impact"] = blast_impact
        return out_payload
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def replace_file_content(path: str = "", target: str = "", replacement: str = "", file_path: str = "", TargetFile: str = "", TargetContent: str = "", ReplacementContent: str = "", task_id: str = "sys", **kwargs):
    """🛠️ [SURGERY - M0 ATOMIC SURGERY]: Phẫu thuật thay thế nội dung tệp tin an toàn với Atomic Write, Checksum & ACI Diagnostics."""
    raw_path = path or file_path or TargetFile or kwargs.get("TargetFile") or kwargs.get("target_path") or ""
    target_path = _resolve_target_path(raw_path)
    tgt = target or TargetContent or kwargs.get("TargetContent") or ""
    repl = replacement or ReplacementContent or kwargs.get("ReplacementContent") or ""
    try:
        guard_err = _guard_path_internal(target_path)
        if guard_err:
            return {"status": "error", "msg": guard_err}

        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}
        
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
            
        # 🩹 [RESILIENT SURGERY]: So khớp đa tầng (Exact -> CRLF Normalized -> Line-stripped Fuzzy)
        match_found = False
        new_content = file_content

        # Tầng 1: Khớp chính xác tuyệt đối
        if tgt in file_content:
            new_content = file_content.replace(tgt, repl, 1)
            match_found = True
        else:
            # Tầng 2: Chuẩn hóa CRLF / LF (chống gãy trên Windows host)
            file_norm = file_content.replace("\r\n", "\n")
            tgt_norm = tgt.replace("\r\n", "\n")
            repl_norm = repl.replace("\r\n", "\n")

            if tgt_norm in file_norm:
                new_norm = file_norm.replace(tgt_norm, repl_norm, 1)
                if "\r\n" in file_content:
                    new_norm = new_norm.replace("\n", "\r\n")
                new_content = new_norm
                match_found = True
            else:
                # Tầng 3: So khớp dòng bỏ qua khoảng trắng thừa và sai lệch thụt lề
                f_lines = file_norm.split("\n")
                t_lines = [l.strip() for l in tgt_norm.split("\n") if l.strip()]
                if t_lines:
                    n_t = len(t_lines)
                    m_start = -1
                    for idx in range(len(f_lines) - n_t + 1):
                        window = [f_lines[idx + k].strip() for k in range(n_t)]
                        if window == t_lines:
                            m_start = idx
                            break
                    if m_start != -1:
                        r_lines = repl_norm.split("\n")
                        res_lines = f_lines[:m_start] + r_lines + f_lines[m_start + n_t:]
                        res_str = "\n".join(res_lines)
                        if "\r\n" in file_content:
                            res_str = res_str.replace("\n", "\r\n")
                        new_content = res_str
                        match_found = True

        if not match_found:
            return {
                "status": "error",
                "msg": (
                    f"❌ Lỗi: Không tìm thấy TargetContent '{tgt}' trong `{target_path}`.\n"
                    f"Nội dung tệp thực tế:\n{file_content}\n\n"
                    f"Vui lòng nhìn kỹ nội dung tệp ở trên và sao chép chính xác đoạn cần sửa vào TargetContent."
                )
            }
        
        # 🔬 [AST + SYMTABLE ACI PRE-VALIDATION]: Chặn đứng lỗi cú pháp & chẩn đoán undefined_name/broken_import (<15ms)
        aci_diag = None
        if target_path.endswith(".py"):
            try:
                ast.parse(new_content)
            except SyntaxError as syn_err:
                return {
                    "status": "error",
                    "msg": f"AST Syntax Error: Mã thay thế gây lỗi cú pháp ({syn_err}). Thao tác ghi bị từ chối."
                }
            try:
                from core.utils.ast_code_auditor import analyze_python_aci_diagnostics
                aci_diag = analyze_python_aci_diagnostics(new_content, filename=target_path)
            except Exception:
                aci_diag = None

        # 🛡️ [SECURITY-AUDIT]: Thẩm định an ninh phần thay thế
        report = auditor.audit_diff(repl)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định phẫu thuật trên `{target_path}`:\n{log_msg}", task_id)

        # 💾 [AUTO-BACKUP]: Sao lưu tệp tin trước khi ghi đè (C3)
        backup_path = None
        try:
            backup_path = _create_backup(target_path)
            if backup_path:
                engine.publish_mission_log("INFO", f"Đã tạo backup cho `{target_path}`: {backup_path}", task_id)
        except Exception as b_err:
            engine.publish_mission_log("WARN", f"Không thể tạo backup cho `{target_path}`: {b_err}", task_id)

        # ⚛️ [ATOMIC-WRITE]: Ghi an toàn qua file tạm và atomic rename
        _write_atomic_sync(target_path, new_content)

        # 🔍 [PHYSICAL-VERIFICATION]: Kiểm chứng mã băm SHA-256 sau phẫu thuật
        sha256_hash = _calculate_sha256(target_path)
        file_size = os.path.getsize(target_path)

        blast_impact = None
        if str(target_path).endswith(".py"):
            try:
                from core.utils.repo_map import notify_workspace_file_mutation
                blast_impact = notify_workspace_file_mutation(
                    target_path,
                    action="replace_file_content",
                    task_id=task_id,
                    sha256=sha256_hash,
                )
            except Exception:
                blast_impact = None

        msg = f"Phẫu thuật thành công trên tệp `{target_path}`."
        if aci_diag and (aci_diag.get("undefined_names") or aci_diag.get("broken_imports")):
            msg += (
                f"\n⚠️ [ACI-GUARDED-EDIT]: Phát hiện cảnh báo tĩnh — "
                f"undefined_names={aci_diag.get('undefined_names')}, "
                f"broken_imports={aci_diag.get('broken_imports')}."
            )
        if blast_impact and (
            blast_impact.get("broken_downstream_imports")
            or blast_impact.get("signature_changes")
        ):
            msg += (
                f"\n⚠️ [BLAST-RADIUS-WARNING]: Phát hiện phụ thuộc liên file bị ảnh hưởng sau khi sửa — "
                f"broken_downstream_imports={blast_impact.get('broken_downstream_imports')}, "
                f"signature_changes={blast_impact.get('signature_changes')}."
            )

        out_payload = {
            "status": "success",
            "msg": msg,
            "path": os.path.abspath(target_path),
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "backup_path": backup_path,
            "atomic": True,
        }
        if aci_diag is not None:
            out_payload["aci_diagnostics"] = aci_diag
        if blast_impact is not None:
            out_payload["blast_radius_impact"] = blast_impact
        return out_payload
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def delete_file(path: str = "", file_path: str = "", TargetFile: str = "", confirm: bool = False, task_id: str = "sys", **kwargs):
    """🗑️ [REMOVAL - M0 SECURE DELETE]: Xóa tệp tin với kiểm soát an toàn tuyệt đối và auto-backup."""
    raw_path = path or file_path or TargetFile or kwargs.get("TargetFile") or ""
    target_path = _resolve_target_path(raw_path)
    try:
        if not confirm:
            return {"status": "error", "msg": "Thao tác xóa tệp yêu cầu xác nhận bắt buộc: confirm=True."}
        
        guard_err = _guard_path_internal(target_path)
        if guard_err:
            return {"status": "error", "msg": guard_err}
            
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}
            
        if os.path.isdir(target_path):
            return {"status": "error", "msg": f"'{target_path}' là thư mục, không thể dùng delete_file."}
            
        # 💾 [SAFETY-BACKUP]: Tự động sao lưu trước khi xóa để có thể phục hồi (Safe Deletion)
        backup_path = None
        pre_delete_sha256 = None
        try:
            pre_delete_sha256 = _calculate_sha256(target_path)
            backup_path = _create_backup(target_path)
        except Exception as b_err:
            engine.publish_mission_log("WARN", f"Không thể tạo backup trước khi xóa `{target_path}`: {b_err}", task_id)

        os.remove(target_path)
        blast_impact = None
        if str(target_path).endswith(".py"):
            try:
                from core.utils.repo_map import notify_workspace_file_mutation
                blast_impact = notify_workspace_file_mutation(
                    target_path,
                    action="delete_file",
                    task_id=task_id,
                    sha256=pre_delete_sha256 or "",
                )
            except Exception:
                blast_impact = None

        engine.publish_mission_log("ACTION", f"Đã xóa tệp `{target_path}` thành công (Backup: {backup_path}).", task_id)
        ret = {
            "status": "success",
            "msg": f"Đã xóa tệp `{target_path}` thành công.",
            "path": os.path.abspath(target_path),
            "pre_delete_sha256": pre_delete_sha256,
            "backup_path": backup_path,
        }
        if blast_impact is not None:
            ret["blast_radius_impact"] = blast_impact
        return ret
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def verify_file(path: str = "", file_path: str = "", TargetFile: str = "", task_id: str = "sys", **kwargs):
    """🔍 [VERIFICATION - M0 SENSOR]: Kiểm chứng sự tồn tại vật lý và trích xuất SHA-256 Checksum trên đĩa."""
    raw_path = path or file_path or TargetFile or kwargs.get("target_path") or kwargs.get("TargetFile") or ""
    target_path = _resolve_target_path(raw_path)
    try:
        if not target_path or not str(target_path).strip():
            return {"status": "error", "msg": "Đường dẫn không được rỗng."}
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại trên đĩa."}
        if os.path.isdir(target_path):
            return {"status": "error", "msg": f"'{target_path}' là thư mục, không phải tệp tin."}
        
        sha = _calculate_sha256(target_path)
        size = os.path.getsize(target_path)
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            line_count = sum(1 for _ in f)
            
        return {
            "status": "success",
            "path": os.path.abspath(target_path),
            "exists": True,
            "is_file": True,
            "sha256": sha,
            "size_bytes": size,
            "line_count": line_count,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# Alias tiện dụng cho Runtime
read_file = view_file


# 🛡️ [M1 COMMAND POLICY GATE & HARD-DENY PATTERNS]
DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|\/s|\/q)\s+([~/]|\*|[a-zA-Z]:\\)",
    r"rm\s+.*[~/]\.ssh",
    r"mkfs",
    r"format\s+[a-zA-Z]:",
    r"dd\s+if=.*of=/dev/",
    r":\(\)\{\s*:\|:&\s*\};:",  # Forkbomb
    r"(curl|wget)\s+.*\|\s*(bash|sh|zsh|powershell|cmd)",
    r"(drop\s+database|truncate\s+table)",
    r"\/etc\/sudoers",
    r"\/etc\/shadow",
    r"\/etc\/passwd",
    r"diskpart",
    r"del\s+\/f\s+\/s\s+\/q\s+[a-zA-Z]:\\"
]

CONFIRMATION_COMMAND_PATTERNS = [
    r"kill\s+-9",
    r"taskkill\s+(\/f|\/F)",
    r"shutdown",
    r"reboot",
    r"netsh\s+advfirewall",
    r"iptables",
    r"useradd",
    r"net\s+user"
]

MAX_OUTPUT_BYTES = 16384  # 16KB limit in memory

def classify_command_policy(command: str) -> Tuple[str, Optional[str]]:
    """
    [M1 POLICY GATE]: Phân loại lệnh theo 4 tầng (Condition 1 & 2):
    - HARD_DENY: Lệnh phá hoại hệ thống hoặc bypass shell
    - REQUIRE_CONFIRMATION: Lệnh nhạy cảm cần xác nhận confirm=True
    - READ_ONLY: Lệnh trinh sát thuần túy, không có shell metacharacter
    - MUTATION_LOCAL: Lệnh thực thi / thay đổi trong workspace cục bộ
    """
    if not command or not command.strip():
        return "HARD_DENY", "Lệnh rỗng."

    cmd_clean = command.strip()
    cmd_lower = cmd_clean.lower()

    # 1. Kiểm tra HARD_DENY trước tiên (Condition 2)
    # Kiểm tra truy cập SSH / Credentials đặc biệt (HELD-001)
    if ".ssh" in cmd_lower and any(act in cmd_lower for act in ["rm", "del", "remove", "erase", ">"]):
        return "HARD_DENY", "Nghiêm cấm mọi hành vi can thiệp hoặc xóa credentials trong ~/.ssh."

    for pat in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pat, cmd_lower):
            return "HARD_DENY", f"Lệnh vi phạm chính sách an ninh bất biến (HARD-DENY pattern: {pat})."

    # Kiểm tra bypass trick nguy hiểm (pipe pipe, chain to dangerous)
    # Tách các lệnh con theo ; && || |
    subcommands = re.split(r";|&&|\|\||\|", cmd_clean)
    if len(subcommands) > 1:
        for sub in subcommands:
            sub_low = sub.strip().lower()
            for pat in DANGEROUS_COMMAND_PATTERNS:
                if re.search(pat, sub_low):
                    return "HARD_DENY", f"Phát hiện lệnh con nguy hiểm bị lách qua shell chaining: {pat}"

    # 2. Kiểm tra REQUIRE_CONFIRMATION
    for pat in CONFIRMATION_COMMAND_PATTERNS:
        if re.search(pat, cmd_lower):
            return "REQUIRE_CONFIRMATION", f"Lệnh tác động tiến trình/hệ thống nhạy cảm cần xác nhận: {pat}"

    # 3. Phân biệt shell metacharacters (Condition 1)
    has_chaining = any(sep in cmd_clean for sep in [";", "&&", "||", "|", "`", "$("])

    # python -c, powershell -encoded, cmd /c không bao giờ là READ_ONLY
    if "python -c" in cmd_lower or "powershell -enc" in cmd_lower or "cmd /c" in cmd_lower:
        return "MUTATION_LOCAL", None

    # Tách token lệnh đầu tiên
    try:
        tokens = shlex.split(cmd_clean, posix=False)
    except Exception:
        tokens = cmd_clean.split()

    if not tokens:
        return "HARD_DENY", "Không thể phân tách cú pháp lệnh."

    bin_name = os.path.basename(tokens[0]).lower().replace(".exe", "")

    # Nếu lệnh có chaining (pipe, and, or) -> Xếp vào MUTATION_LOCAL
    if has_chaining:
        return "MUTATION_LOCAL", None

    # Nếu là binary read-only thuần túy không có chaining
    if bin_name in ["ls", "dir", "cat", "type", "head", "tail", "pwd", "whoami", "hostname", "uname"]:
        return "READ_ONLY", None

    if bin_name in ["git", "pytest", "python", "npm", "node", "cargo"]:
        args = [t.lower() for t in tokens[1:]]
        if bin_name == "git" and args and args[0] in ["status", "log", "diff", "branch", "show", "rev-parse"]:
            return "READ_ONLY", None
        if bin_name == "pytest" and any(a in args for a in ["--collect-only", "--version"]):
            return "READ_ONLY", None
        if bin_name in ["python", "node", "npm", "cargo"] and any(a in args for a in ["--version", "-v", "-version"]):
            return "READ_ONLY", None
        return "MUTATION_LOCAL", None

    return "MUTATION_LOCAL", None


async def run_command(command: str = "", CommandLine: str = "", cwd: str = "", confirm: bool = False, timeout: float = 30.0, task_id: str = "sys", **kwargs):
    """⚡ [EXECUTION - M1 COMMAND SANDBOX]: Thực thi mật lệnh với Policy Gate 4 tầng, Timeout & Zombie Prevention."""
    cmd = (command or CommandLine or kwargs.get("CommandLine") or kwargs.get("cmd") or "").strip()
    if not cmd:
        return {"status": "error", "msg": "Mật lệnh rỗng.", "exit_code": -1, "policy_tier": "HARD_DENY"}

    # 1. Thẩm định Cổng Thẩm Quyền (Command Policy Gate - Condition 1 & 2)
    policy_tier, policy_reason = classify_command_policy(cmd)
    
    if policy_tier == "HARD_DENY":
        engine.publish_mission_log("RISK", f"[HARD-DENY]: Chặn đứng lệnh nguy hiểm: `{cmd}` ({policy_reason})", task_id)
        # 🛡️ [OPENCODE PROPOSAL 2]: Runtime Telemetry Harvester (Append-only gate intercepts)
        try:
            telemetry_dir = Path("data/telemetry")
            telemetry_dir.mkdir(parents=True, exist_ok=True)
            intercept_record = {
                "timestamp": time.time(),
                "task_id": task_id,
                "command": cmd,
                "policy_reason": policy_reason,
                "policy_tier": policy_tier,
                "cwd": cwd or kwargs.get("cwd", "")
            }
            with open(telemetry_dir / "gate_intercepts.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(intercept_record, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return {
            "status": "error",
            "msg": f"Cổng thẩm quyền từ chối lệnh [HARD-DENY]: {policy_reason}",
            "exit_code": 126,
            "policy_tier": policy_tier,
            "timed_out": False
        }

    if policy_tier == "REQUIRE_CONFIRMATION" and not confirm:
        return {
            "status": "error",
            "msg": f"Lệnh yêu cầu xác nhận bắt buộc (confirm=True): {policy_reason}",
            "exit_code": 126,
            "policy_tier": policy_tier,
            "timed_out": False
        }

    # 2. Nhốt CWD vào Workspace an toàn (Condition 5)
    default_ws = os.getcwd()
    run_cwd = cwd or kwargs.get("cwd") or kwargs.get("Cwd") or default_ws
    try:
        run_cwd_resolved = _resolve_target_path(run_cwd)
        run_cwd_abs = os.path.abspath(run_cwd_resolved)
        if not os.path.isdir(run_cwd_abs):
            run_cwd_abs = default_ws
    except Exception:
        run_cwd_abs = default_ws

    # Bóc tách tiền tố cd dư thừa nếu có (vd: cd /workspace/projects/foo && pytest)
    m_cd = re.match(r"^cd\s+(?:/d\s+)?([^\&]+)\s*&&\s*(.+)$", cmd, re.IGNORECASE)
    if m_cd:
        cd_target = _resolve_target_path(m_cd.group(1).strip().strip("'\""))
        try:
            cd_target_abs = os.path.abspath(cd_target)
            if cd_target_abs.lower() == run_cwd_abs.lower() or os.path.isdir(cd_target_abs):
                run_cwd_abs = cd_target_abs
                cmd = m_cd.group(2).strip()
        except Exception:
            pass

    # 3. Timeout bounds (Condition 4) - Mặc định 30s, trần tối đa 120s
    actual_timeout = min(max(float(timeout), 0.5), 120.0)

    # 4. Thực thi tiến trình an toàn
    start_time = time.time()
    timed_out = False
    process = None
    stdout_data = b""
    stderr_data = b""
    exit_code = -1

    try:
        # Audit log
        report = auditor.audit_diff(cmd)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định mật lệnh `{cmd}` (Tier: {policy_tier}):\n{log_msg}", task_id)

        # M1.1: Trực thi trực tiếp qua argv list (create_subprocess_exec) nếu không có shell metacharacters
        use_shell = any(sep in cmd for sep in [";", "&&", "||", "|", "`", "$(", "<", ">"])
        tokens = []
        if not use_shell:
            try:
                raw_tokens = shlex.split(cmd, posix=False) if sys.platform == "win32" else shlex.split(cmd)
                tokens = [
                    t[1:-1] if (sys.platform == "win32" and len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'")) else t
                    for t in raw_tokens
                ]
                bin_lower = os.path.basename(tokens[0]).lower().replace(".exe", "")
                if bin_lower in ["dir", "type", "cls", "copy", "del", "move", "ren", "md", "rd", "echo"]:
                    use_shell = True
            except Exception:
                use_shell = True

        process = None
        if not use_shell and tokens:
            bin_to_run = tokens[0]
            if bin_to_run.lower() in ("python", "python3") and sys.platform == "win32":
                bin_to_run = sys.executable
            try:
                process = await asyncio.create_subprocess_exec(
                    bin_to_run,
                    *tokens[1:],
                    cwd=run_cwd_abs,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            except (FileNotFoundError, OSError):
                use_shell = True

        if use_shell or process is None:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=run_cwd_abs,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=actual_timeout
            )
            exit_code = process.returncode
        except asyncio.TimeoutError:
            timed_out = True
            # Condition 4: Kill thật sau timeout + communicate lần 2 + đóng pipe thu hồi PID
            try:
                process.kill()
            except Exception:
                pass
            try:
                stdout_data, stderr_data = await asyncio.wait_for(process.communicate(), timeout=3.0)
            except Exception:
                pass
            exit_code = process.returncode if process.returncode is not None else -9
            engine.publish_mission_log("WARN", f"Lệnh vượt quá timeout {actual_timeout}s và đã bị tiêu diệt: `{cmd}`", task_id)

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "error",
            "msg": f"Lỗi khởi tạo tiến trình: {str(e)}",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "timed_out": timed_out,
            "policy_tier": policy_tier
        }

    duration_ms = round((time.time() - start_time) * 1000, 2)
    stdout_str = stdout_data.decode(errors="ignore") if stdout_data else ""
    stderr_str = stderr_data.decode(errors="ignore") if stderr_data else ""

    # Condition 6 + Slice 1.4 StreamBufferStore: Lưu toàn văn vào StreamBufferStore kèm stream_id thay vì cắt cụt mù quáng
    truncated = False
    stream_id = None
    stream_meta = None
    if len(stdout_str) > MAX_OUTPUT_BYTES:
        from core.utils.stream_buffer_store import store_stream
        stream_meta = store_stream(
            content=stdout_str,
            source_tool="run_command",
            task_id=task_id,
            preview_chars=MAX_OUTPUT_BYTES,
        )
        stream_id = stream_meta["stream_id"]
        stdout_str = (
            stdout_str[:MAX_OUTPUT_BYTES]
            + f"\n... [TRUNCATED - Output vượt quá {MAX_OUTPUT_BYTES} bytes | "
            f"stream_id={stream_id} | total_lines={stream_meta['total_lines']} | "
            f"coverage={stream_meta['coverage_ratio']} | "
            f"Dùng read_stream_window(stream_id='{stream_id}', start_line={stream_meta['next_start_line']}, end_line=...) "
            f"hoặc search_in_stream(stream_id='{stream_id}', query='...') để đọc tiếp]"
        )
        truncated = True
    if len(stderr_str) > MAX_OUTPUT_BYTES:
        from core.utils.stream_buffer_store import store_stream
        err_meta = store_stream(
            content=stderr_str,
            source_tool="run_command:stderr",
            task_id=task_id,
            preview_chars=MAX_OUTPUT_BYTES,
        )
        if not stream_id:
            stream_id = err_meta["stream_id"]
            stream_meta = err_meta
        stderr_str = (
            stderr_str[:MAX_OUTPUT_BYTES]
            + f"\n... [TRUNCATED - Stderr vượt quá {MAX_OUTPUT_BYTES} bytes | stream_id={err_meta['stream_id']}]"
        )
        truncated = True

    ret_payload = {
        "status": "success" if exit_code == 0 else "error",
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "policy_tier": policy_tier,
        "truncated": truncated,
    }
    if stream_id and stream_meta:
        ret_payload["stream_id"] = stream_id
        ret_payload["total_lines"] = stream_meta["total_lines"]
        ret_payload["coverage_ratio"] = stream_meta["coverage_ratio"]
        ret_payload["has_more"] = stream_meta["has_more"]
    return ret_payload


async def multi_replace_file_content(path: str, replacements: List[Dict[str, str]], task_id: str = "sys"):
    """🔬 [MULTI-SURGERY]: Phẫu thuật đa điểm trên tệp tin."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        for r in replacements:
            target = r.get("target")
            rep = r.get("replacement")
            if target in content:
                content = content.replace(target, rep)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "msg": f"Đã thực hiện {len(replacements)} ca phẫu thuật trên `{path}`."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def command_status(command_id: str, task_id: str = "sys"):
    """📊 [MONITORING]: Kiểm tra trạng thái mật lệnh đang chạy."""
    return {"status": "success", "msg": "Tính năng đang được đồng bộ hóa với hệ thống n8n."}

def _clean_query(query) -> str:
    if not query:
        return ""
    if isinstance(query, dict):
        for key in ["query", "q", "extracted_params", "description", "value"]:
            if val := query.get(key):
                return _clean_query(val)
        if len(query) == 1:
            return _clean_query(list(query.values())[0])
        return json.dumps(query)
    if isinstance(query, list):
        if len(query) > 0:
            return _clean_query(query[0])
        return ""
    if isinstance(query, str):
        query_str = query.strip()
        if query_str.startswith("{") and query_str.endswith("}"):
            try:
                parsed = json.loads(query_str)
                return _clean_query(parsed)
            except Exception:
                pass
        return query_str
    return str(query)

async def search_web(
    query: str,
    task_id: str = "sys",
    local_only: Optional[bool] = None,
    **kwargs,
):
    """🌐 [RECON]: Tầm soát Internet thấu thị (minh bạch Local-Only & tích hợp StreamBufferStore)."""
    _ensure_tools_importable()
    from tools.web_search import (
        build_transparent_refusal,
        execute_real_web_search_sync,
        is_local_only_enabled,
    )

    query = _clean_query(query)
    eff_local_only = kwargs.get("local_only", local_only)
    if is_local_only_enabled(eff_local_only):
        return build_transparent_refusal(query=query, reason="LOCAL_ONLY_MODE")

    # [Trọng điểm 2 - Multi-Query Deep Retrieval]: Kích hoạt khi có cờ deep=True/multi_query=True hoặc câu hỏi yêu cầu phân tích/tổng hợp chuyên sâu
    want_multi_query = bool(kwargs.get("deep") or kwargs.get("multi_query") or kwargs.get("deep_search"))
    if not want_multi_query:
        q_lower = query.lower()
        if any(w in q_lower for w in ("phân tích", "tổng hợp", "đánh giá", "toàn cảnh", "tuần qua", "overview")) and len(query.split()) >= 4:
            want_multi_query = True

    if want_multi_query and os.getenv("JKAI_MULTI_QUERY_ENABLED", "1") != "0":
        try:
            from core.os.cognition.multi_query_retriever import multi_query_retriever
            mq_res = await multi_query_retriever.retrieve_deep(
                query=query,
                task_id=task_id,
                local_only=bool(eff_local_only),
            )
            if isinstance(mq_res, dict) and mq_res.get("status") == "success":
                return mq_res
        except Exception:
            pass

    try:
        from intelligence.skills.CORE.OMNI_SEARCH_ENGINE.logic import omni_search

        res = await omni_search(query=query, task_id=task_id, local_only=eff_local_only, **kwargs)
        if isinstance(res, dict) and res.get("status") == "success":
            out_obj = res.get("output")
            text_val = out_obj.get("content", "") if isinstance(out_obj, dict) else str(out_obj or "")
            if len(text_val) > 8000 and not res.get("stream_id"):
                from core.utils.stream_buffer_store import store_stream

                env = store_stream(
                    content=text_val,
                    source_tool="search_web",
                    task_id=task_id,
                    mission_id=task_id,
                    preview_chars=8000,
                    metadata={"query": query},
                )
                res["stream_id"] = env["stream_id"]
                res["total_lines"] = env["total_lines"]
                res["coverage_ratio"] = env["coverage_ratio"]
                res["has_more"] = env["has_more"]
                res["next_start_line"] = env["next_start_line"]
            res["is_simulated"] = False
            return res
    except Exception:
        pass

    return execute_real_web_search_sync(
        query=query,
        task_id=task_id,
        mission_id=task_id,
        local_only=eff_local_only,
    )


async def read_url_content(
    url: str,
    task_id: str = "sys",
    local_only: Optional[bool] = None,
    **kwargs,
):
    """📄 [VISION]: Đọc nội dung URL thấu thị (kiểm tra SSRF/Egress allowlist + lưu toàn văn vào StreamBufferStore)."""
    import httpx
    _ensure_tools_importable()
    from tools.web_search import (
        build_transparent_refusal,
        is_local_only_enabled,
        validate_egress_url_ssrf_safe,
    )

    eff_local_only = kwargs.get("local_only", local_only)
    if is_local_only_enabled(eff_local_only):
        return build_transparent_refusal(query=url, reason="LOCAL_ONLY_MODE")

    ssrf_verdict = validate_egress_url_ssrf_safe(
        url=url,
        allowed_domains=kwargs.get("allowed_domains"),
    )
    if not ssrf_verdict.get("allowed"):
        return ssrf_verdict

    MAX_URL_PREVIEW_CHARS = 5000
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:

            resp = await client.get(f"https://r.jina.ai/{url}")
            if resp.status_code == 200:
                full_text = str(resp.text or "")
                if len(full_text) <= MAX_URL_PREVIEW_CHARS:
                    return {
                        "status": "success",
                        "is_simulated": False,
                        "url": url,
                        "stream_id": None,
                        "has_more": False,
                        "content": full_text,
                    }
                from core.utils.stream_buffer_store import store_stream

                env = store_stream(
                    content=full_text,
                    source_tool="read_url_content",
                    task_id=task_id,
                    mission_id=task_id,
                    preview_chars=MAX_URL_PREVIEW_CHARS,
                    metadata={"url": url},
                )
                sid = env["stream_id"]
                preview_with_banner = (
                    env["preview"]
                    + f"\n... [STREAM_BUFFERED: stream_id={sid} | "
                    f"lines_shown=1..{env['preview_end_line']}/{env['total_lines']} | "
                    f"coverage={env['coverage_ratio']} | "
                    f"Dùng read_stream_window(stream_id='{sid}', start_line={env['next_start_line']}, end_line=...) "
                    f"hoặc search_in_stream(stream_id='{sid}', query='...') để đọc tiếp phần còn lại]"
                )
                return {
                    "status": "success",
                    "is_simulated": False,
                    "url": url,
                    "stream_id": sid,
                    "total_lines": env["total_lines"],
                    "coverage_ratio": env["coverage_ratio"],
                    "has_more": env["has_more"],
                    "next_start_line": env["next_start_line"],
                    "content": preview_with_banner,
                }
            else:
                return {
                    "status": "unavailable",
                    "is_simulated": False,
                    "reason": f"JINA_HTTP_{resp.status_code}",
                    "url": url,
                    "msg": f"Jina.ai API Error: {resp.status_code}",
                }
    except Exception as e:
        return {
            "status": "unavailable",
            "is_simulated": False,
            "reason": "URL_FETCH_ERROR",
            "url": url,
            "msg": str(e),
        }

async def generate_image(prompt: str, task_id: str = "sys"):
    """🎨 [CREATION]: Kiến tạo hình ảnh từ tri tưởng tượng."""
    from intelligence.skills.skill_generate_image.logic import skill_generate_image
    return await skill_generate_image(prompt=prompt, task_id=task_id)

async def grep_search(
    query: str = "",
    path: str = ".",
    offset: int = 0,
    limit: int = 50,
    task_id: str = "sys",
    **kwargs,
):
    """🔍 [SCANNER]: Quét tìm từ khóa một lượt (single-pass) qua iter_workspace_files() kèm phân trang (offset, limit)."""
    import re
    import concurrent.futures
    from pathlib import Path
    from core.utils.project_workspace import iter_workspace_files
    
    query = query or kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("q") or ""
    raw_path = path or kwargs.get("SearchPath") or kwargs.get("directory") or kwargs.get("dir") or "."
    resolved_path = _resolve_target_path(raw_path)
    if not resolved_path or resolved_path == ".":
        resolved_path = os.getcwd()
        
    base_path = Path(resolved_path)
    page_offset = max(0, int(kwargs.get("offset", offset) or 0))
    page_limit = max(1, min(200, int(kwargs.get("limit", limit) or 50)))
    pattern = re.compile(query, re.IGNORECASE)
    
    results = []
    
    def scan_file(file_path):
        file_results = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        file_results.append({
                            "file": str(file_path),
                            "line": i,
                            "content": line.strip()
                        })
        except Exception:
            pass
        return file_results

    try:
        exts = (".py", ".js", ".md", ".txt", ".json", ".xml", ".ini", ".yaml", ".yml", ".ts", ".tsx", ".html", ".css")
        if base_path.is_file():
            target_files = [base_path]
        else:
            target_files = list(iter_workspace_files(root=base_path, suffixes=exts))
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(scan_file, f): f for f in target_files}
            for future in concurrent.futures.as_completed(future_to_file):
                results.extend(future.result())

        results.sort(key=lambda r: (r["file"], r["line"]))
        total_count = len(results)
        if not results:
            return {
                "status": "success",
                "count": 0,
                "offset": page_offset,
                "limit": page_limit,
                "has_more": False,
                "data": [],
                "msg": "Không tìm thấy kết quả nào trên thực địa.",
            }

        paged_data = results[page_offset : page_offset + page_limit]
        has_more = (page_offset + page_limit) < total_count
        report = (
            f"✅ Đã tìm thấy {total_count} kết quả (hiển thị {page_offset + 1}..{page_offset + len(paged_data)}, "
            f"has_more={has_more}). Dưới đây là các vị trí trọng tâm:\n"
        )
        for r in paged_data[:20]:
            report += f"- `{r['file']}:{r['line']}`: {r['content'][:100]}\n"
            
        return {
            "status": "success",
            "count": total_count,
            "offset": page_offset,
            "limit": page_limit,
            "has_more": has_more,
            "data": paged_data,
            "report": report,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}


async def query_repo_map(
    query: str = "",
    file_path: str = "",
    path: str = "",
    include_blast_radius: bool = True,
    max_tokens: int = 700,
    task_id: str = "sys",
    **kwargs,
):
    """🗺️ [AST-REPOMAP TIER 1]: Định vị tức thì symbol (class/def/method), phạm vi dòng [Lstart-Lend] và Blast Radius phụ thuộc ngược."""
    try:
        from core.utils.repo_map import query_repo_map as _query_rm

        q_val = query or kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("q") or ""
        f_val = file_path or path or kwargs.get("TargetFile") or kwargs.get("AbsolutePath") or ""
        inc_blast = bool(kwargs.get("include_blast_radius", include_blast_radius))
        tok_budget = int(kwargs.get("max_tokens", max_tokens) or 700)
        return _query_rm(
            query=str(q_val),
            file_path=str(f_val),
            include_blast_radius=inc_blast,
            max_tokens=tok_budget,
        )
    except Exception as e:
        return {"status": "error", "msg": str(e)}


async def read_stream_window(
    stream_id: str = "",
    start_line: int = 1,
    end_line: int = 100,
    task_id: str = "sys",
    **kwargs,
):
    """📖 [STREAM-WINDOW]: Đọc phân trang cửa sổ dòng [start_line..end_line] từ StreamBufferStore kèm trích dẫn [L...]."""
    try:
        from core.utils.stream_buffer_store import read_stream_window as _read_win

        sid = stream_id or kwargs.get("stream_id") or kwargs.get("path") or kwargs.get("target") or ""
        s_line = int(kwargs.get("StartLine") or kwargs.get("start_line") or start_line or 1)
        e_line = int(kwargs.get("EndLine") or kwargs.get("end_line") or end_line or (s_line + 99))
        return _read_win(stream_id=str(sid), start_line=s_line, end_line=e_line)
    except Exception as e:
        return {"status": "error", "msg": str(e)}


async def search_in_stream(
    stream_id: str = "",
    query: str = "",
    context_lines: int = 2,
    offset: int = 0,
    limit: int = 20,
    task_id: str = "sys",
    **kwargs,
):
    """🔎 [STREAM-SEARCH]: Tìm kiếm có mục tiêu bên trong một stream_id lớn và cập nhật sổ cái độ bao phủ."""
    try:
        from core.utils.stream_buffer_store import search_in_stream as _search_stream

        sid = stream_id or kwargs.get("stream_id") or kwargs.get("path") or kwargs.get("target") or ""
        q_val = query or kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("q") or ""
        ctx = int(kwargs.get("context_lines", context_lines) or 2)
        off = int(kwargs.get("offset", offset) or 0)
        lim = int(kwargs.get("limit", limit) or 20)
        return _search_stream(
            stream_id=str(sid),
            query=str(q_val),
            context_lines=ctx,
            offset=off,
            limit=lim,
        )
    except Exception as e:
        return {"status": "error", "msg": str(e)}



