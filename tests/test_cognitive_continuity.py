import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import unittest
from core.os.world_state import (
    get_mission_world_state,
    update_mission_world_state,
    record_causality_link,
    MissionWorldState
)
from core.kernel.cognitive_loop import CognitiveLoop

class TestCognitiveContinuity(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_continuity_001"

    def test_7_dimensional_world_state(self):
        m_state = get_mission_world_state(self.task_id)
        self.assertIsInstance(m_state, MissionWorldState)

        # 1. Entities
        update_mission_world_state(self.task_id, "entities", {"active_file": "main.py"})
        # 2. Relationships
        update_mission_world_state(self.task_id, "relationships", {"step_01": ["step_02"]})
        # 3. State Data
        update_mission_world_state(self.task_id, "state_data", {"stage": "DRAFTING"})
        # 4. Events
        update_mission_world_state(self.task_id, "events", [{"event": "BOOT"}])
        # 5. Causality
        record_causality_link(self.task_id, cause="search_web", effect="Got news results")
        # 6. Uncertainty
        update_mission_world_state(self.task_id, "uncertainty", {"risk_score": 0.1})

        refreshed = get_mission_world_state(self.task_id)
        self.assertEqual(refreshed.entities.get("active_file"), "main.py")
        self.assertEqual(refreshed.state_data.get("stage"), "DRAFTING")
        self.assertEqual(len(refreshed.causality), 1)
        self.assertEqual(refreshed.causality[0]["cause"], "search_web")
        self.assertTrue(len(refreshed.temporal_changes) >= 5)

    def test_cognitive_loop_world_state_integration(self):
        loop = CognitiveLoop(self.task_id, "Kiểm tra chu trình tự trị nhận thức")
        self.assertEqual(loop.task_id, self.task_id)

if __name__ == "__main__":
    unittest.main()
