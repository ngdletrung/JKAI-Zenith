"""
JKAI Runtime Stability: Resource Governor, Rollback Manager & Recovery Engine
File: core/runtime/governor_and_recovery.py

Triển khai tiêu chuẩn Phase R3:
- ResourceGovernor: Kiểm soát trần tài nguyên (VRAM ceiling, RAM ceiling, token budget, max tool hops).
- RollbackManager: Lưu snapshot mutation và phục hồi trạng thái an toàn khi gặp sự cố, kích hoạt FSM ROLLED_BACK.
- RecoveryEngine: Phân loại lỗi và điều phối tự phục hồi (Retry, Alternative Tool, Degradation) ngăn sập hệ thống.
"""

import time
import os
import shutil
from enum import Enum
from typing import Dict, Any, List, Optional
from core.contracts.canonical_contract import (
    CanonicalState,
    CanonicalFSM,
    ExecutionReceipt,
    PolicyDecision
)


class ErrorSeverity(str, Enum):
    RETRYABLE_TRANSIENT = "RETRYABLE_TRANSIENT"       # Ví dụ: timeout, network glitch, lock tạm thời
    ALTERNATIVE_TOOL_NEEDED = "ALTERNATIVE_TOOL_NEEDED" # Ví dụ: tool thiếu package, dùng fallback
    FATAL_INVARIANT_BREACH = "FATAL_INVARIANT_BREACH"   # Vi phạm bảo mật/chính sách, bắt buộc rollback
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"           # Vượt trần VRAM, Token, Hop


class ResourceGovernor:
    """Kiểm soát trần tài nguyên nghiêm ngặt, ngăn chặn rò rỉ VRAM và vòng lặp vô tận."""
    def __init__(
        self,
        max_hops: int = 10,
        max_vram_mb: float = 8192.0,      # AMD RX 6600 8GB
        max_ram_mb: float = 32768.0,      # Hệ thống 128GB, cấp phát 32GB cho JKAI pool
        max_time_sec: float = 60.0,
        token_budget: int = 4096
    ):
        self.max_hops = max_hops
        self.max_vram_mb = max_vram_mb
        self.max_ram_mb = max_ram_mb
        self.max_time_sec = max_time_sec
        self.token_budget = token_budget

        self.current_hops = 0
        self.used_tokens = 0
        self.start_time = time.time()

    def check_hop_budget(self) -> bool:
        """Kiểm tra số lần gọi công cụ."""
        return self.current_hops < self.max_hops

    def record_hop(self):
        self.current_hops += 1
        if self.current_hops > self.max_hops:
            raise ResourceWarning(f"Vượt quá trần số bước tool ({self.current_hops}/{self.max_hops})!")

    def check_token_budget(self, requested_tokens: int) -> bool:
        return (self.used_tokens + requested_tokens) <= self.token_budget

    def consume_tokens(self, count: int):
        self.used_tokens += count
        if self.used_tokens > self.token_budget:
            raise ResourceWarning(f"Vượt quá ngân sách token ({self.used_tokens}/{self.token_budget})!")

    def check_vram_ceiling(self, current_vram_mb: float) -> bool:
        """Kiểm tra trần VRAM phần cứng (RX 6600 8GB)."""
        return current_vram_mb <= self.max_vram_mb

    def is_timed_out(self) -> bool:
        return (time.time() - self.start_time) > self.max_time_sec

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_hops": self.current_hops,
            "max_hops": self.max_hops,
            "used_tokens": self.used_tokens,
            "token_budget": self.token_budget,
            "elapsed_sec": round(time.time() - self.start_time, 2),
            "max_time_sec": self.max_time_sec
        }


class RollbackManager:
    """Quản lý snapshot workspace và hoàn nguyên trạng thái khi xảy ra lỗi nghiêm trọng."""
    def __init__(self, backup_dir: str = "/tmp/jkai_rollback_snapshots"):
        self.backup_dir = backup_dir
        self.snapshots: Dict[str, Dict[str, str]] = {}  # mission_id -> {filepath: original_content}
        os.makedirs(self.backup_dir, exist_ok=True)

    def snapshot_file(self, mission_id: str, file_path: str, content: Optional[str] = None):
        """Lưu trữ trạng thái tệp trước khi can thiệp (mutation)."""
        if mission_id not in self.snapshots:
            self.snapshots[mission_id] = {}

        if file_path not in self.snapshots[mission_id]:
            if content is not None:
                self.snapshots[mission_id][file_path] = content
            elif os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.snapshots[mission_id][file_path] = f.read()
                except Exception:
                    self.snapshots[mission_id][file_path] = ""
            else:
                # File chưa tồn tại trước đó, đánh dấu để xóa nếu rollback
                self.snapshots[mission_id][file_path] = "__FILE_DID_NOT_EXIST__"

    def execute_rollback(self, mission_id: str, fsm: Optional[CanonicalFSM] = None) -> List[str]:
        """Khôi phục toàn bộ các tệp bị ảnh hưởng về trạng thái ban đầu."""
        restored = []
        if mission_id in self.snapshots:
            for file_path, original_content in self.snapshots[mission_id].items():
                try:
                    if original_content == "__FILE_DID_NOT_EXIST__":
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            restored.append(f"REMOVED_NEW_FILE:{file_path}")
                    else:
                        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(original_content)
                        restored.append(f"RESTORED:{file_path}")
                except Exception as e:
                    restored.append(f"ERROR_RESTORING:{file_path}:{str(e)}")

        # Chuyển FSM sang ROLLED_BACK nếu có
        if fsm and fsm.current_state not in [CanonicalState.COMPLETE, CanonicalState.ROLLED_BACK]:
            try:
                fsm.transition(CanonicalState.ROLLED_BACK, actor="KERNEL", evidence=f"Rollback {len(restored)} files")
            except Exception as e:
                pass

        return restored


class RecoveryEngine:
    """Động cơ chẩn đoán lỗi và đưa ra hành động khắc phục tự động."""
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_counts: Dict[str, int] = {}

    def classify_error(self, receipt: ExecutionReceipt) -> ErrorSeverity:
        err = receipt.error_message or ""
        lower_err = err.lower()

        if "timeout" in lower_err or "connection reset" in lower_err or "rate limit" in lower_err:
            return ErrorSeverity.RETRYABLE_TRANSIENT
        if "no module named" in lower_err or "command not found" in lower_err or "not supported" in lower_err:
            return ErrorSeverity.ALTERNATIVE_TOOL_NEEDED
        if "vram" in lower_err or "out of memory" in lower_err or "quota exceeded" in lower_err:
            return ErrorSeverity.RESOURCE_EXHAUSTED
        if "permission denied" in lower_err or "policy violation" in lower_err or "invariant" in lower_err:
            return ErrorSeverity.FATAL_INVARIANT_BREACH

        return ErrorSeverity.RETRYABLE_TRANSIENT

    def determine_strategy(self, mission_id: str, receipt: ExecutionReceipt) -> Dict[str, Any]:
        """Xác định phương án cứu vãn nhiệm vụ."""
        severity = self.classify_error(receipt)
        current_retry = self.retry_counts.get(mission_id, 0)

        if severity == ErrorSeverity.RETRYABLE_TRANSIENT:
            if current_retry < self.max_retries:
                self.retry_counts[mission_id] = current_retry + 1
                return {
                    "action": "RETRY",
                    "attempt": self.retry_counts[mission_id],
                    "delay_sec": 1.5 * (self.retry_counts[mission_id]),
                    "reason": f"Thử lại lỗi tạm thời ({receipt.error_message})"
                }
            else:
                return {
                    "action": "FAIL_AND_ROLLBACK",
                    "reason": f"Đã vượt quá số lần thử lại ({self.max_retries}) mà vẫn lỗi."
                }

        elif severity == ErrorSeverity.ALTERNATIVE_TOOL_NEEDED:
            # Fallback tool routing
            tool_fallbacks = {
                "browser_scrape": "fast_web_reader",
                "BROWSER_CONTROL": "HTTP_EXECUTOR_FALLBACK",
                "bash_exec": "safe_subproc_exec"
            }
            fallback = tool_fallbacks.get(receipt.tool_name, "clarify_or_report")
            return {
                "action": "FALLBACK_TOOL",
                "fallback_tool": fallback,
                "reason": f"Công cụ {receipt.tool_name} gặp lỗi cấu hình: {receipt.error_message}"
            }

        elif severity == ErrorSeverity.RESOURCE_EXHAUSTED:
            return {
                "action": "DEGRADE_AND_EVICT",
                "evict_model_cache": True,
                "reason": "Giải phóng VRAM/RAM và chuyển sang chế độ suy luận nhẹ."
            }

        else:  # FATAL_INVARIANT_BREACH
            return {
                "action": "IMMEDIATE_ROLLBACK_AND_HALT",
                "reason": f"Vi phạm bất biến hoặc chính sách bảo mật: {receipt.error_message}"
            }
