# -*- coding: utf-8 -*-
"""
core/utils/smart_patch_engine.py
🏛️ Multi-Format Smart Patch Engine (Inspired by aider & Cortex)
Part of JKAI Zenith Sovereign OS — SDS v28.24.0

Solves the classic Small LLM (3B/4B) Code Surgery bottleneck:
1. Tier 1 (Exact Match): Ultra-fast exact substring match.
2. Tier 2 (Whitespace & Indentation Normalized Match): Tolerates tab/space mismatches,
   trailing whitespace, and relative indent variations without corrupting surrounding code.
3. Tier 3 (Unified Diff / Patch Format): Parses standard unified diffs (--- / +++ / @@).
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import Optional, Tuple, List

logger = logging.getLogger("JKAI.SmartPatchEngine")


class PatchResult:
    def __init__(
        self,
        success: bool,
        content: str,
        tier_used: int,
        match_start_line: Optional[int] = None,
        match_end_line: Optional[int] = None,
        message: str = "",
    ):
        self.success = success
        self.content = content
        self.tier_used = tier_used
        self.match_start_line = match_start_line
        self.match_end_line = match_end_line
        self.message = message


class SmartPatchEngine:
    """
    3-Tier Deterministic Code Patch Engine.
    Guarantees surgical precision and zero placeholder tolerance.
    """

    @classmethod
    def apply_patch(
        cls,
        original_text: str,
        target_content: str,
        replacement_content: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        allow_multiple: bool = False,
    ) -> PatchResult:
        """
        Applies patch using 3-tier progressive resolution:
        Tier 1 (Exact) -> Tier 2 (Whitespace Normalized) -> Tier 3 (Unified Diff).
        """
        if not original_text:
            return PatchResult(False, original_text, 0, message="Tệp rỗng hoặc không có nội dung.")

        # -------------------------------------------------------------
        # Tier 3 Pre-check: Unified Diff Format Detection
        # -------------------------------------------------------------
        if cls._is_unified_diff(target_content) or cls._is_unified_diff(replacement_content):
            diff_text = replacement_content if cls._is_unified_diff(replacement_content) else target_content
            res_diff = cls._apply_unified_diff(original_text, diff_text)
            if res_diff.success:
                return res_diff

        # -------------------------------------------------------------
        # Tier 1: Exact Substring Matching
        # -------------------------------------------------------------
        if target_content in original_text:
            count = original_text.count(target_content)
            if count > 1 and not allow_multiple:
                # If multiple and line range provided, try restricting
                if start_line is not None and end_line is not None:
                    lines = original_text.splitlines(keepends=True)
                    s_idx = max(0, start_line - 1)
                    e_idx = min(len(lines), end_line)
                    sub_text = "".join(lines[s_idx:e_idx])
                    if target_content in sub_text and sub_text.count(target_content) == 1:
                        new_sub = sub_text.replace(target_content, replacement_content, 1)
                        new_text = "".join(lines[:s_idx]) + new_sub + "".join(lines[e_idx:])
                        return PatchResult(
                            success=True,
                            content=new_text,
                            tier_used=1,
                            match_start_line=start_line,
                            match_end_line=end_line,
                            message="Khớp chính xác (Tier 1) trong phạm vi dòng giới hạn.",
                        )
                return PatchResult(
                    success=False,
                    content=original_text,
                    tier_used=1,
                    message=f"Đoạn mã mục tiêu xuất hiện {count} lần trong tệp. Hãy thu hẹp phạm vi dòng hoặc đặt allow_multiple=True.",
                )

            # Unique match or multiple allowed
            new_text = original_text.replace(
                target_content,
                replacement_content,
                count if allow_multiple else 1
            )
            return PatchResult(
                success=True,
                content=new_text,
                tier_used=1,
                message="Khớp chính xác từng ký tự (Tier 1 Exact Match).",
            )

        # -------------------------------------------------------------
        # Tier 2: Whitespace & Indentation Normalized Line Matching
        # -------------------------------------------------------------
        res_t2 = cls._apply_whitespace_normalized(
            original_text,
            target_content,
            replacement_content,
            start_line,
            end_line,
        )
        if res_t2.success:
            return res_t2

        return PatchResult(
            success=False,
            content=original_text,
            tier_used=0,
            message="Không tìm thấy đoạn mã cần thay thế (Đã thử cả Exact Match và Whitespace-Normalized Match).",
        )

    @classmethod
    def _apply_whitespace_normalized(
        cls,
        original_text: str,
        target_content: str,
        replacement_content: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> PatchResult:
        """
        Khớp dòng dựa trên nội dung đã chuẩn hóa khoảng trắng (strip / normalized spaces).
        Tự động bảo toàn độ thụt lề gốc của tệp mã nguồn.
        """
        orig_lines = original_text.splitlines(keepends=True)
        tgt_lines = target_content.splitlines()

        if not tgt_lines:
            return PatchResult(False, original_text, 2, message="Target content rỗng.")

        # Chuẩn hóa target: loại bỏ dòng trống đầu/cuối và strip
        clean_tgt = [line.strip() for line in tgt_lines if line.strip()]
        if not clean_tgt:
            return PatchResult(False, original_text, 2, message="Target chỉ chứa khoảng trắng.")

        search_start = max(0, (start_line - 1)) if start_line is not None else 0
        search_end = min(len(orig_lines), end_line) if end_line is not None else len(orig_lines)

        matches = []
        n_clean = len(clean_tgt)

        for i in range(search_start, search_end):
            # Check if subsequence of stripped non-empty lines matches clean_tgt
            window_orig_indices = []
            curr_idx = i
            while curr_idx < search_end and len(window_orig_indices) < n_clean:
                line_str = orig_lines[curr_idx].strip()
                if line_str:
                    expected = clean_tgt[len(window_orig_indices)]
                    if line_str == expected:
                        window_orig_indices.append(curr_idx)
                    else:
                        break
                curr_idx += 1

            if len(window_orig_indices) == n_clean:
                matches.append((window_orig_indices[0], window_orig_indices[-1]))

        if not matches:
            return PatchResult(False, original_text, 2, message="Không tìm thấy khối tương đồng khoảng trắng.")

        if len(matches) > 1:
            return PatchResult(
                False,
                original_text,
                2,
                message=f"Tìm thấy {len(matches)} khối mã khớp tương đối. Cần chỉ định start_line và end_line cụ thể.",
            )

        match_s, match_e = matches[0]

        # Xác định độ thụt lề cơ sở của dòng đầu tiên trong khối khớp
        first_orig_line = orig_lines[match_s]
        base_indent = ""
        m_indent = re.match(r"^(\s*)", first_orig_line)
        if m_indent:
            base_indent = m_indent.group(1)

        # Tính toán độ thụt lề cơ sở trong replacement
        repl_lines = replacement_content.splitlines()
        first_repl_indent = ""
        for r_l in repl_lines:
            if r_l.strip():
                m_r = re.match(r"^(\s*)", r_l)
                if m_r:
                    first_repl_indent = m_r.group(1)
                break

        # Điều chỉnh lại thụt lề cho replacement lines để khớp tệp gốc
        adapted_repl_lines = []
        for r_l in repl_lines:
            if not r_l.strip():
                adapted_repl_lines.append("\n")
            else:
                if r_l.startswith(first_repl_indent):
                    adjusted = base_indent + r_l[len(first_repl_indent):]
                else:
                    adjusted = base_indent + r_l.lstrip()
                adapted_repl_lines.append(adjusted + "\n")

        # Ghép lại nội dung tệp
        new_lines = (
            orig_lines[:match_s]
            + [cls._preserve_line_endings("".join(adapted_repl_lines), orig_lines[match_s])]
            + orig_lines[match_e + 1:]
        )
        final_text = "".join(new_lines)

        return PatchResult(
            success=True,
            content=final_text,
            tier_used=2,
            match_start_line=match_s + 1,
            match_end_line=match_e + 1,
            message=f"Khớp tương đối và bảo toàn thụt lề (Tier 2 Whitespace-Normalized: dòng {match_s + 1} -> {match_e + 1}).",
        )

    @classmethod
    def _is_unified_diff(cls, text: str) -> bool:
        if not text:
            return False
        return "@@ " in text or ("--- " in text and "+++ " in text)

    @classmethod
    def _apply_unified_diff(cls, original_text: str, diff_text: str) -> PatchResult:
        """Áp dụng unified diff đơn giản."""
        try:
            orig_lines = original_text.splitlines()
            diff_lines = diff_text.splitlines()

            # Trích xuất các dòng -, + và context từ diff block
            hunk_lines = [l for l in diff_lines if l.startswith(("-", "+", " ")) and not l.startswith(("---", "+++"))]
            if not hunk_lines:
                return PatchResult(False, original_text, 3, message="Diff không chứa dòng thay đổi hợp lệ.")

            removals = [l[1:].strip() for l in hunk_lines if l.startswith("-") and l[1:].strip()]
            additions = [l[1:] for l in hunk_lines if l.startswith("+")]

            target_block = "\n".join(removals)
            repl_block = "\n".join(additions)

            # Tái sử dụng matching cho khối đã trích xuất từ diff
            return cls.apply_patch(original_text, target_block, repl_block)
        except Exception as e:
            return PatchResult(False, original_text, 3, message=f"Lỗi phân tích unified diff: {e}")

    @classmethod
    def _preserve_line_endings(cls, new_text: str, reference_line: str) -> str:
        if reference_line.endswith("\r\n"):
            return new_text.replace("\r\n", "\n").replace("\n", "\r\n")
        return new_text.replace("\r\n", "\n")
