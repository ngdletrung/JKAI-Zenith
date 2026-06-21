import os
import re
import asyncio
import logging
from typing import List, Dict

logger = logging.getLogger("JKAI.SecurityMonitor")

class SecurityMonitor:
    """
    🛡️ JKAI ZENITH: HỆ THỐNG GIÁM SÁT BẢO MẬT CHỦ ĐỘNG v1.0
    Nhiệm vụ: Phát hiện rò rỉ API Key và kiểm tra tính toàn vẹn của hệ thống.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        # Các mẫu nhận diện API Key phổ biến
        self.secret_patterns = {
            "GEMINI": re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
            "OPENAI": re.compile(r"sk-[a-zA-Z0-9]{48}"),
            "DEEPSEEK": re.compile(r"sk-[a-z0-9]{32}"),
            "ANTHROPIC": re.compile(r"sk-ant-api03-[a-zA-Z0-9_-]{93}"),
            "TAVILY": re.compile(r"tvly-[a-zA-Z0-9]{32}")
        }
        self.ignored_files = [".gitignore", "node_modules", ".git", "venv", ".venv", "__pycache__"]

    async def scan_for_leaks(self) -> List[Dict]:
        """🔍 Quét toàn bộ workspace để tìm các bí mật bị lộ."""
        leaks = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Bỏ qua các thư mục không cần thiết
            dirs[:] = [d for d in dirs if d not in self.ignored_files]
            
            for file in files:
                if file.endswith((".py", ".md", ".json", ".txt", ".env", ".log")):
                    file_path = os.path.join(root, file)
                    # Không quét chính file này và các file trong vault (vì vault được coi là an toàn)
                    if "security_monitor.py" in file_path or "intelligence/vault" in file_path:
                        continue
                        
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for key_type, pattern in self.secret_patterns.items():
                                matches = pattern.findall(content)
                                if matches:
                                    # Kiểm tra xem file này có được ignore bởi git không
                                    # (Đây là bước quan trọng nhất để cảnh báo leak lên GitHub)
                                    is_ignored = await self._is_git_ignored(file_path)
                                    if not is_ignored:
                                        leaks.append({
                                            "file": file_path,
                                            "type": key_type,
                                            "count": len(matches),
                                            "severity": "CRITICAL"
                                        })
                    except Exception as e:
                        logger.error(f"❌ Error scanning {file_path}: {e}")
        return leaks

    async def _is_git_ignored(self, file_path: str) -> bool:
        """Kiểm tra xem một file có bị Git bỏ qua không."""
        try:
            rel_path = os.path.relpath(file_path, self.workspace_root)
            process = await asyncio.create_subprocess_exec(
                "git", "check-ignore", rel_path,
                cwd=self.workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def run_audit_loop(self):
        """Vòng lặp giám sát liên tục."""
        while True:
            logger.info("🛡️ Starting security audit scan...")
            leaks = await self.scan_for_leaks()
            if leaks:
                self._report_leaks(leaks)
            await asyncio.sleep(3600)  # Quét mỗi giờ một lần

    def _report_leaks(self, leaks: List[Dict]):
        """Báo cáo các rò rỉ phát hiện được."""
        msg = "⚠️ [SECURITY-ALERT]: Phát hiện rò rỉ API Key trong các file KHÔNG được Git bảo vệ!\n"
        for leak in leaks:
            msg += f"- File: `{leak['file']}` | Loại: `{leak['type']}` | Mức độ: `{leak['severity']}`\n"
        
        # Ở đây sẽ gọi đến hệ thống thông báo của Brain (ví dụ: publish_mission_log)
        print(msg)
        # Giả định có cơ chế notify Master ở đây
        
if __name__ == "__main__":
    import sys
    # Force UTF-8 for Windows console
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    ws = os.getenv("WORKSPACE_ROOT", "d:/Docker/JKAI")
    monitor = SecurityMonitor(ws)
    print(f"[SCAN-START]: Bat dau quet bao mat tai {ws}...")
    leaks = asyncio.run(monitor.scan_for_leaks())
    if leaks:
        monitor._report_leaks(leaks)
    else:
        print("[CLEAN]: Khong phat hien ro ri API Key nao trong cac file cong khai.")
