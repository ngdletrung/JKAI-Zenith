# -*- coding: utf-8 -*-
"""
scripts/build_gold_boundary_contrastive_dataset.py
JKAI ZENITH — Learning Loop: Gold Boundary Contrastive Dataset Generator

Trích xuất các ca thất bại thực tế từ Artifact Baseline v2.1 (results/baseline_30_ood_qwen3b_v2_1.json)
kết hợp cùng Ground Truth (data/distillation/held_out_eval_30.jsonl) để kiến tạo
tập dữ liệu đối chiếu ranh giới (GOOD / BAD / NEAR_MISS) phục vụ huấn luyện LoRA cho JKAI Model v2.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BASELINE_PATH = WORKSPACE_DIR / "results" / "baseline_30_ood_qwen3b_v2_1.json"
GROUND_TRUTH_PATH = WORKSPACE_DIR / "data" / "distillation" / "held_out_eval_30.jsonl"
OUTPUT_PATH = WORKSPACE_DIR / "data" / "distillation" / "gold_boundary_contrastive_pairs.jsonl"

def generate_near_miss(category: str, expected_dec: str, expected_act: str) -> Dict[str, str]:
    """Tạo ví dụ ranh giới tiệm cận (Near-Miss) để tôi luyện độ phân định sắc bén."""
    if expected_dec == "REJECT_INVALID_REASONING":
        return {
            "decision": "DENY",
            "action": "REFUSE_WITH_POLICY_RULE",
            "near_miss_explanation": "Nhầm lẫn giữa vi phạm an ninh (Policy DENY) và lỗi ngụy biện logic toán học (REJECT_INVALID_REASONING)."
        }
    elif expected_dec == "DENY":
        return {
            "decision": "MODIFY",
            "action": "REQUIRE_HUMAN_CONFIRMATION",
            "near_miss_explanation": "Thỏa hiệp lằn ranh đỏ (Evasion via MODIFY) thay vì kiên quyết cấm triệt để (DENY)."
        }
    elif expected_dec == "MODIFY":
        return {
            "decision": "ALLOW",
            "action": "EXECUTE",
            "near_miss_explanation": "Chủ quan bỏ qua điều kiện an toàn / kênh kề, cho phép thực thi ngay mà không hiệu chỉnh giải pháp."
        }
    elif expected_dec == "ALLOW":
        return {
            "decision": "DENY",
            "action": "REFUSE_WITH_POLICY_RULE",
            "near_miss_explanation": "Báo động giả (False Alarm), từ chối nhầm một thao tác phân tích hợp lệ và an toàn."
        }
    return {
        "decision": "CLARIFY",
        "action": "REQUEST_USER_INPUT",
        "near_miss_explanation": "Hỏi lại thụ động khi dữ kiện đã có đủ căn cứ để quyết định."
    }

def build_contrastive_dataset():
    if not BASELINE_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy baseline: {BASELINE_PATH}")
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy ground truth: {GROUND_TRUTH_PATH}")

    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)

    ground_truth_map: Dict[str, Dict[str, Any]] = {}
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                ground_truth_map[item["case_id"]] = item

    contrastive_records: List[Dict[str, Any]] = []
    failure_cases = 0

    for case in baseline_data.get("cases", []):
        cid = case["case_id"]
        gt = ground_truth_map.get(cid)
        if not gt:
            continue

        taxonomy = case.get("taxonomy")
        is_all_correct = (taxonomy == "ALL_CORRECT")

        # Xác định các phân loại lỗi đặc thù
        is_fallacy_unsafe_allow = (gt["expected_decision"] == "REJECT_INVALID_REASONING" and case.get("parsed_decision") == "ALLOW")
        is_modify_evasion = (gt["expected_decision"] == "DENY" and case.get("parsed_decision") == "MODIFY")

        # Cấu trúc bản ghi đối chiếu
        good_example = {
            "decision": gt["expected_decision"],
            "action": gt["expected_action"],
            "reason": gt["gold_metadata"].get("expected_output", ""),
            "rationale": gt["gold_metadata"].get("gold_rationale", "")
        }

        bad_example = {
            "decision": case.get("parsed_decision") or "NONE",
            "action": case.get("matched_action_enum") or case.get("raw_action_field") or "NONE",
            "reason": case.get("parsed_reason") or "",
            "raw_output": case.get("raw_output", ""),
            "taxonomy": taxonomy,
            "is_fallacy_unsafe_allow": is_fallacy_unsafe_allow,
            "is_modify_evasion": is_modify_evasion
        }

        near_miss = generate_near_miss(
            category=gt.get("category", ""),
            expected_dec=gt["expected_decision"],
            expected_act=gt["expected_action"]
        )

        record = {
            "case_id": cid,
            "category": gt.get("category"),
            "state": gt.get("state"),
            "observation": gt.get("observation"),
            "evidence": gt.get("evidence"),
            "model_proposal": gt.get("model_proposal"),
            "is_baseline_failure": not is_all_correct,
            "good_decision": good_example,
            "bad_decision": bad_example,
            "near_miss": near_miss
        }

        contrastive_records.append(record)
        if not is_all_correct:
            failure_cases += 1

    # Lưu ra tệp JSONL
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in contrastive_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"==================================================")
    print(f"✅ GOLD BOUNDARY CONTRASTIVE DATASET BUILT")
    print(f"Tổng số ca xử lý: {len(contrastive_records)}")
    print(f"Số ca thất bại baseline được trích xuất: {failure_cases} / {len(contrastive_records)}")
    print(f"Đã lưu tệp tại: {OUTPUT_PATH}")
    print(f"==================================================")

if __name__ == "__main__":
    build_contrastive_dataset()
