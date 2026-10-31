# -*- coding: utf-8 -*-
"""
scripts/update_hardware_rules_deepseek_r1.py
Cập nhật intelligence/rule_hardware.md:
Đưa deepseek-r1:latest làm cỗ máy suy luận kép (Dual-Role: PLANNER + CRITIC + DEEP_REASONER).
"""
from pathlib import Path

def update_rules():
    path = Path("intelligence/rule_hardware.md")
    text = path.read_text(encoding="utf-8")

    # 1. Update Section 2.6
    s26_target = "| `qwen3.5:4b` (Planner/Critic/Deep) | 262144 | 8192 | GPU/VRAM | Native 262K để dành cho offload CPU đọc sâu về sau, chưa bật |"
    s26_replacement = (
        "| `qwen3.5:4b` (Receptionist/Summarizer/Fast) | 262144 | 8192 | GPU/VRAM | Tối ưu phản xạ nhanh và tổng hợp văn bản |\n"
        "| `deepseek-r1:latest` (Dual-Role Deep Reasoning) | 65536 | 8192 | GPU/VRAM | Chuyên gia suy luận sâu CoT kép (PLANNER + CRITIC), thường trực VRAM |"
    )

    # 2. Update Section 3 Active Role Mapping
    s3_target = (
        "| **PLANNER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 2048 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning,planning | high |\n"
        "| **CRITIC** | qwen3.5:4b | **GPU/VRAM** | 8192 | 2048 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |"
    )
    s3_replacement = (
        "| **PLANNER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning,planning | high |\n"
        "| **CRITIC** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |"
    )

    s3_deep_target = "| **DEEP_REASONER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 4096 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |"
    s3_deep_replacement = "| **DEEP_REASONER** | deepseek-r1:latest | **GPU/VRAM** | 8192 | 4096 | 0.60 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |"

    assert s26_target in text, "Section 2.6 target not found!"
    assert s3_target in text, "Section 3 target not found!"
    assert s3_deep_target in text, "Section 3 DEEP_REASONER target not found!"

    text = text.replace(s26_target, s26_replacement, 1)
    text = text.replace(s3_target, s3_replacement, 1)
    text = text.replace(s3_deep_target, s3_deep_replacement, 1)

    path.write_text(text, encoding="utf-8", newline="\r\n")
    print("✅ Đã cập nhật thành công deepseek-r1:latest vào intelligence/rule_hardware.md!")

if __name__ == "__main__":
    update_rules()
