import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import asyncio
from core.utils.image_renderer import image_renderer
from core.kernel.interactive_protocol import interactive_protocol
from core.kernel.subagent_engine import subagent_engine

class TestAntigravityParityProduction(unittest.TestCase):
    def test_svg_edge_diagram_rendering(self):
        nodes = ["User", "FastAPI Gateway", "Redis Queue", "AI Executor"]
        edges = [("User", "FastAPI Gateway"), ("FastAPI Gateway", "Redis Queue"), ("Redis Queue", "AI Executor")]
        res = image_renderer.render_architecture_diagram(nodes, edges, "test_arch_edges.svg")
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["file_path"]))
        with open(res["file_path"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("marker-end=", content) # Verified Edge Arrowheads!

    def test_ui_mockup_rendering(self):
        components = [
            {"type": "button", "label": "Kích hoạt Mission"},
            {"type": "input", "label": "Nhập Goal"},
            {"type": "card", "label": "System Telemetry Panel", "description": "CPU: 12% | RAM: 4.2GB"}
        ]
        res = image_renderer.render_ui_mockup("Dashboard Mockup", components, "test_ui_mockup.svg")
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["file_path"]))

    def test_interactive_protocol(self):
        card = interactive_protocol.ask_question(
            question="Master muốn chọn công nghệ nào?",
            options=["FastAPI", "Express"],
            auto_prompt_cli=False
        )
        self.assertEqual(card["type"], "interactive_modal_question")

    def test_subagent_parallel_swarm_lifecycle(self):
        subagent_engine.define_subagent(
            name="tester_bot",
            role="Automated Test Bot",
            system_prompt="You run automated unit tests."
        )
        
        async def _test_async():
            launch_res = await subagent_engine.invoke_subagent(
                "tester_bot", "Run test suite", run_in_background=True
            )
            self.assertEqual(launch_res["status"], "launched")
            sub_id = launch_res["subagent_id"]
            
            # List & Status API
            sub_list = subagent_engine.list_subagents()
            self.assertGreater(len(sub_list["subagents"]), 0)
            
            # Kill API
            kill_res = subagent_engine.kill_subagent(sub_id)
            self.assertEqual(kill_res["status"], "success")

        asyncio.run(_test_async())

if __name__ == "__main__":
    unittest.main()
