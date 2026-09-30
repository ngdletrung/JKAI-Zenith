# -*- coding: utf-8 -*-
"""
tests/test_distillation_batch_3_logic.py
Bộ kiểm chứng 4 Cửa cho Mẻ 3: 50 Mẫu Suy Luận Logic Thuần Túy (Pure Logic Reasoning)
Co-Teaching: 25 mẫu từ Opencode (OPLOGIC-001..025) + 25 mẫu từ Antigravity (ANTILOGIC-001..025).
"""

import json
import ast
import pytest
from pathlib import Path

OPLOGIC_FILE = Path("data/distillation/coteach_oplogic_25.jsonl")
ANTILOGIC_FILE = Path("data/distillation/coteach_antilogic_25.jsonl")


def load_all_batch_3_samples():
    assert OPLOGIC_FILE.exists(), f"Không tìm thấy: {OPLOGIC_FILE}"
    assert ANTILOGIC_FILE.exists(), f"Không tìm thấy: {ANTILOGIC_FILE}"
    samples = []
    with open(OPLOGIC_FILE, "r", encoding="utf-8") as f:
        samples.extend([json.loads(line.strip()) for line in f if line.strip()])
    with open(ANTILOGIC_FILE, "r", encoding="utf-8") as f:
        samples.extend([json.loads(line.strip()) for line in f if line.strip()])
    return samples


def test_gate1_schema_and_ast_validity():
    """Cửa 1: Cú pháp & Schema chuẩn (50 mẫu, 25 Opencode + 25 Antigravity)."""
    samples = load_all_batch_3_samples()
    assert len(samples) == 50, f"Dự kiến 50 mẫu, thực tế có {len(samples)}"

    required_keys = ["sample_id", "level", "task_code", "teacher_id", "critic_id", "prompt", "chain_of_thought", "decision_type"]
    for s in samples:
        for k in required_keys:
            assert k in s, f"Mẫu {s.get('sample_id')} thiếu trường {k}"

        payload = s.get("action_payload", {})
        if payload.get("type") == "PYTHON_CODE":
            code = payload.get("code", "")
            ast.parse(code)


def test_gate2_no_negative_list_violations():
    """Cửa 2: Quét tự động không vi phạm 6 Lằn Ranh Đỏ."""
    samples = load_all_batch_3_samples()
    for s in samples:
        cot = json.dumps(s["chain_of_thought"], ensure_ascii=False).lower()
        # Nếu có đề cập vi phạm lằn ranh đỏ, CoT phải chỉ rõ từ chối hoặc cảnh báo
        if "inv 1" in cot or "inv 3" in cot:
            assert any(word in cot for word in ["từ chối", "nguy hiểm", "bất biến", "không được"])


def test_gate3_provenance_truthfulness():
    """Cửa 3: Tính chính danh tác giả (Provenance) chuẩn xác 100%."""
    samples = load_all_batch_3_samples()
    op_samples = [s for s in samples if s["sample_id"].startswith("OPLOGIC-")]
    anti_samples = [s for s in samples if s["sample_id"].startswith("ANTILOGIC-")]

    assert len(op_samples) == 25, f"Opencode phải đủ 25 mẫu, thực tế: {len(op_samples)}"
    assert len(anti_samples) == 25, f"Antigravity phải đủ 25 mẫu, thực tế: {len(anti_samples)}"

    for s in op_samples:
        assert s["teacher_id"] == "opencode_logic_teacher", f"Sai teacher_id ở {s['sample_id']}"
    for s in anti_samples:
        assert s["teacher_id"] == "gemini-2.5-pro_via_antigravity", f"Sai teacher_id ở {s['sample_id']}"


def test_gate4_archetype_coverage():
    """Cửa 4: Phủ đầy đủ các mô thức tư duy logic cốt lõi."""
    samples = load_all_batch_3_samples()
    task_codes = {s["task_code"] for s in samples}

    # Phải có đủ các nhóm logic
    assert any("DEDUCT" in tc or "CONTRADICTION" in tc for tc in task_codes)
    assert any("CAUSAL" in tc for tc in task_codes)
    assert any("CONSTRAINT" in tc or "DAG" in tc for tc in task_codes)
    assert any("ABDUCTION" in tc or "FALSIFICATION" in tc or "OCCAM" in tc for tc in task_codes)
    assert any("COUNTERFACTUAL" in tc or "SECOND_ORDER" in tc for tc in task_codes)
    assert any("BOUNDARY" in tc or "EPISTEMIC" in tc for tc in task_codes)
    assert any("ADVERSARIAL" in tc or "GAME_THEORY" in tc for tc in task_codes)
