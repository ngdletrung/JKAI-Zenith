import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import asyncio

from core.kernel.subagent_workspace import subagent_workspace_manager
from core.kernel.subagent_engine import subagent_engine
from core.kernel.event_waiter import event_waiter_manager
from core.kernel.interactive_protocol import interactive_protocol
from core.utils.image_renderer import image_renderer

class TestE2ESovereignPipeline(unittest.TestCase):
    """
    🏛️ [E2E-INTEGRATION-TEST]: Bộ kiểm thử tích hợp End-to-End kiểm chứng 4 Trụ cột Kĩ thuật Sản xuất.
    """
    def test_pillar_1_workspace_isolation_and_inbox(self):
        # 1. Thử tạo Workspace Cô lập
        sub_id = "test_e2e_sub_001"
        ws_path = subagent_workspace_manager.get_workspace(sub_id)
        self.assertTrue(ws_path.exists())
        self.assertTrue((ws_path / "artifacts").exists())

        # 2. Thử gửi và lấy inbox
        subagent_engine.send_message(sub_id, "Tác vụ kiểm thử tích hợp")
        inbox = subagent_engine.fetch_inbox(sub_id)
        self.assertIsInstance(inbox, list)

        # 3. Dọn dẹp Workspace
        cleanup_ok = subagent_workspace_manager.cleanup_workspace(sub_id)
        self.assertTrue(cleanup_ok)

    def test_pillar_2_async_interactive_event_waiter(self):
        async def _run_waiter_test():
            q_id = "q_test_123"
            # Giả lập luồng 1: Agent chờ Master phản hồi với Timeout 2s
            waiter_task = asyncio.create_task(
                event_waiter_manager.wait_for_selection(q_id, timeout_seconds=2.0, default_selection="FastAPI")
            )
            # Giả lập luồng 2: Master bấm chọn nút trên UI sau 0.1s
            await asyncio.sleep(0.1)
            resolved = event_waiter_manager.resolve_waiter(q_id, {"selection": "FastAPI", "status": "user_selected"})
            self.assertTrue(resolved)

            res = await waiter_task
            self.assertEqual(res["selection"], "FastAPI")

        asyncio.run(_run_waiter_test())

    def test_pillar_3_diagram_and_ui_mockup_rendering(self):
        # 1. Sơ đồ kiến trúc có Cạnh nối (Edges/Arrows)
        nodes = ["Frontend UI", "API Gateway", "Subagent Swarm", "Redis EventBus"]
        edges = [("Frontend UI", "API Gateway"), ("API Gateway", "Subagent Swarm"), ("Subagent Swarm", "Redis EventBus")]
        diag_res = image_renderer.render_architecture_diagram(nodes, edges, "e2e_arch.svg")
        self.assertEqual(diag_res["status"], "success")

        # 2. Phác thảo giao diện UI Mockup
        ui_comps = [
            {"type": "button", "label": "Chạy Mission"},
            {"type": "input", "label": "Nhập mục tiêu"},
            {"type": "card", "label": "Telemetry Dashboard", "description": "CPU: 5% | Memory: OK"}
        ]
        ui_res = image_renderer.render_ui_mockup("Production Dashboard", ui_comps, "e2e_ui.svg")
        self.assertEqual(ui_res["status"], "success")

if __name__ == "__main__":
    unittest.main()
