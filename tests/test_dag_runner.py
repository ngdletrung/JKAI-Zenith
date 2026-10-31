import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.dag_runner import build_dag_waves

class TestDAGRunner(unittest.TestCase):
    def test_linear_steps(self):
        steps = [
            {"id": "step_01", "depends_on": []},
            {"id": "step_02", "depends_on": ["step_01"]},
            {"id": "step_03", "depends_on": ["step_02"]}
        ]
        waves = build_dag_waves(steps)
        self.assertEqual(len(waves), 3)
        self.assertEqual([s["id"] for s in waves[0]], ["step_01"])
        self.assertEqual([s["id"] for s in waves[1]], ["step_02"])
        self.assertEqual([s["id"] for s in waves[2]], ["step_03"])

    def test_parallel_independent_steps(self):
        steps = [
            {"id": "step_01", "depends_on": []},
            {"id": "step_02", "depends_on": []},
            {"id": "step_03", "depends_on": ["step_01", "step_02"]}
        ]
        waves = build_dag_waves(steps)
        self.assertEqual(len(waves), 2)
        # Wave 0 has step_01 and step_02 in parallel
        wave0_ids = {s["id"] for s in waves[0]}
        self.assertEqual(wave0_ids, {"step_01", "step_02"})
        # Wave 1 has step_03
        self.assertEqual([s["id"] for s in waves[1]], ["step_03"])

    def test_invalid_cycle_fails_closed(self):
        steps = [
            {"id": "step_01", "depends_on": ["step_02"]},
            {"id": "step_02", "depends_on": ["step_01"]}
        ]
        with self.assertRaises(ValueError):
            build_dag_waves(steps)

    def test_unknown_dependency_fails_closed(self):
        with self.assertRaises(ValueError):
            build_dag_waves([{"id": "step_01", "depends_on": ["missing"]}])

if __name__ == "__main__":
    unittest.main()
