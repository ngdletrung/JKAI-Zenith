"""
JKAI ZENITH — COGNITIVE DOMAIN: MISSION LEDGER
File: core/cognitive/mission_ledger.py

Append-only event-sourced log of mission lifecycle events.
Durable source of historical truth for Mission Replay, Audit, and Recovery.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import uuid


@dataclass
class MissionLedgerEntry:
    """Immutable entry in MissionLedger."""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mission_id: str = ""
    attempt_id: str = ""
    event_type: str = "MissionCreated"   # "MissionCreated" | "LeaseGranted" | "ExecutionCompleted" | "EvaluationCompleted" | "ReplanRequested"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MissionLedger:
    """Append-only Event-Sourced Mission History Ledger."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._entries: List[MissionLedgerEntry] = []

    def append(self, event_type: str, payload: Dict[str, Any], attempt_id: str = "") -> MissionLedgerEntry:
        entry = MissionLedgerEntry(
            mission_id=self.mission_id,
            attempt_id=attempt_id,
            event_type=event_type,
            payload=payload
        )
        self._entries.append(entry)
        return entry

    def get_entries(self) -> List[MissionLedgerEntry]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)
