"""
JKAI ZENITH — COGNITIVE DOMAIN: CHECKPOINT MANAGER
File: core/cognitive/checkpoint_manager.py

Manages durable MissionCheckpoints for Long-Horizon Autonomous Missions.
Enables crash recovery, pause/resume, and long-running continuation across restarts.
Zero serialization of transient LLM thoughts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json
import os
import time
from core.contracts import MissionContract, MissionState


@dataclass
class MissionCheckpoint:
    """Durable checkpoint artifact for long-horizon mission persistence."""
    checkpoint_id: str
    mission_id: str
    contract_id: str
    state: str
    ledger_position: int
    active_plan: List[Dict[str, Any]] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class CheckpointManager:
    """Durable disk-backed Checkpoint Manager."""

    def __init__(self, checkpoint_dir: str = ".zenith/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def save_checkpoint(self, checkpoint: MissionCheckpoint) -> str:
        """Persist checkpoint to JSON file."""
        filepath = os.path.join(self.checkpoint_dir, f"{checkpoint.mission_id}_chk.json")
        data = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "mission_id": checkpoint.mission_id,
            "contract_id": checkpoint.contract_id,
            "state": checkpoint.state,
            "ledger_position": checkpoint.ledger_position,
            "active_plan": checkpoint.active_plan,
            "completed_tasks": checkpoint.completed_tasks,
            "timestamp": checkpoint.timestamp,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

    def load_checkpoint(self, mission_id: str) -> Optional[MissionCheckpoint]:
        """Load durable checkpoint from disk."""
        filepath = os.path.join(self.checkpoint_dir, f"{mission_id}_chk.json")
        if not os.path.exists(filepath):
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return MissionCheckpoint(
            checkpoint_id=data["checkpoint_id"],
            mission_id=data["mission_id"],
            contract_id=data["contract_id"],
            state=data["state"],
            ledger_position=data["ledger_position"],
            active_plan=data.get("active_plan", []),
            completed_tasks=data.get("completed_tasks", []),
            timestamp=data.get("timestamp", time.time())
        )
