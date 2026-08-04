# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/scheduler.py
# - Role: Mission Lifecycle Workflow State Machine
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import logging
from .schema import MissionState

logger = logging.getLogger("JKAI.MissionScheduler")

class MissionScheduler:
    """Manages lifecycle transitions of a mission."""
    
    ALLOWED_TRANSITIONS = {
        "READY": {"RUNNING", "FAILED"},
        "RUNNING": {"WAITING", "BLOCKED", "SUCCESS", "FAILED"},
        "WAITING": {"RUNNING", "FAILED"},
        "BLOCKED": {"RUNNING", "FAILED"},
        "SUCCESS": set(),
        "FAILED": set()
    }

    def transition_to(self, state: MissionState, target_lifecycle: str, reason: str = "") -> bool:
        """Transitions state to a target lifecycle if permitted."""
        current = state.lifecycle
        if target_lifecycle not in self.ALLOWED_TRANSITIONS.get(current, set()):
            logger.error("[LIFECYCLE-ERR] Invalid transition requested: %s -> %s (Reason: %s)", current, target_lifecycle, reason)
            return False

        logger.info("[LIFECYCLE-TRANSITION] %s -> %s | Reason: %s", current, target_lifecycle, reason)
        state.lifecycle = target_lifecycle
        return True
