"""
JKAI ZENITH — COGNITIVE DOMAIN: MISSION STATE RECONSTRUCTOR
File: core/cognitive/mission_reconstructor.py

Reconstructs materialized MissionState strictly from an immutable MissionLedger event stream.
Ensures 100% deterministic replay and event-sourced source of truth.
"""

from typing import Dict, Any, Optional, List
from core.contracts import MissionState, MissionContext
from core.cognitive.mission_ledger import MissionLedger, MissionLedgerEntry


class MissionStateReconstructor:
    """Event-sourced state projection engine."""

    def reconstruct(self, ledger: MissionLedger, initial_context: Optional[MissionContext] = None) -> MissionState:
        """Reconstruct current MissionState from event ledger."""
        state = MissionState.IDLE

        for entry in ledger.get_entries():
            evt = entry.event_type
            if evt == "MissionCreated":
                state = MissionState.IDLE

            elif evt in ("ExecutionStarted", "LeaseGranted"):
                state = MissionState.RUNNING
            elif evt == "ReplanRequested":
                state = MissionState.RUNNING
            elif evt == "EvaluationCompleted":
                payload = entry.payload
                if payload.get("succeeded", False):
                    state = MissionState.COMPLETED
                else:
                    state = MissionState.RUNNING
            elif evt == "MissionCompleted":
                state = MissionState.COMPLETED
            elif evt in ("MissionAborted", "MissionFailed"):
                state = MissionState.FAILED

        return state
