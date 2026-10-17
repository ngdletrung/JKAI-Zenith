# -*- coding: utf-8 -*-
"""Khoa lich su mission (case vang 15/10): task_id duy nhat + chot nhat quan dap an."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))


def test_task_id_never_defaults_to_man():
    src = open("services/ai-control-plane/main.py", encoding="utf-8").read()
    assert 'payload["task_id"] = task_id' in src
    tmsrc = open("services/ai-control-plane/task_manager.py", encoding="utf-8").read()
    assert 'data.get("task_id", "man")' not in tmsrc
    assert 'tid == "man"' not in tmsrc or "task_" in tmsrc


def test_consistency_gate_flags_false_refusal():
    from deep_pipeline import DeepPipeline
    evidence = {
        "auto_recovery_01": {
            "status": "success",
            "output": "VN-Index tang 12 diem, thanh khoan 50.5 nghin ty. " * 5,
        }
    }
    res = DeepPipeline.check_answer_evidence_consistency(
        "He thong khong the tim thay ket qua nao ve thi truong.", evidence
    )
    assert res["contradiction"] is True
    assert "1 bằng chứng" in res["reason"] or "1 b" in res["reason"]


def test_consistency_gate_passes_honest_cases():
    from deep_pipeline import DeepPipeline
    # Khong phu nhan -> pass
    r1 = DeepPipeline.check_answer_evidence_consistency(
        "Bao cao phan tich nhu sau.", {"s": {"status": "success", "output": "x" * 100}}
    )
    assert r1["contradiction"] is False
    # Phu nhan nhung that su khong evidence -> pass (trung thuc)
    r2 = DeepPipeline.check_answer_evidence_consistency(
        "Khong the tim thay ket qua.", {"s": {"status": "error", "msg": "timeout"}}
    )
    assert r2["contradiction"] is False
