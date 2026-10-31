# -*- coding: utf-8 -*-
"""
scripts/unify_all_roles_to_deepseek_r1.py
Hợp nhất 100% các vai trò xử lý ngôn ngữ trên GPU về duy nhất một mô hình: deepseek-r1:latest.
Triệt tiêu hoàn toàn hiện tượng hoán đổi VRAM (Zero VRAM Swapping) trên GPU 8GB.
"""
from pathlib import Path

def unify_roles():
    path = Path("intelligence/rule_hardware.md")
    text = path.read_text(encoding="utf-8")

    old_mapping = """| **RECEPTIONIST** | qwen3.5:4b | **GPU/VRAM** | 8192 | 2048 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | medium |
| **CHAT** | qwen3.5:4b | **GPU/VRAM** | 8192 | 2048 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning | medium |
| **PLANNER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning,planning | high |
| **CRITIC** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **EXECUTOR** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 2048 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_ALPHA** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 2048 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_BETA** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 2048 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **DEEP_REASONER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **SUMMARIZER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 2048 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | medium |"""

    unified_mapping = """| **RECEPTIONIST** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | high |
| **CHAT** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning | high |
| **PLANNER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning,planning | high |
| **CRITIC** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **EXECUTOR** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.10 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_ALPHA** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.10 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_BETA** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.10 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **DEEP_REASONER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **SUMMARIZER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | high |"""

    assert old_mapping in text, "Target mapping block not found in intelligence/rule_hardware.md!"
    text = text.replace(old_mapping, unified_mapping, 1)

    path.write_text(text, encoding="utf-8", newline="\r\n")
    print("SUCCESS_UNIFIED_ALL_ROLES_TO_DEEPSEEK_R1")

if __name__ == "__main__":
    unify_roles()
