import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.tool_masker import mask_tools

class TestToolMasker(unittest.TestCase):
    def setUp(self):
        self.mock_tools = [
            {"name": "search_web", "description": "Search Google"},
            {"name": "read_url_content", "description": "Fetch webpage"},
            {"name": "view_file", "description": "Read file"},
            {"name": "replace_file_content", "description": "Edit file"},
            {"name": "run_command", "description": "Run shell command"},
            {"name": "manage_task", "description": "Manage task"},
        ]

    def test_greeting_masks_to_zero(self):
        tools = mask_tools(goal="Xin chào", intent="SOCIAL", skill="GREETING", all_tools=self.mock_tools)
        self.assertEqual(len(tools), 0)

    def test_web_search_masking(self):
        tools = mask_tools(goal="tìm kiếm tin tức AI", skill="SEARCH_WEB_GLOBAL", all_tools=self.mock_tools)
        tool_names = [t["name"] for t in tools]
        self.assertIn("search_web", tool_names)
        self.assertNotIn("run_command", tool_names)

    def test_file_view_masking(self):
        tools = mask_tools(goal="xem file core.py", all_tools=self.mock_tools)
        tool_names = [t["name"] for t in tools]
        self.assertIn("view_file", tool_names)

    def test_shell_command_masking(self):
        tools = mask_tools(goal="chạy lệnh docker ps", all_tools=self.mock_tools)
        tool_names = [t["name"] for t in tools]
        self.assertIn("run_command", tool_names)

if __name__ == "__main__":
    unittest.main()
