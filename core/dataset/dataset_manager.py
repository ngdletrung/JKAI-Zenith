# -*- coding: utf-8 -*-
"""
core/dataset/dataset_manager.py
JKAI Dataset Management & LoRA Alignment Registry (Target: 1,000 labels)

Phân tầng 5 nhóm chuẩn hóa:
- A: MATH_FIDELITY (250 mẫu) - Số đúng, đơn vị chuẩn, không tráo thùng/tấn
- B: ANAPHORA_CONTEXT (250 mẫu) - Hiểu đại từ nối, kế thừa ngữ cảnh mission trước
- C: EPISTEMIC_TRUTHFULNESS (200 mẫu) - Bẫy logic, dữ kiện thiếu, không bịa đặt
- D: TOOL_AND_FILEOPS (150 mẫu) - Thao tác file, sandbox execution
- E: MASTER_STANDARD_COMMUNICATION (150 mẫu) - Đi thẳng vào vấn đề, không rào đón
"""

from __future__ import annotations
import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

def _resolve_dataset_dir() -> str:
    # Ưu tiên /workspace mount trong Docker container
    if os.path.exists("/workspace"):
        return "/workspace/data/labeled_dataset"
    # Fallback chạy trực tiếp từ host
    curr = os.path.abspath(__file__)
    # Đi lùi lên thư mục gốc JKAI
    while curr and os.path.basename(curr) not in ("JKAI", "workspace", ""):
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.join(curr, "data", "labeled_dataset")

DATASET_DIR = _resolve_dataset_dir()
SEED_BANK_FILE = os.path.join(DATASET_DIR, "zenith_seed_bank_1000.jsonl")
GOLD_DATASET_FILE = os.path.join(DATASET_DIR, "master_gold_dataset.jsonl")


CATEGORIES = {
    "A_MATH_FIDELITY": {"target": 250, "desc": "Số học thực tế, bảo toàn đơn vị gốc"},
    "B_ANAPHORA_CONTEXT": {"target": 250, "desc": "Ngữ cảnh liên mission, giải nghĩa đại từ nối"},
    "C_EPISTEMIC_TRUTHFULNESS": {"target": 200, "desc": "Trung thực nhận thức, xử lý dữ kiện thiếu và bẫy logic"},
    "D_TOOL_AND_FILEOPS": {"target": 150, "desc": "Thao tác công cụ, file và lệnh sandbox"},
    "E_MASTER_COMMUNICATION": {"target": 150, "desc": "Giao tiếp chuẩn Master: trực diện, súc tích, không sáo rỗng"}
}

@dataclass
class LabeledRecord:
    id: str
    category: str
    goal: str
    history: List[Dict[str, str]]
    model_response: str
    target_response: str
    verdict: str  # ACCEPT, REJECT, REVIEW
    failure_type: Optional[str] = None
    source_mission_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    reviewed_by_master: bool = False
    master_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "goal": self.goal,
            "history": self.history or [],
            "model_response": self.model_response,
            "target_response": self.target_response,
            "verdict": self.verdict,
            "failure_type": self.failure_type,
            "source_mission_id": self.source_mission_id,
            "created_at": self.created_at,
            "reviewed_by_master": self.reviewed_by_master,
            "master_notes": self.master_notes,
        }



class DatasetManager:
    """Quản trị Ngân hàng mẫu hạt giống (Seed Bank) và Bộ dữ liệu chuẩn Master (Gold Dataset)."""

    def __init__(self, seed_file: str = SEED_BANK_FILE, gold_file: str = GOLD_DATASET_FILE):
        self.seed_file = seed_file
        self.gold_file = gold_file
        os.makedirs(os.path.dirname(self.seed_file), exist_ok=True)

    def load_gold_dataset(self) -> List[LabeledRecord]:
        """Tải toàn bộ nhãn THỰC TẾ do Master đã phán quyết."""
        records = []
        if not os.path.exists(self.gold_file):
            return records
        with open(self.gold_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(LabeledRecord(**json.loads(line)))
                    except Exception:
                        continue
        return records

    def record_master_feedback(self, record: LabeledRecord) -> bool:
        """Ghi nhận một mẫu do Master trực tiếp chấm vào Gold Dataset."""
        record.reviewed_by_master = True
        with open(self.gold_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return True

    def load_all(self) -> List[LabeledRecord]:
        return self.load_gold_dataset()

    def append_seed_record(self, record: LabeledRecord) -> bool:
        with open(self.seed_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return True

    def get_stats(self) -> Dict[str, Any]:
        records = self.load_all()
        stats = {
            "total": len(records),
            "target": 1000,
            "master_reviewed": sum(1 for r in records if r.reviewed_by_master),
            "verdicts": {"ACCEPT": 0, "REJECT": 0, "REVIEW": 0},
            "by_category": {cat: 0 for cat in CATEGORIES}
        }
        for r in records:
            stats["verdicts"][r.verdict] = stats["verdicts"].get(r.verdict, 0) + 1
            if r.category in stats["by_category"]:
                stats["by_category"][r.category] += 1
            else:
                stats["by_category"][r.category] = 1
        return stats


dataset_manager = DatasetManager()
