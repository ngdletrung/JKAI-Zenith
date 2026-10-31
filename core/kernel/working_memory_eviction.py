# -*- coding: utf-8 -*-
"""
Meta CCA Working Memory Eviction Engine (Slice 1 of 5 Secret Weapons).
Trục xuất nội dung tệp thô khỏi Working Memory, chỉ lưu trữ Symbol Skeleton
(danh sách class, phương thức, số dòng, mã băm SHA-256) để giải phóng 70% Token Budget,
ngăn chặn Attention Degradation trên mô hình nhỏ (Qwen 3B).
"""

import ast
import hashlib
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SymbolSkeleton(BaseModel):
    """Bộ khung ký hiệu trích xuất từ tệp mã nguồn để lưu giữ trong Working Memory."""
    file_path: str
    line_count: int
    sha256_16: str
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    key_symbols: List[str] = Field(default_factory=list)
    raw_size_bytes: int = 0
    skeleton_size_tokens_est: int = 0


class WorkingMemoryEvictionEngine:
    """Động cơ quản lý trục xuất Working Memory theo triết lý Meta Confucius Code Agent (CCA)."""

    def __init__(self, cache_dir: str = "data/cache/evicted_files"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._skeletons: Dict[str, SymbolSkeleton] = {}

    def extract_skeleton(self, file_path: str, content: str) -> SymbolSkeleton:
        """Trích xuất Symbol Skeleton từ nội dung văn bản mà không làm mất thông tin cấu trúc."""
        lines = content.splitlines()
        line_count = len(lines)
        sha16 = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        classes = []
        functions = []

        # Thử parse bằng AST Python nếu là file .py
        if file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
            except Exception:
                # Fallback regex nếu AST parse gặp lỗi cú pháp
                classes = re.findall(r"^\s*class\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
                functions = re.findall(r"^\s*(?:async\s+)?def\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
        else:
            classes = re.findall(r"^\s*class\s+([A-Za-z0-9_]+)", content, re.MULTILINE)
            functions = re.findall(r"^\s*(?:function|def)\s+([A-Za-z0-9_]+)", content, re.MULTILINE)

        # Trích xuất các symbol đặc biệt (hằng số, enums)
        key_symbols = re.findall(r"^\s*([A-Z0-9_]{3,})\s*=", content, re.MULTILINE)

        skeleton = SymbolSkeleton(
            file_path=file_path.replace("\\", "/"),
            line_count=line_count,
            sha256_16=sha16,
            classes=sorted(list(set(classes))),
            functions=sorted(list(set(functions))),
            key_symbols=sorted(list(set(key_symbols)))[:10],
            raw_size_bytes=len(content.encode("utf-8")),
            skeleton_size_tokens_est=max(20, (len(classes) + len(functions)) * 4),
        )
        self._skeletons[skeleton.file_path] = skeleton
        return skeleton

    def evict_and_render_observation(self, file_path: str, content: str, max_retain_lines: int = 15) -> str:
        """
        Trục xuất nội dung tệp thô khỏi observation:
        Lưu tệp đầy đủ vào cache cục bộ, và chỉ trả về Symbol Skeleton cô đọng
        kèm vài dòng mở đầu để mô hình nắm được bối cảnh mà không ngốn token.
        """
        norm_path = file_path.replace("\\", "/")
        skeleton = self.extract_skeleton(norm_path, content)

        # Lưu bản thô an toàn vào cache
        cache_key = hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:12]
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.raw")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

        # Hiển thị vài dòng đầu mẫu
        lines = content.splitlines()
        preview = "\n".join(lines[:max_retain_lines])

        class_str = ", ".join(skeleton.classes) if skeleton.classes else "None"
        fn_str = ", ".join(skeleton.functions[:15]) if skeleton.functions else "None"
        if len(skeleton.functions) > 15:
            fn_str += f" (+{len(skeleton.functions) - 15} methods)"

        obs = (
            f"📄 [SYMBOL-SKELETON (Working Memory Eviction Active)]: `{norm_path}`\n"
            f"  • Tổng số dòng: {skeleton.line_count} dòng | SHA-256 (16 hex): {skeleton.sha256_16}\n"
            f"  • Classes định nghĩa: [{class_str}]\n"
            f"  • Functions/Methods: [{fn_str}]\n"
            f"  • Tiết kiệm token: Giảm từ {skeleton.raw_size_bytes} bytes thô xuống {skeleton.skeleton_size_tokens_est} tokens cấu trúc.\n"
            f"  • Nội dung mẫu {max_retain_lines} dòng đầu:\n```python\n{preview}\n...\n```\n"
            f"💡 [LƯU Ý]: Toàn bộ cấu trúc tệp đã được ghi nhớ vào Working Memory. "
            f"Nếu cần đọc chính xác đoạn nào để phẫu thuật, hãy dùng view_file với StartLine/EndLine cụ thể."
        )
        return obs

    def get_skeleton(self, file_path: str) -> Optional[SymbolSkeleton]:
        return self._skeletons.get(file_path.replace("\\", "/"))


# Singleton instance
_eviction_engine = WorkingMemoryEvictionEngine()

def get_eviction_engine() -> WorkingMemoryEvictionEngine:
    return _eviction_engine
