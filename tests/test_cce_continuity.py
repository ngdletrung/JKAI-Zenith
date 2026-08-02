import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import unittest
from core.os.ucws import (
    get_ucws,
    reduce_world_state,
    replay_world_state,
    UCWS
)
from core.kernel.cce import CognitiveContinuityEngine

class TestCCEContinuity(unittest.TestCase):
    def setUp(self):
        self.mission_id = "mission_cce_e2e_001"
        self.cce = CognitiveContinuityEngine(self.mission_id)

    def test_a_state_integrity_and_reducer(self):
        ucws_v0 = get_ucws(self.mission_id)
        v0 = ucws_v0.world_version

        event = {
            "event_type": "ENTITY_ADDED",
            "payload": {
                "entity_id": "file:contract_v1.docx",
                "data": {"name": "contract_v1.docx", "type": "file", "status": "draft", "updated_at": time.time()}
            }
        }
        ucws_v1 = reduce_world_state(ucws_v0, event)
        self.assertEqual(ucws_v1.world_version, v0 + 1)
        self.assertIn("file:contract_v1.docx", ucws_v1.current_state.entities)

    def test_b_replayability(self):
        events = [
            {"event_type": "ENTITY_ADDED", "payload": {"entity_id": "file:report.pdf", "data": {"name": "report.pdf", "type": "file"}}},
            {"event_type": "STATE_CHANGED", "payload": {"stage": "AUDITED"}}
        ]
        replayed = replay_world_state("mission_replay_test", events)
        self.assertEqual(replayed.world_version, 102)
        self.assertIn("file:report.pdf", replayed.current_state.entities)
        self.assertEqual(replayed.current_state.state.get("stage"), "AUDITED")

    def test_c_causality_graph_edge(self):
        event = {
            "event_type": "CAUSALITY_RECORDED",
            "payload": {
                "cause": "GPU VRAM > 7.5GB",
                "action": "Switch Qwen3.5 -> Qwen3",
                "observation": "TPS +42%",
                "effect": "Latency decreased",
                "confidence": 0.91
            }
        }
        ucws = reduce_world_state(self.cce.ucws, event)
        causal_graph = ucws.provenance.causality_graph
        self.assertTrue(len(causal_graph) > 0)
        latest_causal = causal_graph[-1]
        self.assertEqual(latest_causal["cause"], "GPU VRAM > 7.5GB")
        self.assertEqual(latest_causal["confidence"], 0.91)

    def test_d_decision_boundary_risk_gate(self):
        # 1. Low risk tool call -> ACT (SUCCESS)
        res_low = self.cce.execute_cognitive_cycle("cycle_1", "Search web", "search_web", {"query": "python"}, "Results found")
        self.assertEqual(res_low["status"], "SUCCESS")

        # 2. High risk tool call -> HUMAN GATE (INTERRUPTED)
        res_high = self.cce.execute_cognitive_cycle("cycle_2", "Delete directory", "run_command", {"command": "rm -rf /tmp/data"}, "Output")
        self.assertEqual(res_high["status"], "INTERRUPTED_AWAITING_APPROVAL")

    def test_e_multi_cycle_cognitive_continuity(self):
        """
        Cognitive Continuity Test:
        Cycle 1: Add contract file entity to UCWS
        Cycle 2: Resolve implicit reference 'file đó' purely from UCWS without raw chat history
        """
        # Cycle 1: Add entity to UCWS
        reduce_world_state(self.cce.ucws, {
            "event_type": "ENTITY_ADDED",
            "payload": {
                "entity_id": "file:hop_dong_2026.docx",
                "data": {"name": "hop_dong_2026.docx", "type": "file", "status": "draft", "updated_at": time.time()}
            }
        })

        # Cycle 2: Resolve implicit entity reference 'file đó'
        resolved_entity = self.cce.resolve_entity_reference("file đó có lỗi gì không?")
        self.assertIsNotNone(resolved_entity)
        self.assertEqual(resolved_entity.get("name"), "hop_dong_2026.docx")

if __name__ == "__main__":
    unittest.main()
