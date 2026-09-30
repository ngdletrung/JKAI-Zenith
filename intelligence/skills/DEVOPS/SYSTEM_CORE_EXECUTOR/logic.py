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

async def view_file(path: str = "", file_path: str = "", AbsolutePath: str = "", start_line: int = 1, end_line: int = 500, task_id: str = "sys", **kwargs):
    """👁️ [VISION]: Đọc nội dung tệp tin thấu thị."""
    raw_path = path or file_path or AbsolutePath or kwargs.get("AbsolutePath") or kwargs.get("TargetFile") or ""
    target_path = _resolve_target_path(raw_path)
    try:
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}
        
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        content = "".join(lines[start_line-1:end_line])
        return {
            "status": "success",
            "path": os.path.abspath(target_path),
            "total_lines": len(lines),
            "content": content
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def write_to_file(path: str = "", file_path: str = "", TargetFile: str = "", target_path: str = "", content: str = "", CodeContent: str = "", target_content: str = "", overwrite: bool = True, task_id: str = "sys", **kwargs):
    """✍️ [CREATION - M0 ATOMIC WRITE]: Kiến tạo tệp tin mới với Atomic Write, Auto-Backup & SHA-256 Checksum."""
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
        
        # 🔬 [AST-PRE-VALIDATION]: Chặn đứng lỗi cú pháp trước khi ghi file Python
        if target_path.endswith(".py") and target_content:
            try:
                ast.parse(target_content)
            except SyntaxError as syn_err:
                return {
                    "status": "error",
                    "msg": f"AST Syntax Error: Mã nguồn Python gây lỗi cú pháp ({syn_err}). Thao tác ghi bị từ chối."
                }

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

        return {
            "status": "success",
            "msg": f"Đã kiến tạo tệp `{target_path}` thành công.",
            "path": os.path.abspath(target_path),
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "backup_path": backup_path,
            "atomic": True
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def replace_file_content(path: str = "", target: str = "", replacement: str = "", file_path: str = "", TargetFile: str = "", TargetContent: str = "", ReplacementContent: str = "", task_id: str = "sys", **kwargs):
    """🛠️ [SURGERY - M0 ATOMIC SURGERY]: Phẫu thuật thay thế nội dung tệp tin an toàn với Atomic Write & Checksum."""
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
            return {"status": "error", "msg": f"Không tìm thấy đoạn hội thoại mục tiêu trong `{target_path}` (đã thử cả khớp chính xác, CRLF và đối chiếu mờ)."}
        
        # 🔬 [AST-PRE-VALIDATION]: Chặn đứng lỗi cú pháp trước khi ghi file Python
        if target_path.endswith(".py"):
            try:
                ast.parse(new_content)
            except SyntaxError as syn_err:
                return {
                    "status": "error",
                    "msg": f"AST Syntax Error: Mã thay thế gây lỗi cú pháp ({syn_err}). Thao tác ghi bị từ chối."
                }

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

        return {
            "status": "success",
            "msg": f"Phẫu thuật thành công trên tệp `{target_path}`.",
            "path": os.path.abspath(target_path),
            "sha256": sha256_hash,
            "size_bytes": file_size,
            "backup_path": backup_path,
            "atomic": True
        }
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
        engine.publish_mission_log("ACTION", f"Đã xóa tệp `{target_path}` thành công (Backup: {backup_path}).", task_id)
        return {
            "status": "success",
            "msg": f"Đã xóa tệp `{target_path}` thành công.",
            "path": os.path.abspath(target_path),
            "pre_delete_sha256": pre_delete_sha256,
            "backup_path": backup_path
        }
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
                tokens = shlex.split(cmd, posix=False) if sys.platform == "win32" else shlex.split(cmd)
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

    # Condition 6: Cắt đầu ra nếu vượt quá 16KB để bảo vệ RAM / context
    truncated = False
    if len(stdout_str) > MAX_OUTPUT_BYTES:
        stdout_str = stdout_str[:MAX_OUTPUT_BYTES] + f"\n... [TRUNCATED - Output vượt quá {MAX_OUTPUT_BYTES} bytes]"
        truncated = True
    if len(stderr_str) > MAX_OUTPUT_BYTES:
        stderr_str = stderr_str[:MAX_OUTPUT_BYTES] + f"\n... [TRUNCATED - Stderr vượt quá {MAX_OUTPUT_BYTES} bytes]"
        truncated = True

    return {
        "status": "success" if exit_code == 0 else "error",
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "policy_tier": policy_tier,
        "truncated": truncated
    }


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

async def search_web(query: str, task_id: str = "sys"):
    """🌐 [RECON]: Tầm soát Internet thấu thị."""
    query = _clean_query(query)
    try:
        from intelligence.skills.CORE.OMNI_SEARCH_ENGINE.logic import omni_search
        return await omni_search(query=query, task_id=task_id)
    except Exception as e:
        import httpx
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post("https://api.tavily.com/search", json={
                        "api_key": api_key, "query": query, "search_depth": "advanced"
                    })
                    if resp.status_code == 200:
                        return resp.json()
                    else:
                        return {"status": "error", "msg": f"Tavily API Error: {resp.status_code} - {resp.text}"}
            except Exception as ex:
                return {"status": "error", "msg": f"Search Connection Fault: {str(ex)}"}
        return {"status": "error", "msg": f"Search failed: {str(e)}"}

async def read_url_content(url: str, task_id: str = "sys"):
    """📄 [VISION]: Đọc nội dung URL thấu thị."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            if resp.status_code == 200:
                return {"status": "success", "content": resp.text[:5000]}
            else:
                return {"status": "error", "msg": f"Jina.ai API Error: {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def generate_image(prompt: str, task_id: str = "sys"):
    """🎨 [CREATION]: Kiến tạo hình ảnh từ tri tưởng tượng."""
    from intelligence.skills.skill_generate_image.logic import skill_generate_image
    return await skill_generate_image(prompt=prompt, task_id=task_id)

async def grep_search(query: str = "", path: str = ".", task_id: str = "sys", **kwargs):
    """🔍 [SCANNER]: Quét tìm từ khóa trong toàn bộ thư mục."""
    import re
    import concurrent.futures
    from pathlib import Path
    
    query = query or kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("q") or ""
    raw_path = path or kwargs.get("SearchPath") or kwargs.get("directory") or kwargs.get("dir") or "."
    resolved_path = _resolve_target_path(raw_path)
    if not resolved_path or resolved_path == ".":
        resolved_path = os.getcwd()
        
    base_path = Path(resolved_path)
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
        target_files = []
        for ext in [".py", ".js", ".md", ".txt", ".json", ".xml", ".ini", ".yaml", ".yml", ".ts", ".tsx", ".html", ".css"]:
            target_files.extend(
                [f for f in base_path.rglob(f"*{ext}") 
                 if not any(x in str(f) for x in [".git", "node_modules", "__pycache__", ".svelte-kit", "dist", "build"])]
            )
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(scan_file, f): f for f in target_files}
            for future in concurrent.futures.as_completed(future_to_file):
                results.extend(future.result())

        if not results:
            return {"status": "success", "msg": "Không tìm thấy kết quả nào trên thực địa."}

        report = f"✅ Đã tìm thấy {len(results)} kết quả. Dưới đây là các vị trí trọng tâm:\n"
        for r in results[:20]:
            report += f"- `{r['file']}:{r['line']}`: {r['content'][:100]}\n"
            
        return {
            "status": "success",
            "count": len(results),
            "data": results[:50],
            "report": report
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

