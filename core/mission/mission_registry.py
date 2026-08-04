"""
JKAI ZENITH — MISSION LAYER: MISSION REGISTRY & STATE MACHINE (v2.1)
File: core/mission/mission_registry.py

Bộ lưu trữ & Quản lý Máy Trạng Thái RuntimeState (State Machine Coordinator).
Theo dõi chuyển trạng thái từ RECEIVED -> COGNIZED -> MISSIONED -> PLANNED -> RESOLVED -> EXECUTING -> OBSERVED -> VERIFYING -> DELIVERED / ABORTED.
"""

from __future__ import annotations
import logging
import threading
from typing import Dict, Optional, List

from core.contracts.cognitive_contract import MissionDefinition
from core.contracts.verification_contract import RuntimeState

logger = logging.getLogger("jkai.mission.registry")


class MissionRegistry:
    """Quản lý lưu trữ & Chuyển trạng thái RuntimeState."""

    _lock = threading.RLock()
    _missions: Dict[str, MissionDefinition] = {}
    _states: Dict[str, RuntimeState] = {}
    _state_history: Dict[str, List[RuntimeState]] = {}

    @classmethod
    def register_mission(cls, mission: MissionDefinition) -> None:
        mid = mission.identity.mission_id
        with cls._lock:
            cls._missions[mid] = mission
            cls._states[mid] = RuntimeState.MISSIONED
            cls._state_history[mid] = [RuntimeState.RECEIVED, RuntimeState.COGNIZED, RuntimeState.MISSIONED]
        logger.info(f"📋 [MISSION-REGISTRY]: Registered Mission ID={mid}")

    @classmethod
    def transition_state(cls, mission_id: str, new_state: RuntimeState) -> RuntimeState:
        with cls._lock:
            current = cls._states.get(mission_id, RuntimeState.RECEIVED)
            
            # Khóa cứng 2 Terminal States: Tuyệt đối không transition ra khỏi DELIVERED hoặc ABORTED
            if current in (RuntimeState.DELIVERED, RuntimeState.ABORTED):
                logger.warning(f"⛔ [STATE-MACHINE-DENY]: Mission ID={mission_id} is in Terminal State {current.value}. Transition to {new_state.value} BLOCKED.")
                return current

            cls._states[mission_id] = new_state
            cls._state_history.setdefault(mission_id, []).append(new_state)
            logger.info(f"🔄 [STATE-MACHINE]: Mission ID={mission_id} transition {current.value} -> {new_state.value}")
            return new_state

    @classmethod
    def get_state(cls, mission_id: str) -> RuntimeState:
        with cls._lock:
            return cls._states.get(mission_id, RuntimeState.RECEIVED)
