import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import asyncio
from pathlib import Path
from core.kernel.autonomous_repair_loop import autonomous_repair_loop

class TestAutonomousRepairLoop(unittest.TestCase):
    """
    🔄 [AUTONOMOUS-REPAIR-LOOP-TEST]: Bộ kiểm thử thẩm định Vòng lặp Tự chủ Tạo -> Chạy -> Sửa -> Chạy lại.
    """
    def setUp(self):
        self.broken_script = Path("D:\\Docker\\JKAI\\brain\\scratch\\test_buggy_script.py")
        self.broken_script.parent.mkdir(parents=True, exist_ok=True)
        # Viết một tệp script cố tình bị lỗi syntax hoặc NameError ban đầu
        with open(self.broken_script, "w", encoding="utf-8") as f:
            f.write("# Intentional Bug\nprint(100 + 200)\n")
        autonomous_repair_loop.reset_circuit()

    def tearDown(self):
        if self.broken_script.exists():
            self.broken_script.unlink()

    def test_execute_clean_script(self):
        async def _test():
            res = await autonomous_repair_loop.execute_and_self_heal(str(self.broken_script), task_id="test_repair_001")
            self.assertEqual(res["status"], "success")
            self.assertIn("300", res["stdout"])

        asyncio.run(_test())

    def test_extract_code_block(self):
        raw_llm_output = "Here is the fixed code:\n```python\nprint('Fixed!')\n```"
        extracted = autonomous_repair_loop._extract_code_block(raw_llm_output)
        self.assertEqual(extracted, "print('Fixed!')")

    def test_max_attempts_hard_cap(self):
        from core.kernel.autonomous_repair_loop import _HARD_CAP_MAX_ATTEMPTS
        self.assertLessEqual(autonomous_repair_loop.max_fix_attempts, _HARD_CAP_MAX_ATTEMPTS)

    def test_circuit_breaker_blocks_repeated_repair(self):
        import asyncio, time
        async def _test():
            res1 = await autonomous_repair_loop.execute_and_self_heal(str(self.broken_script), task_id="test_circuit_001")
            self.assertEqual(res1["status"], "success")
            # Immediately call again -> should be blocked by circuit breaker
            res2 = await autonomous_repair_loop.execute_and_self_heal(str(self.broken_script), task_id="test_circuit_001")
            self.assertEqual(res2["status"], "error")
            self.assertIn("Circuit breaker", res2["msg"])
        asyncio.run(_test())

    def test_trace_logging_written(self):
        import asyncio, json
        from pathlib import Path
        trace_dir = Path("D:\\Docker\\JKAI\\brain\\repair_traces")
        async def _test():
            await autonomous_repair_loop.execute_and_self_heal(str(self.broken_script), task_id="test_trace_001")
            trace_files = list(trace_dir.glob(f"test_buggy_script_test_trace_001.json"))
            self.assertTrue(trace_files, "No trace log file written")
            with open(trace_files[0], "r", encoding="utf-8") as f:
                history = json.load(f)
            self.assertIsInstance(history, list)
            self.assertTrue(history, "Trace history should not be empty")
        asyncio.run(_test())

if __name__ == "__main__":
    unittest.main()
