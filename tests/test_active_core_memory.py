import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.active_core_memory import update_core_memory, get_core_memory, get_all_blocks_prompt

class TestActiveCoreMemory(unittest.TestCase):
    def setUp(self):
        self.block = "test_master_pref"

    def test_update_and_get_core_memory(self):
        content = "Master prefers concise Markdown format and Vietnamese language."
        updated = update_core_memory(self.block, content)
        self.assertTrue(updated)

        retrieved = get_core_memory(self.block)
        self.assertEqual(retrieved, content)

    def test_get_all_blocks_prompt(self):
        update_core_memory("human_preference", "User likes high performance code.")
        prompt = get_all_blocks_prompt()
        self.assertIn("<core_memory>", prompt)
        self.assertIn("human_preference", prompt)

if __name__ == "__main__":
    unittest.main()
