# -*- coding: utf-8 -*-
"""
core/os/cognition/event_checkpoint.py
======================================
[Trọng điểm 3 - Hiện đại hóa Kiến trúc T5/T6: Học hỏi OpenHands & LangGraph]
Microkernel Event Stream & Step Checkpointing:
1. Event Stream: Mọi Action (hành động) và Observation (kết quả quan sát)
   được chuẩn hóa thành chuỗi sự kiện bất biến (Immutable Event Sourcing)
   phát xạ vào `CognitiveEventStore`.
2. Step Checkpointing: Sau mỗi bước DAG thực thi thành công hoặc có dữ liệu,
   hệ thống tạo một Checkpoint trạng thái (`StepCheckpoint`) lưu giữ trọn vẹn
   dữ liệu chứng cứ (evidence snapshot) và các dữ kiện đã kiểm chứng (verified facts).
3. Time-Travel Backtracking: Khi Ban Kiểm Soát T5 phán quyết `[PARTIAL]` hoặc `[FAIL]`
   cần Re-plan, thay vì xóa sạch ngữ cảnh hoặc bắt đầu lại từ con số 0:
   - Hệ thống tự động xác định Checkpoint hợp lệ tốt nhất gần nhất (Best Valid Checkpoint).
   - Quay lui (Backtrack) về Checkpoint đó và bảo tồn toàn bộ dữ kiện đã xác minh.
   - Cung cấp ngữ cảnh đã thu thập cho T2 Planner để chỉ cần bổ sung các bước còn thiếu.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.os.cognition.event_model import CognitiveEvent, event_store

logger = logging.getLogger("JKAI.EventCheckpoint")


@dataclass
class StepCheckpoint:
    """Bản lưu trạng thái bất biến tại một mốc thực thi bước (LangGraph Checkpoint)."""
    checkpoint_id: str
    mission_id: str
    step_id: str
    step_index: int
    status: str  # SUCCESS | PARTIAL | ERROR | BLOCKED
    state_hash: str
    verified_facts: List[str] = field(default_factory=list)
    evidence_snapshot: Dict[str, Any] = field(default_factory=dict)
    action_event_id: Optional[str] = None
    observation_event_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckpointStore:
    """
    Quản lý lưu trữ, truy xuất và quay lui Checkpoint (Time-Travel Backtracking):
    - Hỗ trợ lưu trữ trong bộ nhớ và ghi nhận sự kiện vào CognitiveEventStore.
    - Tìm kiếm Checkpoint tối ưu nhất để khôi phục khi Re-plan.
    """

    def __init__(self):
        self._checkpoints: Dict[str, List[StepCheckpoint]] = {}  # mission_id -> list[StepCheckpoint]

    def create_checkpoint(
        self,
        mission_id: str,
        step_id: str,
        step_index: int,
        status: str,
        evidence: Any,
        action_name: str = "",
        trace_id: str = "trace_default",
    ) -> StepCheckpoint:
        """Tạo và lưu trữ một Checkpoint bất biến cho bước vừa chạy."""
        # 1. Phát xạ Observation Event vào Event Store
        obs_payload = {
            "step_id": step_id,
            "status": status,
            "action": action_name,
            "evidence_summary": str(evidence)[:300],
        }
        obs_event = event_store.append(
            aggregate_id=mission_id,
            event_type="OBSERVATION_RECORDED",
            payload=obs_payload,
            correlation_id=trace_id,
        )

        # 2. Bóc tách các dữ kiện đã xác minh (Verified Facts) từ evidence
        verified_facts = self._extract_verified_facts(evidence)

        # 3. Tính toán state hash
        encoded_data = json.dumps(
            {"step_id": step_id, "status": status, "facts": verified_facts},
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
        s_hash = hashlib.sha256(encoded_data).hexdigest()[:16]

        cp_id = f"cp_{mission_id}_{step_index}_{s_hash[:8]}"
        cp = StepCheckpoint(
            checkpoint_id=cp_id,
            mission_id=mission_id,
            step_id=step_id,
            step_index=step_index,
            status=status,
            state_hash=s_hash,
            verified_facts=verified_facts,
            evidence_snapshot={step_id: evidence},
            observation_event_id=obs_event.event_id,
        )

        if mission_id not in self._checkpoints:
            self._checkpoints[mission_id] = []
        self._checkpoints[mission_id].append(cp)

        # 4. Phát xạ sự kiện Checkpoint Committed
        event_store.append(
            aggregate_id=mission_id,
            event_type="STEP_CHECKPOINT_COMMITTED",
            payload={"checkpoint_id": cp_id, "step_id": step_id, "status": status, "state_hash": s_hash},
            causation_id=obs_event.event_id,
            correlation_id=trace_id,
        )

        return cp

    def get_checkpoints(self, mission_id: str) -> List[StepCheckpoint]:
        return self._checkpoints.get(mission_id, [])

    def get_best_checkpoint(self, mission_id: str) -> Optional[StepCheckpoint]:
        """
        Tìm Checkpoint tốt nhất gần nhất:
        - Ưu tiên status == SUCCESS và có số lượng verified facts nhiều nhất.
        - Nếu không có SUCCESS, chọn PARTIAL có facts lớn nhất.
        """
        cps = self._checkpoints.get(mission_id, [])
        if not cps:
            return None

        # Sắp xếp: Ưu tiên SUCCESS > PARTIAL, facts count giảm dần, timestamp mới nhất
        def _score(cp: StepCheckpoint) -> Tuple[int, int, float]:
            status_weight = 2 if cp.status.upper() == "SUCCESS" else (1 if cp.status.upper() == "PARTIAL" else 0)
            return (status_weight, len(cp.verified_facts), cp.timestamp)

        sorted_cps = sorted(cps, key=_score, reverse=True)
        return sorted_cps[0]

    def backtrack_to_best_checkpoint(
        self,
        mission_id: str,
        trace_id: str = "trace_replan",
    ) -> Tuple[Optional[StepCheckpoint], Dict[str, Any], List[str]]:
        """
        Thực hiện Time-Travel Backtracking khi Critic phán quyết thiếu bằng chứng:
        - Quay lui về Checkpoint hợp lệ tốt nhất.
        - Trả về: (best_checkpoint, consolidated_evidence, consolidated_facts)
        """
        best_cp = self.get_best_checkpoint(mission_id)
        if not best_cp:
            return None, {}, []

        # Hợp nhất tất cả các evidence và facts từ các checkpoint thành công trước mốc đó
        consolidated_evidence: Dict[str, Any] = {}
        all_facts: List[str] = []

        cps = self._checkpoints.get(mission_id, [])
        for cp in cps:
            if cp.timestamp <= best_cp.timestamp and cp.status.upper() in ("SUCCESS", "PARTIAL"):
                consolidated_evidence.update(cp.evidence_snapshot)
                for f in cp.verified_facts:
                    if f not in all_facts:
                        all_facts.append(f)

        # Phát xạ sự kiện Backtracking vào Event Store
        event_store.append(
            aggregate_id=mission_id,
            event_type="CONTEXT_BACKTRACKED",
            payload={
                "target_checkpoint_id": best_cp.checkpoint_id,
                "target_step_id": best_cp.step_id,
                "retained_facts_count": len(all_facts),
            },
            correlation_id=trace_id,
        )

        return best_cp, consolidated_evidence, all_facts

    def _extract_verified_facts(self, evidence: Any) -> List[str]:
        """Trích xuất danh sách các dữ kiện hoặc trích dẫn đã xác nhận."""
        facts: List[str] = []
        if isinstance(evidence, dict):
            # Nếu là kết quả web search hoặc multi query có trích đoạn
            results = evidence.get("results") or []
            for r in results:
                if isinstance(r, dict):
                    title = r.get("title") or ""
                    url = r.get("url") or ""
                    snippet = r.get("snippet") or r.get("content") or ""
                    if title and snippet:
                        facts.append(f"[{title}] ({url}): {snippet[:150]}")
            if evidence.get("output") and isinstance(evidence.get("output"), str):
                lines = evidence["output"].splitlines()
                for l in lines:
                    if l.strip().startswith(("[1]", "[2]", "[3]", "[4]", "[5]", "###", "- ")):
                        facts.append(l.strip()[:200])
        elif isinstance(evidence, str):
            for l in evidence.splitlines():
                if l.strip().startswith(("[", "-", "*", "URL:")):
                    facts.append(l.strip()[:200])

        return facts[:10]  # Giới hạn top 10 facts tiêu biểu


# Global Checkpoint Store Singleton
checkpoint_store = CheckpointStore()
