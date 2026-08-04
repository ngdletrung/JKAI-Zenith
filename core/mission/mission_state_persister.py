"""
JKAI ZENITH — PRODUCTION HARDENING P1: CRASH / RESUME PERSISTENCE (v2.1)
File: core/mission/mission_state_persister.py

Lưu trữ và Khôi phục Trạng thái MissionState & TaskGraph khi process bị kill đột ngột giữa chừng.
Cho phép tiếp tục tác chiến từ nút nhiệm vụ dở dang (ví dụ: Task 13/100) mà không làm lại từ đầu.
"""

from __future__ import annotations
import os
import json
import logging
from typing import Dict, Any, Optional

from core.contracts.cognitive_contract import IdentityChain, MissionDefinition, DeliverableSpec
from core.contracts.verification_contract import RuntimeState
from core.mission.mission_registry import MissionRegistry

logger = logging.getLogger("jkai.mission.persister")


class MissionStatePersister:
    """Bộ Lưu Trữ & Khôi Phục Trạng Thái Tác Chiến Tự Chủ (P1 Persistence)."""

    STORAGE_DIR = "data/persisted_missions"

    @classmethod
    def persist_snapshot(
        cls,
        mission: MissionDefinition,
        state: RuntimeState,
        current_task_index: int = 0,
        completed_tasks: Optional[list] = None
    ) -> str:
        """
        Lưu Snapshot trạng thái tác chiến xuống đĩa.
        """
        os.makedirs(cls.STORAGE_DIR, exist_ok=True)
        mid = mission.identity.mission_id
        filepath = os.path.join(cls.STORAGE_DIR, f"{mid}.json")

        payload = {
            "identity": {
                "request_id": mission.identity.request_id,
                "mission_id": mission.identity.mission_id,
                "plan_id": mission.identity.plan_id,
                "task_id": mission.identity.task_id,
                "attempt_id": mission.identity.attempt_id,
                "execution_id": mission.identity.execution_id,
                "observation_id": mission.identity.observation_id,
                "verification_id": mission.identity.verification_id,
            },
            "objective": mission.objective,
            "deliverable_format": mission.expected_output.format,
            "runtime_state": state.value,
            "current_task_index": current_task_index,
            "completed_tasks": completed_tasks or []
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 [P1-PERSISTENCE]: Persisted snapshot for Mission ID={mid} (Task #{current_task_index}) -> '{filepath}'")
        return filepath

    @classmethod
    def restore_snapshot(cls, mission_id: str) -> Optional[Dict[str, Any]]:
        """
        Khôi phục Snapshot trạng thái tác chiến sau khi process khởi động lại.
        """
        filepath = os.path.join(cls.STORAGE_DIR, f"{mission_id}.json")
        if not os.path.exists(filepath):
            logger.warning(f"⚠️ [P1-PERSISTENCE]: No persisted snapshot found for Mission ID={mission_id}")
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"🔄 [P1-RESUME]: Restored snapshot for Mission ID={mission_id} (Resuming from Task #{data['current_task_index'] + 1})")
        return data
