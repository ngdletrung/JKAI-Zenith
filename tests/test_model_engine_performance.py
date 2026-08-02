import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from core.utils.engine import engine

class TestModelEnginePerformance(unittest.TestCase):
    """
    🧠 [MODEL-ENGINE-PERFORMANCE-TEST]: Thẩm định Bộ Khung Chạy Model Core Engine.
    """
    def test_persistent_async_client_pool(self):
        client1 = engine._get_client()
        client2 = engine._get_client()
        self.assertIsNotNone(client1)
        self.assertFalse(client1.is_closed)
        self.assertIs(client1, client2) # Persistent Client Singleton Instance

    def test_role_config_resolution(self):
        receptionist_cfg = engine.get_role_config("RECEPTIONIST")
        planner_cfg = engine.get_role_config("PLANNER")
        critic_cfg = engine.get_role_config("CRITIC")
        
        self.assertIsNotNone(receptionist_cfg)
        self.assertIsNotNone(planner_cfg)
        self.assertIsNotNone(critic_cfg)

if __name__ == "__main__":
    unittest.main()
