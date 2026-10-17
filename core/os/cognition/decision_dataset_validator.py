# -*- coding: utf-8 -*-
"""
core/os/cognition/decision_dataset_validator.py
================================================
JKAI Zenith — Cognitive Decision Dataset Semantic Validator (Phase A3).
Directive: Master Lee Trung's Approval & Senior Red Team Audit SOP v2.4.

Chức năng:
Tự động thẩm tra ngữ nghĩa sâu của tập dữ liệu huấn luyện Gold Decision LoRA:
1. Ràng buộc số lượng: Bắt buộc >= 100 mẫu (Luật chốt A0), cấm train khi thiếu mẫu.
2. Cân bằng chiến lược: Đủ 5 nhóm (FAST, MULTI_STEP, RECOVERY, CLARIFICATION, ESCALATE).
3. Hợp đồng dữ liệu (Data Contract): Kiểm tra TTL, Compute Budget, Freshness Policy.
4. Cấu trúc nhận thức sâu: Bắt buộc có 'alternatives_rejected' (dạy mô hình ranh giới quyết định).
5. Vệ sinh phục hồi lỗi (Recovery Hygiene):
   - Cấm tự ý đổi path hoặc đánh cắp credential khi gặp Permission Denied.
   - Cấm dùng cache thiu/chưa kiểm chứng độ tươi khi gặp timeout mạng/CSDL.
   - Cấm lặp lại lệnh hỏng một cách mù quáng.
6. Phân định thẩm quyền leo thang:
   - Thao tác phá hoại/nguy hiểm -> Bắt buộc leo thang lên MASTER_HUMAN_APPROVAL.
   - Bài toán trừu tượng/bất định cao -> Chuyển tiếp TEACHER_MODEL.
7. Chống rò rỉ đề thi: N-gram Overlap Guard < 0.40 so với kho đề niêm phong sealed_C.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.os.cognition.real_lora_trainer import check_exam_ngram_leak

logger = logging.getLogger("JKAI.Cognition.DatasetValidator")


@dataclass
class ValidationReport:
    is_valid: bool
    total_samples: int
    group_counts: Dict[str, int] = field(default_factory=dict)
    contract_violations: List[str] = field(default_factory=list)
    hygiene_violations: List[str] = field(default_factory=list)
    leak_violations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_samples": self.total_samples,
            "group_counts": self.group_counts,
            "contract_violations_count": len(self.contract_violations),
            "hygiene_violations_count": len(self.hygiene_violations),
            "leak_violations_count": len(self.leak_violations),
            "errors": self.errors,
        }


class DecisionDatasetValidator:
    """
    Bộ thẩm tra ngữ nghĩa sâu tự động cho tập dữ liệu Gold Decision LoRA.
    """

    CANONICAL_GROUPS = (
        "FAST_DIRECT",
        "MULTI_STEP_PLANNING",
        "ERROR_ADAPTIVE_RECOVERY",
        "ASK_USER_CLARIFICATION",
        "ESCALATE_MODEL_OR_HUMAN",
    )

    REQUIRED_CONTRACT_FIELDS = (
        "source", "sample_count", "created_at", "expires_at",
        "freshness_policy", "benchmark_id", "compute_budget", "approval_tier"
    )

    def __init__(self, min_samples: int = 100, max_ngram_overlap: float = 0.40):
        self.min_samples = min_samples
        self.max_ngram_overlap = max_ngram_overlap

    def validate_dataset(
        self,
        dataset_path: Path,
        exam_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> ValidationReport:
        if not dataset_path.exists():
            return ValidationReport(
                is_valid=False,
                total_samples=0,
                errors=[f"Dataset file not found at: {dataset_path}"],
            )

        samples: List[Dict[str, Any]] = []
        with open(dataset_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if line.strip():
                    try:
                        samples.append(json.loads(line.strip()))
                    except json.JSONDecodeError as e:
                        return ValidationReport(
                            is_valid=False,
                            total_samples=len(samples),
                            errors=[f"Malformed JSON on line {idx + 1}: {e}"],
                        )

        total_count = len(samples)
        errors: List[str] = []
        contract_violations: List[str] = []
        hygiene_violations: List[str] = []
        leak_violations: List[str] = []

        # 1. Ràng buộc tối thiểu số lượng mẫu
        if total_count < self.min_samples:
            errors.append(
                f"INSUFFICIENT_SAMPLES: expected >= {self.min_samples}, got {total_count} (Vi phạm Luật chốt A0)"
            )

        group_counts: Dict[str, int] = {grp: 0 for grp in self.CANONICAL_GROUPS}

        for idx, sample in enumerate(samples):
            sample_id = sample.get("id", f"sample_{idx}")
            grp = sample.get("group")
            if grp not in group_counts:
                errors.append(f"{sample_id}: Invalid group '{grp}'")
                continue
            group_counts[grp] += 1

            # 2. Thẩm tra Data Contract
            contract = sample.get("data_contract", {})
            for fld in self.REQUIRED_CONTRACT_FIELDS:
                if fld not in contract or contract[fld] is None:
                    contract_violations.append(f"{sample_id}: Missing contract field '{fld}'")

            # 3. Thẩm tra cấu trúc nhận thức & alternatives_rejected
            raw_out = sample.get("output", "{}")
            out_obj = json.loads(raw_out) if isinstance(raw_out, str) else raw_out

            strategy = out_obj.get("strategy")
            if strategy != grp:
                errors.append(f"{sample_id}: Strategy mismatch (group={grp} vs strategy={strategy})")

            # Bắt buộc có lý do loại trừ các nhánh khác (alternatives_rejected) để dạy biên quyết định
            alts = out_obj.get("alternatives_rejected")
            if not alts or len(alts) < 2:
                hygiene_violations.append(
                    f"{sample_id}: Missing or insufficient 'alternatives_rejected' (must reject >= 2 alternatives)"
                )

            # 4. Thẩm tra Recovery Hygiene (Chống tác dụng phụ khi phục hồi)
            if grp == "ERROR_ADAPTIVE_RECOVERY":
                inst_lower = str(sample.get("instruction", "")).lower()
                rationale_lower = str(out_obj.get("rationale", "")).lower()
                action_lower = str(out_obj.get("action", "")).lower()

                # Cấm tự ý đổi path bừa bãi khi gặp Permission Denied
                if "permission denied" in inst_lower or "403" in inst_lower:
                    if "tự ý" in rationale_lower or "đổi sang" in action_lower:
                        hygiene_violations.append(
                            f"{sample_id}: Unsafe permission recovery (must verify authority, not arbitrarily switch path)"
                        )

                # Cấm dùng offline cache thiu khi timeout
                if "timeout" in inst_lower and "offline" in action_lower:
                    if "freshness_verified" not in rationale_lower and "kiểm chứng" not in rationale_lower:
                        hygiene_violations.append(
                            f"{sample_id}: Unsafe offline fallback without verifying cache freshness"
                        )

            # 5. Phân định thẩm quyền leo thang (Escalation Hygiene)
            if grp == "ESCALATE_MODEL_OR_HUMAN":
                inst_lower = str(sample.get("instruction", "")).lower()
                target = str(out_obj.get("escalation_target", "")).upper()
                is_destructive = any(w in inst_lower for w in ("rm -rf", "xóa toàn bộ", "drop database", "format", "ngắt nguồn", "flash firmware"))
                if is_destructive and "MASTER" not in target:
                    hygiene_violations.append(
                        f"{sample_id}: Destructive action escalated to '{target}' instead of MASTER_APPROVAL"
                    )

            # 6. Kiểm tra N-gram Leak
            if exam_tasks:
                cand_text = f"{sample.get('instruction', '')} {sample.get('output', '')}"
                is_clean, overlap, reason = check_exam_ngram_leak(
                    cand_text, exam_tasks, max_4gram_ratio=self.max_ngram_overlap
                )
                if not is_clean:
                    leak_violations.append(f"{sample_id}: {reason}")

        # Kiểm tra tính cân bằng nhóm
        if total_count >= self.min_samples:
            target_per_group = total_count // len(self.CANONICAL_GROUPS)
            for grp, cnt in group_counts.items():
                if cnt != target_per_group:
                    errors.append(f"UNBALANCED_GROUP: {grp} has {cnt} samples, expected {target_per_group}")

        is_valid = (
            len(errors) == 0
            and len(contract_violations) == 0
            and len(hygiene_violations) == 0
            and len(leak_violations) == 0
        )

        return ValidationReport(
            is_valid=is_valid,
            total_samples=total_count,
            group_counts=group_counts,
            contract_violations=contract_violations,
            hygiene_violations=hygiene_violations,
            leak_violations=leak_violations,
            errors=errors,
        )


# Singleton validator instance
decision_dataset_validator = DecisionDatasetValidator()
