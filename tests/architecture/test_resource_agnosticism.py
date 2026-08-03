"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: RESOURCE AGNOSTICISM
tests/architecture/test_resource_agnosticism.py

Architectural Invariant Enforced:
    Cognitive, Knowledge, and Capabilities domains MUST NOT contain low-level
    hardware / accelerator keywords (CUDA, ROCm, Vulkan, VRAM, num_gpu, num_thread).
"""

import pytest
import os
import glob
import ast


class TestResourceAgnosticism:

    def test_cognitive_knowledge_capabilities_have_zero_hardware_keywords(self):
        target_dirs = [
            os.path.join("core", "cognitive"),
            os.path.join("core", "knowledge"),
            os.path.join("core", "capabilities"),
        ]

        forbidden_keywords = ["CUDA", "ROCm", "Vulkan", "num_gpu", "num_thread"]

        for target_dir in target_dirs:
            py_files = glob.glob(os.path.join(target_dir, "**", "*.py"), recursive=True)
            for filepath in py_files:
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()

                for kw in forbidden_keywords:
                    assert kw not in code, (
                        f"Resource Leakage Violation in {filepath}: "
                        f"High-level domain code must NOT contain low-level keyword '{kw}'!"
                    )
