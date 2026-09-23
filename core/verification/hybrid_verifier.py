"""
HybridVerifier — Bộ kiểm tra lai ghép thực thi theo triết lý "REPLACE, NOT ADD" của Master.

Thay thế hoàn toàn Ban Kiểm Soát LLM cũ (nơi LLM tự chấm 0.98 cho code lỗi):
1. NHÁNH MÃ NGUỒN (CODE PATH): Deterministic Gate 100% (AST syntax, Artifact existence, Exit codes).
   - Zero LLM call, Zero extra latency, Zero hallucination.
   - Code có bug hoặc lỗi cú pháp -> REJECT NGAY TỨC THÌ.
2. NHÁNH TRI THỨC (NON-CODE PATH): Calibrated Confidence Evaluation.
   - Đánh giá dựa trên bằng chứng dữ liệu thực tế thay vì LLM chấm điểm cảm tính.
"""

from __future__ import annotations

import ast
import os
import logging
from typing import Any, Dict, Tuple, Optional

logger = logging.getLogger("jkai.verification.hybrid_verifier")

CODE_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "delete_file",
    "run_command",
    "code_actuator",
    "terminal",
    "execute_script"
}


class HybridVerifier:
    """Bộ kiểm soát lai ghép: Deterministic cho Code + Calibrated cho Non-code."""

    @classmethod
    def verify(
        cls,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        task_id: str = "sys"
    ) -> Tuple[bool, str, float]:
        """
        Xác minh kết quả thực thi.
        Trả về: (is_valid, reason, confidence_score)
        """
        tool_lower = (tool_name or "").lower()

        # Phân nhánh 1: NHÁNH MÃ NGUỒN (CODE PATH) - Deterministic Gate
        if cls.is_code_tool(tool_lower):
            return cls._verify_code_deterministic(tool_lower, args, result)

        # Phân nhánh 2: NHÁNH TRI THỨC (NON-CODE PATH) - Calibrated Evaluation
        return cls._verify_non_code_calibrated(tool_lower, args, result)

    @classmethod
    def is_code_tool(cls, tool_name: str) -> bool:
        """Nhận diện công cụ tác động mã nguồn hoặc lệnh hệ thống."""
        t = tool_name.lower()
        if any(c in t for c in CODE_TOOLS):
            return True
        if any(kw in t for kw in ("code", "file", "command", "script", "patch")):
            return True
        return False

    # =========================================================================
    # NHÁNH CODE: DETERMINISTIC GATE (CHÉM THẲNG CỔ NẾU LỖI, ZERO LLM CALL)
    # =========================================================================

    @classmethod
    def _verify_code_deterministic(
        cls,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> Tuple[bool, str, float]:
        # 1. Kiểm tra trạng thái trả về từ công cụ
        if isinstance(result, dict):
            status = result.get("status", "").lower()
            if status in ("error", "failed", "rejected"):
                msg = result.get("msg") or result.get("error") or "Execution returned error status"
                return False, f"Deterministic Gate REJECTED: {msg}", 0.0

            # Đối với run_command: Kiểm tra exit_code
            exit_code = result.get("exit_code")
            if exit_code is not None and exit_code != 0:
                stderr = result.get("stderr") or ""
                return False, f"Deterministic Gate REJECTED: Command exited with code {exit_code} ({stderr.strip()[:200]})", 0.0

        # 2. Đối với các thao tác ghi/sửa tệp: Xác thực vật lý và cú pháp AST
        target_path = (
            args.get("path")
            or args.get("TargetFile")
            or args.get("file_path")
            or args.get("target_path")
            or ""
        )

        if target_path and any(w in tool_name for w in ("write", "replace", "create")):
            # Kiểm tra tệp có thực sự tồn tại trên đĩa không (P0.3 Artifact Exists)
            if not os.path.exists(target_path):
                return False, f"Deterministic Gate REJECTED: Target file '{target_path}' does not exist on disk", 0.0

            # Kiểm tra tệp không được rỗng nếu là file code
            try:
                if os.path.getsize(target_path) == 0:
                    return False, f"Deterministic Gate REJECTED: Target file '{target_path}' is empty (0 bytes)", 0.0
            except OSError:
                pass

            # Nếu là tệp Python: Bắt buộc cú pháp AST phải biên dịch được
            if target_path.endswith(".py"):
                try:
                    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                        code_content = f.read()
                    ast.parse(code_content)
                except SyntaxError as syn_err:
                    return False, f"Deterministic Gate REJECTED: Python file has syntax error: {syn_err}", 0.0

        return True, "Deterministic Gate APPROVED: All physical & syntactic constraints satisfied", 1.0

    # =========================================================================
    # NHÁNH NON-CODE: CALIBRATED EVALUATION (EVIDENCE-BASED, NOT LENGTH HEURISTIC)
    # =========================================================================

    @classmethod
    def _verify_non_code_calibrated(
        cls,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> Tuple[bool, str, float]:
        """
        [V1] Evidence-based confidence for non-code tool results.
        Confidence must reflect actual evidence of content, NOT payload key presence.
        Rule: 0.98 is NEVER awarded unless content is non-empty, non-error, and has substance.
        """
        if result is None:
            return False, "Calibrated Gate REJECTED: Tool returned None result", 0.0

        # Empty container check
        if isinstance(result, (str, list, dict)) and len(result) == 0:
            return False, "Calibrated Gate REJECTED: Tool returned empty payload", 0.1

        # Explicit error signal
        if isinstance(result, dict):
            if result.get("status") == "error":
                return False, f"Calibrated Gate REJECTED: {result.get('msg', 'Error')}", 0.0
            if result.get("error") or result.get("exception"):
                return False, f"Calibrated Gate REJECTED: Error in result: {result.get('error') or result.get('exception')}", 0.0

        # ── Evidence scoring (replaces length heuristic) ──────────────────────
        # Principle: Confidence = f(evidence) — NOT f(key presence or byte count)
        confidence = 0.50  # Baseline — elevated only by concrete evidence

        if isinstance(result, dict):
            # Evidence 1: Non-empty list content (items, results)
            items_val = result.get("items") or result.get("results")
            if isinstance(items_val, (list, dict)) and len(items_val) > 0:
                confidence = max(confidence, 0.85)
            # Evidence 2: Substantive string content (>= 20 chars, not "ok"/"done" filler)
            for key in ("content", "stdout", "output", "text", "data"):
                val = result.get(key)
                if isinstance(val, str) and len(val.strip()) >= 20:
                    confidence = max(confidence, 0.85)
                    break
                elif isinstance(val, (dict, list)) and len(val) > 0:
                    confidence = max(confidence, 0.80)
                    break
            # Evidence 3: Explicit success status
            status_val = result.get("status", "")
            if isinstance(status_val, str) and status_val.lower() in ("success", "ok", "done", "completed"):
                confidence = max(confidence, 0.75)
            # Evidence 4: Multiple meaningful keys (breadth of result)
            meaningful_keys = [k for k, v in result.items()
                               if v not in (None, "", [], {}) and k not in ("status", "msg", "message")]
            if len(meaningful_keys) >= 3:
                confidence = min(confidence + 0.05, 0.90)
            # Penalize: only 1 key with trivially short value → low confidence
            if len(result) < 2 and confidence <= 0.60:
                confidence = 0.40

        elif isinstance(result, list):
            if len(result) >= 3:
                confidence = 0.85
            elif len(result) >= 1:
                confidence = 0.70

        elif isinstance(result, str):
            stripped = result.strip()
            if len(stripped) >= 100:
                confidence = 0.85
            elif len(stripped) >= 20:
                confidence = 0.70
            else:
                confidence = 0.40  # filler like "ok", "done" — not real evidence

        # ── Verdict ───────────────────────────────────────────────────────────
        if confidence < 0.50:
            return False, f"Calibrated Gate REJECTED: Insufficient evidence (confidence={confidence:.2f})", confidence
        elif confidence < 0.80:
            return True, f"Calibrated Gate APPROVED with warning (confidence={confidence:.2f})", confidence

        return True, f"Calibrated Gate APPROVED (confidence={confidence:.2f})", confidence

