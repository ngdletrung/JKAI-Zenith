# -*- coding: utf-8 -*-
"""
Unit test suite cho Cognitive Immune System v1.0
"""

import pytest
from core.kernel.immune_memory import (
    CognitiveImmuneSystem, immune_system, ImmuneAntibody
)


class TestCognitiveImmuneSystem:
    """Kiểm tra chức năng sinh kháng thể và miễn dịch sai lầm trong quá khứ."""

    @pytest.fixture(autouse=True)
    def reset_immune(self):
        immune_system.antibodies.clear()

    def test_register_failure_creates_antibody(self):
        ab = immune_system.register_failure(
            failure_pattern="invalid syntax (<unknown>, line 1)",
            root_cause="AST Python SyntaxError",
            prescriptive_rule="Luôn đóng đầy đủ dấu ngoặc trong biểu thức",
            task_id="task_test_ab"
        )
        assert ab.occurrence_count == 1
        assert "Luôn đóng đầy đủ dấu ngoặc" in ab.prescriptive_rule
        assert len(immune_system.antibodies) == 1

    def test_repeated_failure_reinforces_antibody(self):
        # Đăng ký cùng 1 lỗi 2 lần
        immune_system.register_failure("syntax error 123", "syntax", "Rule A")
        ab2 = immune_system.register_failure("syntax error 123", "syntax", "Rule A")
        assert ab2.occurrence_count == 2

    def test_build_immune_prompt_injection_format(self):
        immune_system.register_failure("error 1", "cause 1", "Quy tắc an toàn số 1")
        immune_system.register_failure("error 2", "cause 2", "Quy tắc an toàn số 2")

        block = immune_system.build_immune_prompt_injection()
        assert "<cognitive_immune_invariants>" in block
        assert "Quy tắc an toàn số 1" in block
        assert "Quy tắc an toàn số 2" in block
