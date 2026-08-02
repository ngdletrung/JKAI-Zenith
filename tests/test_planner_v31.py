"""
Tests for Planner v3.1 (services/ai-brain/planner.py).
Proper pytest conversion of the legacy script-style test.
"""

import os
import sys

import pytest
from pydantic import ValidationError

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "services", "ai-brain"))

from planner import Planner, Blueprint


def test_pydantic_validation():
    valid_data = {
        "thought": "Cần trinh sát web trước khi tổng hợp.",
        "steps": [
            {
                "id": "1",
                "tool": "web_search",
                "args": {"query": "python 2024"},
                "description": "Tìm kiếm thông tin",
                "assigned_agent": "agent_executor_beta.md",
                "hardware_target": "BETA",
                "expert_mindset": "Be fast",
                "verification": "Check results",
                "parallel": True,
            }
        ],
        "rationale": "Tiết kiệm GPU cho bước sau",
        "failure_speculation": "Nếu mất mạng sẽ dùng cache",
    }

    model = Blueprint.model_validate(valid_data)
    assert model.steps[0].hardware_target == "BETA"
    assert model.steps[0].tool == "web_search"

    invalid_data = valid_data.copy()
    invalid_data["steps"][0]["hardware_target"] = "INVALID"
    with pytest.raises(ValidationError):
        Blueprint.model_validate(invalid_data)


def test_complexity_estimation():
    planner = Planner()
    simple = planner._estimate_complexity("Viết email chào mừng")
    complex_goal = planner._estimate_complexity("Phân tích và tích hợp hệ thống pipeline cho dữ liệu lớn")

    assert simple["level"] == "simple"
    assert complex_goal["level"] in ("complex", "extreme")
    assert complex_goal["budget"] > simple["budget"]

    # Diacritic-agnostic: input không dấu (JKAI normalize) vẫn phải nhận diện đúng độ phức tạp
    complex_norm = planner._estimate_complexity("phan tich va tich hop he thong pipeline cho du lieu lon")
    assert complex_norm["level"] in ("complex", "extreme")
