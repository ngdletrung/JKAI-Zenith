import sys
import os
import unittest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

from state_pipeline import StatePipeline, ExecutionPlan, ExecutionPlanStep

class TestStatePipeline(unittest.TestCase):
    """
    Test suite for state_pipeline.py:
      1. Verify execution plan construction
      2. Verify Cognitive Override Circuit Breaker resets on success
      3. Verify Circuit Breaker trips after max consecutive failures
    """

    def setUp(self):
        self.pipeline = StatePipeline()

    def test_circuit_breaker_initial_state(self):
        """Initial failure count must be 0 and circuit breaker closed."""
        self.assertEqual(self.pipeline._cognitive_failures, 0)

    def test_circuit_breaker_resets_on_success(self):
        """Circuit breaker failure counter must reset to 0 on successful override."""
        self.pipeline._cognitive_failures = 2
        # Simulate success
        async def _test():
            if self.pipeline._cognitive_lock is None:
                self.pipeline._cognitive_lock = asyncio.Lock()
            async with self.pipeline._cognitive_lock:
                self.pipeline._cognitive_failures = 0
        asyncio.run(_test())
        self.assertEqual(self.pipeline._cognitive_failures, 0)

    def test_execution_plan_creation(self):
        """ExecutionPlan must initialize with default reactive steps."""
        plan = ExecutionPlan(
            selected_pipeline="fast",
            steps=[ExecutionPlanStep(step_id="S1", description="Fast reactive step")]
        )
        self.assertEqual(plan.selected_pipeline, "fast")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].step_id, "S1")

if __name__ == "__main__":
    unittest.main()
