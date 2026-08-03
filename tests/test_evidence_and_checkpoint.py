"""
JKAI ZENITH — TEST SUITE: EVIDENCE VALIDATOR & CHECKPOINT MANAGER
tests/test_evidence_and_checkpoint.py
"""

import pytest
import os
from core.evaluation.evidence_validator import EvidenceValidator, EvidenceGraph
from core.cognitive.checkpoint_manager import CheckpointManager, MissionCheckpoint


class TestEvidenceAndCheckpoint:

    def test_evidence_validator_graph_creation(self):
        validator = EvidenceValidator()
        tools = [
            {"tool_name": "python_eval", "status": "success", "output": "42"},
            {"tool_name": "bash_exec", "status": "failed", "output": "error"}
        ]
        graph = validator.build_evidence_graph(
            mission_id="m_ev_001",
            output_text="Executed python and bash tools",
            tool_results=tools
        )

        assert graph.mission_id == "m_ev_001"
        assert len(graph.claims) == 3
        assert len(graph.evidence) == 2
        assert graph.grounding_ratio == 1/3

    def test_checkpoint_manager_save_and_load(self, tmp_path):
        chk_dir = str(tmp_path / "checkpoints")
        manager = CheckpointManager(checkpoint_dir=chk_dir)

        chk = MissionCheckpoint(
            checkpoint_id="chk_001",
            mission_id="m_chk_100",
            contract_id="c_100",
            state="RUNNING",
            ledger_position=14,
            active_plan=[{"step": 1, "task": "analyze"}],
            completed_tasks=["step_0"]
        )

        filepath = manager.save_checkpoint(chk)
        assert os.path.exists(filepath)

        loaded = manager.load_checkpoint("m_chk_100")
        assert loaded is not None
        assert loaded.checkpoint_id == "chk_001"
        assert loaded.ledger_position == 14
        assert loaded.completed_tasks == ["step_0"]
