# -*- coding: utf-8 -*-
"""
core/memory/telemetry_experience_bridge.py
JKAI ZENITH — Telemetry-to-Experience Memory Bridge (v1.0)
Architecture: Engram v2 Causal Bridge

Cầu nối khép kín: Đọc nhãn chấm thực tế từ Master (0.0 Sai / 0.5 Chưa chuẩn)
trong `storage/shadow_telemetry/labeled_telemetry.jsonl` và nạp tự động vào
`ExperienceStore` (Negative Memory) để JKAI học hỏi và không lặp lại lỗi cũ.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from core.memory.experience_store import ExperienceStore
from core.contracts.verification_contract import ExperienceRecord, FailureClassification

logger = logging.getLogger("jkai.memory.telemetry_bridge")


def compute_error_fingerprint(text: str) -> str:
    """
    Tạo dấu vân tay ngữ nghĩa (Semantic Error Fingerprint) cho câu hỏi/mục tiêu.
    Loại bỏ từ dừng, ký tự đặc biệt, chuẩn hóa chữ thường, sắp xếp từ khóa (order-invariant)
    để nhận diện chính xác các biến thể câu hỏi (Red Team Lượt 103).
    """
    if not text:
        return "generic_query"
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    # Lấy các từ có nghĩa (>2 ký tự), loại bỏ trùng lặp và sắp xếp theo bảng chữ cái
    unique_words = sorted(list(set(w for w in clean.split() if len(w) > 2)))
    return "_".join(unique_words[:8]) if unique_words else "short_query"


def match_error_fingerprints(fp1: str, fp2: str, min_overlap: int = 3) -> bool:
    """So khớp 2 dấu vân tay lỗi: khớp tuyệt đối hoặc trùng khớp >= min_overlap từ khóa."""
    if fp1 == fp2:
        return True
    set1 = set(fp1.split("_"))
    set2 = set(fp2.split("_"))
    overlap = len(set1 & set2)
    return overlap >= min_overlap and overlap >= min(len(set1), len(set2)) * 0.6


class TelemetryExperienceBridge:
    """Bridge đồng bộ nhãn chấm từ Master vào ExperienceStore."""

    _imported_records: Set[str] = set()

    @classmethod
    def get_telemetry_file_path(cls) -> Path:
        """Xác định đường dẫn file telemetry (hỗ trợ cả trong Docker lẫn dev host)."""
        container_path = Path("/storage/shadow_telemetry/labeled_telemetry.jsonl")
        if container_path.exists():
            return container_path
        
        # Local workspace path
        local_path = Path(__file__).resolve().parent.parent.parent / "storage" / "shadow_telemetry" / "labeled_telemetry.jsonl"
        return local_path

    @classmethod
    def sync_labeled_records(cls) -> int:
        """
        Quét file labeled_telemetry.jsonl và nạp các nhãn chưa xử lý vào ExperienceStore.
        Trả về số lượng record mới được nạp.
        """
        telemetry_file = cls.get_telemetry_file_path()
        if not telemetry_file.exists():
            return 0

        imported_count = 0
        try:
            with open(telemetry_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue

                    record_id = data.get("record_id")
                    if not record_id or record_id in cls._imported_records:
                        continue

                    score = data.get("score")
                    verdict = data.get("verdict", "")
                    
                    # Chỉ nạp các bài học tiêu cực (0.0 = Sai hoàn toàn, 0.5 = Chưa chuẩn)
                    if score in (0.0, 0.5) or verdict in ("COMPLETELY_WRONG", "PARTIALLY_CORRECT"):
                        cls.ingest_record(data)
                        imported_count += 1
                    
                    cls._imported_records.add(record_id)
        except Exception as exc:
            logger.error("❌ [TELEMETRY-BRIDGE-ERR] Failed to sync labeled telemetry: %s", exc)

        if imported_count > 0:
            logger.info("🧠 [TELEMETRY-BRIDGE] Synchronized %d negative lesson(s) to ExperienceStore", imported_count)
        return imported_count

    @classmethod
    def ingest_record(cls, data: Dict[str, Any]) -> None:
        """Chuyển đổi một bản ghi telemetry thành ExperienceRecord và lưu vào store."""
        msg_preview = data.get("msg_preview", "")
        task_id = data.get("task_id", "")
        score = data.get("score", 0.0)
        verdict = data.get("verdict", "FLAGGED")
        notes = data.get("notes", "")

        fingerprint = compute_error_fingerprint(msg_preview)
        
        lesson = f"Master rated {verdict} (score={score}). Output preview: '{msg_preview[:120]}...'"
        if notes:
            lesson += f" | Notes: {notes}"

        exp_record = ExperienceRecord(
            task_signature=fingerprint,
            context_summary=f"Master Feedback: {verdict} for task {task_id}",
            strategy_used="master_supervised_feedback",
            outcome="FAILED",
            failure_classification=FailureClassification.VERIFICATION_FAILURE if score == 0.0 else FailureClassification.MODEL_FAILURE,
            failure_cause=f"Direct Master feedback: {verdict}",
            negative_lessons=[lesson],
            confidence_rating=0.99
        )
        ExperienceStore.add_record(exp_record)


telemetry_bridge = TelemetryExperienceBridge()
