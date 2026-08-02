import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.state_checkpoint import save_checkpoint, load_checkpoint, clear_checkpoints

class TestStateCheckpoint(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_99"
        clear_checkpoints(self.task_id)

    def tearDown(self):
        clear_checkpoints(self.task_id)

    def test_save_and_load_checkpoint(self):
        sample_state = {
            "goal": "Viết unit test cho checkpoint",
            "task_id": self.task_id,
            "stage": "ReconStage",
            "skill_dna": "SKILL_RECON_DNA",
            "count": 42
        }
        # Save
        saved = save_checkpoint(self.task_id, "ReconStage", sample_state)
        self.assertTrue(saved)

        # Load
        loaded = load_checkpoint(self.task_id, "ReconStage")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["goal"], sample_state["goal"])
        self.assertEqual(loaded["count"], 42)

    def test_clear_checkpoints(self):
        save_checkpoint(self.task_id, "Stage1", {"a": 1})
        save_checkpoint(self.task_id, "Stage2", {"b": 2})

        clear_checkpoints(self.task_id)

        self.assertIsNone(load_checkpoint(self.task_id, "Stage1"))
        self.assertIsNone(load_checkpoint(self.task_id, "Stage2"))

if __name__ == "__main__":
    unittest.main()
