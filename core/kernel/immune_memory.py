# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — COGNITIVE IMMUNE MEMORY SYSTEM v1.0              ║
║   Ghi Nhớ Mẫu Lỗi (Antigen/Antibody), Miễn Dịch Sai Lầm Quá Khứ  ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Khả Năng Tự Miễn Dịch Sai Lầm. 🛡️🧬⚡*
"""

from __future__ import annotations
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.kernel.decision_ledger import decision_ledger

logger = logging.getLogger("JKAI.ImmuneMemory")


@dataclass
class ImmuneAntibody:
    antibody_id: str
    failure_pattern: str       # Mẫu lỗi cú pháp/runtime (Antigen)
    root_cause: str            # Nguyên nhân gốc rễ
    prescriptive_rule: str     # Quy tắc phòng ngừa (Antibody injection)
    occurrence_count: int = 1
    created_at: float = field(default_factory=time.time)
    last_triggered_at: float = field(default_factory=time.time)


class CognitiveImmuneSystem:
    """
    🛡️ Hệ Thống Miễn Dịch Nhận Thức (Cognitive Immune System) v1.0
    - Lưu trữ danh mục các Kháng Thể Nhận Thức (Antibodies).
    - Khi phát hiện một lỗi lặp lại trong quá trình code hoặc tool execution:
      Tự động tạo Kháng Thể và tiêm vào System Prompt phòng ngừa cho các lượt sau.
    - Bảo đảm JKAI không bao giờ vấp phải cùng một lỗi 2 lần.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.antibodies: Dict[str, ImmuneAntibody] = {}

    def register_failure(
        self,
        failure_pattern: str,
        root_cause: str,
        prescriptive_rule: str,
        task_id: str = "sys"
    ) -> ImmuneAntibody:
        """
        Đăng ký một mẫu lỗi mới và sinh Kháng Thể (Antibody).
        """
        # Tạo hash đại diện cho mẫu lỗi
        antigen_hash = hashlib.sha256(failure_pattern.strip().lower().encode("utf-8")).hexdigest()[:12]
        ab_id = f"ab_{antigen_hash}"

        if ab_id in self.antibodies:
            ab = self.antibodies[ab_id]
            ab.occurrence_count += 1
            ab.last_triggered_at = time.time()
            logger.info(f"🛡️ [IMMUNE]: Kháng thể '{ab_id}' được gia cố (Đã gặp {ab.occurrence_count} lần).")
            return ab

        ab = ImmuneAntibody(
            antibody_id=ab_id,
            failure_pattern=failure_pattern,
            root_cause=root_cause,
            prescriptive_rule=prescriptive_rule,
            occurrence_count=1,
            created_at=time.time(),
            last_triggered_at=time.time()
        )
        self.antibodies[ab_id] = ab

        # Ghi nhận vào DecisionLedger
        decision_ledger.record_decision(
            decision_type="IMMUNE_ANTIBODY_CREATED",
            task_id=task_id,
            input_summary=f"Antigen: {failure_pattern[:60]}",
            output_decision=f"Antibody: {prescriptive_rule[:60]}",
            reason=f"Phát hiện lỗi mới: {root_cause}",
            metadata={"antibody_id": ab_id}
        )

        logger.info(f"🛡️ [IMMUNE]: Đã sinh Kháng Thể Mới '{ab_id}': {prescriptive_rule}")
        return ab

    def get_prescriptive_invariants(self, task_type: str = "ALL") -> List[str]:
        """Lấy danh sách tất cả các quy tắc kháng thể để tiêm vào prompt."""
        return [ab.prescriptive_rule for ab in self.antibodies.values()]

    def build_immune_prompt_injection(self) -> str:
        """Xây dựng khối văn bản tiêm phòng ngừa lỗi vào System Prompt."""
        rules = self.get_prescriptive_invariants()
        if not rules:
            return ""
        
        formatted_rules = "\n".join([f"- {r}" for r in rules])
        return (
            "\n<cognitive_immune_invariants>\n"
            "CÁC QUY TẮC MIỄN DỊCH BẮT BUỘC (BẢO VỆ TUYỆT ĐỐI CHỐNG LỖI CŨ):\n"
            f"{formatted_rules}\n"
            "</cognitive_immune_invariants>\n"
        )


immune_system = CognitiveImmuneSystem()
