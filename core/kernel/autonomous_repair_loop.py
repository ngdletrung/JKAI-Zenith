import os
import sys
import time
import subprocess
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("AutonomousRepairLoop")

# 🛡️ [CIRCUIT-BREAKER]: Giới hạn cứng để tránh vòng lặp vô hạn tiêu tốn tài nguyên
_HARD_CAP_MAX_ATTEMPTS = 5


class AutonomousRepairLoop:
    """
    🔄 [AUTONOMOUS-REPAIR-LOOP]: Vòng lặp Tự chủ "Thiếu thì Tạo & Chạy -> Sai thì Sửa -> Chạy lại -> Thẩm định".
    Đây chính là Động cơ Tự sửa lỗi và Thực thi Tự chủ chuẩn Antigravity!
    """
    def __init__(self, max_fix_attempts: int = 3, trace_dir: str = None):
        configured = int(os.getenv("JKAI_REPAIR_MAX_ATTEMPTS", max_fix_attempts))
        self.max_fix_attempts = min(max(configured, 1), _HARD_CAP_MAX_ATTEMPTS)
        default_trace = os.path.join(os.getenv("WORKSPACE_ROOT", r"D:\Docker\JKAI"), "brain", "repair_traces")
        self.trace_dir = trace_dir or default_trace
        self._circuit: Dict[str, float] = {}  # script_path -> last_repair_ts (global circuit breaker)

    def reset_circuit(self):
        """Xoá trạng thái circuit breaker (dùng trong test isolation)."""
        self._circuit.clear()

    def _write_trace(self, task_id: str, script_path: str, entry: dict):
        """Ghi log trace chi tiết mỗi lần tự sửa lỗi vào brain/repair_traces/ để phục vụ đánh giá."""
        try:
            Path(self.trace_dir).mkdir(parents=True, exist_ok=True)
            safe_name = Path(script_path).name.replace(".py", "").replace("/", "_").replace("\\", "_")
            trace_file = Path(self.trace_dir) / f"{safe_name}_{task_id}.json"
            history = []
            if trace_file.exists():
                try:
                    with open(trace_file, "r", encoding="utf-8") as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = []
                except Exception:
                    history = []
            history.append(entry)
            with open(trace_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[REPAIR-TRACE] Failed to write trace: {e}")

    async def execute_and_self_heal(self, script_path: str, task_id: str = "sys") -> dict:
        """
        Chạy tệp Python script. Nếu gặp lỗi, tự động trích xuất Traceback, gọi LLM sửa code, 
        ghi đè tệp và chạy lại đến khi thành công 100% hoặc đạt max attempts (sau đó rollback).
        """
        script_file = Path(script_path)
        if not script_file.exists():
            return {"status": "error", "msg": f"Tệp `{script_path}` không tồn tại."}

        from core.kernel.saga_atomic_healer import saga_atomic_healer
        from core.utils.engine import engine

        # 🛡️ [CIRCUIT-BREAKER]: Chặn sửa lại cùng tệp quá thường xuyên (trong vòng 60 giây)
        now = time.time()
        last_repair = self._circuit.get(str(script_file), 0)
        if now - last_repair < 60:
            return {
                "status": "error",
                "msg": f"Circuit breaker: `{script_file.name}` đã được sửa cách đây {now - last_repair:.0f}s. Bỏ qua để tránh lặp vô hạn."
            }
        self._circuit[str(script_file)] = now

        # 1. Khởi tạo Giao dịch Snapshot bảo vệ tệp gốc
        saga_atomic_healer.begin_transaction(task_id, [str(script_file)])

        last_stderr = ""
        for attempt in range(1, self.max_fix_attempts + 1):
            logger.info("[REPAIR-LOOP-ATTEMPT-%s]: Thực thi tệp `%s` (Lần %s/%s)...", attempt, script_file.name, attempt, self.max_fix_attempts)

            # 2. Thực thi tệp Python
            proc = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True, timeout=60)

            if proc.returncode == 0:
                # NẾU THÀNH CÔNG -> Commit transaction & Dọn dẹp backup .bak
                saga_atomic_healer.commit_transaction(task_id)
                logger.info("[REPAIR-LOOP-SUCCESS]: Tệp `%s` đã chạy thành công sau %s lần thử!", script_file.name, attempt)
                self._write_trace(task_id, str(script_file), {
                    "ts": time.time(), "status": "success", "attempts": attempt,
                    "stdout_tail": proc.stdout[-500:], "stderr": proc.stderr[-500:]
                })
                return {
                    "status": "success",
                    "attempts": attempt,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr
                }

            # NẾU THẤT BẠI -> Thu thập Traceback lỗi
            last_stderr = proc.stderr or proc.stdout
            logger.warning("[REPAIR-LOOP-FAIL-%s]: Tệp `%s` bị lỗi (Exit code: %s). Traceback:\n%s", attempt, script_file.name, proc.returncode, last_stderr[:300])
            self._write_trace(task_id, str(script_file), {
                "ts": time.time(), "status": "failed", "attempt": attempt,
                "exit_code": proc.returncode, "stderr_tail": last_stderr[-500:]
            })

            if attempt == self.max_fix_attempts:
                break

            # 3. Đọc mã nguồn hiện tại
            with open(script_file, "r", encoding="utf-8") as f:
                current_code = f.read()

            # 4. Gọi LLM để Tự Sửa Lỗi (Self-Fixing Code Generation)
            fix_prompt = [
                {"role": "system", "content": "Bạn là Tác tử Tự Sửa Lỗi Python (Code Repair Agent). Hãy đọc mã nguồn bị lỗi và đoạn Traceback exception bên dưới, sau đó sửa lại mã Python HOÀN CHỈNH 100% để sửa lỗi. CHỈ TRẢ VỀ MÃ PYTHON TRONG CODEBLOCK ```python ```."},
                {"role": "user", "content": f"Mã nguồn hiện tại:\n```python\n{current_code}\n```\n\nLỗi Traceback:\n{last_stderr}\n\nHãy sửa lại code Python hoàn chỉnh:"}
            ]

            fixed_code_text = await engine.call_chat(fix_prompt, role="EXECUTOR", task_id=task_id, skip_build_final=True)
            
            # Trích xuất mã Python từ codeblock ```python
            clean_code = self._extract_code_block(fixed_code_text)
            if clean_code and len(clean_code) > 10:
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(clean_code)
                logger.info("[CODE-PATCHED]: Đã áp dụng bản sửa lỗi mới cho `%s`.", script_file.name)

        # NẾU VẪN THẤT BẠI SAU MAX ATTEMPTS -> Rollback khôi phục tệp .bak ban đầu
        saga_atomic_healer.rollback_transaction(task_id, error_detail=last_stderr)
        return {
            "status": "failed",
            "attempts": self.max_fix_attempts,
            "error": f"Không thể tự sửa tệp sau {self.max_fix_attempts} lần. Đã rollback tệp gốc.",
            "last_stderr": last_stderr
        }

    @staticmethod
    def _extract_code_block(text: str) -> str:
        """Trích xuất mã nguồn thuần khiết từ Markdown codeblock."""
        if not text:
            return ""
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()

autonomous_repair_loop = AutonomousRepairLoop()
