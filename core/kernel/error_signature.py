# -*- coding: utf-8 -*-
"""
Meta CCA Error Signature Extraction & Clustering Engine (Weapon 1 Part 2).
Tự động trích xuất chữ ký lỗi (Error Signature) khi gặp thất bại trong vận hành,
thay thế hoàn toàn việc con người biên soạn thủ công KNOWN_GAPS.md.
Cho phép JKAI tự học thất bại và tự sinh tri thức phòng thủ xuyên session.
"""

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorSignature(BaseModel):
    """Mô hình chữ ký lỗi tự động trích xuất theo chuẩn Meta Confucius Code Agent (CCA)."""
    signature_id: str = Field(description="Mã định danh duy nhất của chữ ký lỗi (ví dụ: ERR-SIG-001)")
    error_type: str = Field(description="Phân loại lỗi (ví dụ: CONFIRMATION_BIAS_FABRICATION, OSCILLATION_LOOP)")
    trigger_pattern: str = Field(description="Biểu thức điều kiện nhận diện lỗi (pattern nhận dạng)")
    automated_invariant: str = Field(description="Bất biến an toàn tự động áp đặt để ngăn chặn tái phạm")
    occurrences: int = Field(default=1, description="Số lần lỗi đã xuất hiện trong lịch sử vận hành")
    first_seen_ts: float = Field(default_factory=time.time)
    last_seen_ts: float = Field(default_factory=time.time)
    sample_task_id: str = Field(default="")
    evidence_snippet: str = Field(default="")


class ErrorSignatureEngine:
    """Động cơ quản lý và gom cụm chữ ký lỗi tự động."""

    def __init__(self, ledger_path: str = "data/knowledge/error_signatures_ledger.jsonl"):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self._signatures: Dict[str, ErrorSignature] = {}
        self._load_ledger()

    def _load_ledger(self) -> None:
        if not os.path.exists(self.ledger_path):
            # Seed 5 chữ ký gốc từ các bài học trước để không bị rỗng
            self._seed_default_signatures()
            return

        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        sig = ErrorSignature.model_validate(data)
                        self._signatures[sig.signature_id] = sig
                    except Exception:
                        pass
        except Exception:
            pass

    def _seed_default_signatures(self) -> None:
        seeds = [
            ErrorSignature(
                signature_id="ERR-SIG-001",
                error_type="CONFIRMATION_BIAS_FABRICATION",
                trigger_pattern="view_file_failed && submit_verdict_attempted",
                automated_invariant="Tuyệt đối cấm xuất kết quả khi chưa đọc file thành công trên đĩa vật lý (needs_validation).",
                occurrences=3,
                sample_task_id="TASK-001_attempt_1",
            ),
            ErrorSignature(
                signature_id="ERR-SIG-002",
                error_type="MULTI_FILE_AUDIT_EARLY_STOP",
                trigger_pattern="goal_requires_multi_files && read_files_count < required_count",
                automated_invariant="Phải đọc đủ 100% các tệp được chỉ định trong goal trước khi kích hoạt tổng hợp báo cáo.",
                occurrences=2,
                sample_task_id="TASK-001_attempt_2",
            ),
            ErrorSignature(
                signature_id="ERR-SIG-003",
                error_type="TOOL_OSCILLATION_REPETITION",
                trigger_pattern="tool_repetition >= 2 && outcome == no_progress",
                automated_invariant="Bẻ gãy dao động: Cấm gọi lại cùng tool, chuyển hướng Agent sang xuất final_answer hoặc đổi tool khác.",
                occurrences=4,
                sample_task_id="TASK-001_attempt_3",
            ),
            ErrorSignature(
                signature_id="ERR-SIG-004",
                error_type="PATH_RESOLUTION_DISCREPANCY",
                trigger_pattern="path_contains_shared_core_vs_relative_core",
                automated_invariant="Tự động chuẩn hóa đường dẫn qua resolve_container_or_workspace_path trước khi gọi tool.",
                occurrences=2,
                sample_task_id="TASK-001_rc1",
            ),
        ]
        for s in seeds:
            self._signatures[s.signature_id] = s
        self._flush_ledger()

    def _flush_ledger(self) -> None:
        try:
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                for sig in self._signatures.values():
                    f.write(sig.model_dump_json() + "\n")
        except Exception:
            pass

    def record_failure(
        self,
        error_type: str,
        trigger_pattern: str,
        automated_invariant: str,
        task_id: str = "",
        evidence: str = "",
    ) -> ErrorSignature:
        """Tự động ghi nhận một thất bại và phân cụm vào chữ ký lỗi tương ứng."""
        # Tạo hash đại diện cho nhóm lỗi
        cluster_key = hashlib.sha256(f"{error_type}:{trigger_pattern}".encode("utf-8")).hexdigest()[:8]
        sig_id = f"ERR-SIG-{cluster_key.upper()}"

        if sig_id in self._signatures:
            sig = self._signatures[sig_id]
            sig.occurrences += 1
            sig.last_seen_ts = time.time()
            if evidence:
                sig.evidence_snippet = evidence[:300]
        else:
            sig = ErrorSignature(
                signature_id=sig_id,
                error_type=error_type,
                trigger_pattern=trigger_pattern,
                automated_invariant=automated_invariant,
                occurrences=1,
                sample_task_id=task_id,
                evidence_snippet=evidence[:300],
            )
            self._signatures[sig_id] = sig

        self._flush_ledger()
        return sig

    def get_relevant_invariants_for_goal(self, goal: str, top_k: int = 3) -> List[ErrorSignature]:
        """Trích xuất các chữ ký lỗi có liên quan trực tiếp tới mục tiêu hiện tại."""
        low_goal = (goal or "").lower()
        scored: List[tuple[int, ErrorSignature]] = []

        for sig in self._signatures.values():
            score = 0
            if "multi" in sig.trigger_pattern and len(re.findall(r"\b[\w/\\-]+\.py\b", low_goal)) >= 2:
                score += 5
            if "view_file" in sig.trigger_pattern and any(k in low_goal for k in ["đọc", "view", "kiểm toán", "audit"]):
                score += 4
            if "oscillation" in sig.error_type.lower():
                score += 3
            if "path" in sig.error_type.lower() and any(k in low_goal for k in ["core/", "shared/", ".py"]):
                score += 3

            score += min(3, sig.occurrences)  # Ưu tiên lỗi xuất hiện nhiều lần
            scored.append((score, sig))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def render_dynamic_awareness_prompt(self, goal: str) -> str:
        """Tạo prompt tự nhận thức động thay thế KNOWN_GAPS.md thủ công."""
        relevant = self.get_relevant_invariants_for_goal(goal, top_k=3)
        if not relevant:
            return ""

        lines = [
            "🧠 [TỰ NHẬN THỨC ĐỘNG — META CCA ERROR SIGNATURES]:",
            "Hệ thống đã tự động trích xuất các chữ ký thất bại quá khứ có nguy cơ tái diễn trong tác vụ này:",
        ]
        for sig in relevant:
            lines.append(f"  • [{sig.signature_id} | {sig.error_type} (Gặp {sig.occurrences} lần)]: {sig.automated_invariant}")
        lines.append("BẮT BUỘC bạn phải tuân thủ nghiêm ngặt các bất biến trên!")
        return "\n".join(lines)


# Singleton
_error_signature_engine = ErrorSignatureEngine()

def get_error_signature_engine() -> ErrorSignatureEngine:
    return _error_signature_engine
