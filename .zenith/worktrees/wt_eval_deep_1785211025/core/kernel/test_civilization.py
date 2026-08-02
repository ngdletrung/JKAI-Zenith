"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — INTEGRATION & CIVILIZATION TEST SUITE            ║
║   Hệ Thống Kiểm Thử Liên Kết Nhận Thức & Sinh Tồn Nội Môi        ║
╚══════════════════════════════════════════════════════════════════╝
*Kiểm toán Thể chất và Tri thức của Tập đoàn JKAI. 🌌🔬🏢*
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import asyncio

# Đưa thư mục gốc vào sys.path để import chuẩn xác
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 🛡️ GLOBAL MOCKING FOR HOST RUNS (Tránh tắc nghẽn mạng do Redis/Qdrant trên host)
from core.utils.engine import engine
engine.publish_mission_log = MagicMock()

try:
    from core.redis_client import redis_client
    redis_client.get_sync_client = MagicMock(return_value=None)
    redis_client.connect = AsyncMock()
except ImportError:
    pass

from core.kernel.homeostasis import HomeostasisEngine
from core.kernel.civilization_ledger import CivilizationLedger
from core.kernel.surgery_engine import SurgeryEngine, surgery_engine
from core.kernel.state_machine import TaskState, StateTransitionGraph, StateInvariantViolation

class TestCivilizationInfrastructure(unittest.IsolatedAsyncioTestCase):
    """
    🏢 BAN KIỂM TOÁN TẬP ĐOÀN (Civilization Audit Board)
    Tiến hành thẩm định 3 chân kiềng sinh tồn và tri thức của JKAI Zenith:
    1. Cơ chế Cân bằng nội môi (Homeostasis Throttle)
    2. Sổ cái Văn minh Tri thức (Civilization Ledger Qdrant Memory)
    3. Phòng Phẫu thuật Tự chữa lành (Autonomic Surgery Engine)
    """

    async def asyncSetUp(self):
        print("\n" + "="*70)
        print("💼 [BAN KIỂM TOÁN] Khởi động phiên thẩm định kiểm thử hạ tầng...")
        print("="*70)

    async def asyncTearDown(self):
        print("💼 [BAN KIỂM TOÁN] Hoàn tất phiên thẩm định phân khu.")
        print("="*70)

    # ══════════════════════════════════════════════════════════════════
    # THẨM ĐỊNH 1: CÂN BẰNG NỘI MÔI (METABOLIC HOMEOSTASIS)
    # ══════════════════════════════════════════════════════════════════

    @patch("core.kernel.homeostasis.psutil")
    @patch("core.kernel.homeostasis.purge_ollama", new_callable=AsyncMock)
    async def test_homeostasis_throttling(self, mock_purge, mock_psutil):
        """
        🧪 [TEST HOMEOSTASIS]: Kiểm tra cơ chế tự động điều tiết concurrency
        dựa trên trạng thái RAM/CPU thực tế của máy chủ.
        """
        print("\n🩺 [TEST-1] Thẩm định Ban Điều phối Nội môi (Homeostasis):")
        
        # Giả lập 1: Hệ thống khỏe mạnh (RAM 40%, CPU 30%)
        mock_mem = MagicMock()
        mock_mem.percent = 40.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_percent.return_value = 30.0
        
        engine_healthy = HomeostasisEngine(max_ram_percent=85.0, max_cpu_percent=90.0)
        concurrency = await engine_healthy.enforce_homeostasis("t_healthy", "tr_healthy")
        print(f"   -> [Hệ thống khỏe mạnh]: RAM 40% | CPU 30% -> Concurrency định mức: {concurrency}")
        self.assertEqual(concurrency, 8)

        # Giả lập 2: Hệ thống quá tải RAM (RAM 90%, CPU 50%) -> Nguy kịch
        mock_mem.percent = 90.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_percent.return_value = 50.0
        
        concurrency_danger = await engine_healthy.enforce_homeostasis("t_danger", "tr_danger")
        print(f"   -> [Hệ thống quá tải RAM]: RAM 90% | CPU 50% -> Concurrency thắt chặt: {concurrency_danger}")
        self.assertEqual(concurrency_danger, 2)
        mock_purge.assert_called_once() # Phải tự động gọi dọn dẹp VRAM

        # Giả lập 3: Hệ thống chớm báo động (RAM 75%, CPU 40%) -> Cảnh báo trung bình
        mock_mem.percent = 75.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_percent.return_value = 40.0
        
        concurrency_warn = await engine_healthy.enforce_homeostasis("t_warn", "tr_warn")
        print(f"   -> [Hệ thống chớm báo động]: RAM 75% | CPU 40% -> Concurrency trung bình: {concurrency_warn}")
        self.assertEqual(concurrency_warn, 3)

    # ══════════════════════════════════════════════════════════════════
    # THẨM ĐỊNH 2: SỔ CÁI VĂN MINH TRI THỨC (CIVILIZATION LEDGER)
    # ══════════════════════════════════════════════════════════════════

    @patch("core.kernel.civilization_ledger.qdrant_client")
    @patch("core.kernel.civilization_ledger.engine")
    async def test_civilization_ledger_experience(self, mock_engine, mock_qdrant):
        """
        🧪 [TEST LEDGER]: Thử nghiệm chưng cất bài học lịch sử thành công/thất bại,
        lưu trữ dưới dạng vector vào Qdrant và truy vấn tương đồng ngữ nghĩa.
        """
        print("\n🏛️ [TEST-2] Thẩm định Sổ cái Văn minh Tri thức (Civilization Ledger):")

        # Mock LLM sinh bài học và Vector nhúng
        mock_engine.call_chat = AsyncMock(return_value="🎯 BLUEPRINT: Luôn cấu hình `--host 0.0.0.0` để Docker container có thể kết nối ra ngoài.")
        mock_engine.get_embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_qdrant.ensure_collection = AsyncMock()
        mock_qdrant.add_intel = AsyncMock()
        mock_qdrant.search_similar = AsyncMock(return_value=[
            {
                "payload": {
                    "text": "🎯 BLUEPRINT: Luôn cấu hình `--host 0.0.0.0`...",
                    "task_id": "m_prior",
                    "goal": "Config Docker network"
                },
                "score": 0.95
            }
        ])

        ledger = CivilizationLedger()
        
        # 1. Thử ghi nhận một trải nghiệm chiến dịch
        lesson = await ledger.record_experience(
            task_id="m_test_99",
            goal="Thiết lập môi trường Docker chạy N8N và kết nối mạng",
            success_steps=[{"id": "step_1", "tool": "run_command"}],
            failed_steps=[{"id": "step_2", "tool": "run_command", "error": "Connection refused"}],
            judicial_review_notes={"verdict": "Thất bại do sai cấu hình host network."}
        )
        print(f"   -> [Bài học chưng cất thành công]: {lesson}")
        self.assertIsNotNone(lesson)
        mock_qdrant.add_intel.assert_called_once()

        # 2. Thử truy vấn bài học tương đồng cho mục tiêu mới
        retrieved = await ledger.retrieve_analogous_lessons("Docker container networking issue")
        print(f"   -> [Truy lục bài học lịch sử thành công]: Tìm thấy {len(retrieved)} bài học tương hợp.")
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["task_id"], "m_prior")
        self.assertGreater(retrieved[0]["score"], 0.90)

    # ══════════════════════════════════════════════════════════════════
    # THẨM ĐỊNH 3: PHẪU THUẬT TỰ CHỮA LÀNH (AUTONOMIC SURGERY)
    # ══════════════════════════════════════════════════════════════════

    @patch("core.kernel.surgery_engine.engine")
    async def test_self_healing_surgery(self, mock_engine):
        """
        🧪 [TEST SURGERY]: Tạo lỗi cú pháp giả định, chạy phẫu thuật thử nghiệm,
        kiểm tra syntax lâm sàng và xác minh bản vá.
        """
        print("\n🩺 [TEST-3] Thẩm định Phòng Phẫu thuật Mã nguồn (Surgery Engine):")

        # 1. Kiểm tra Syntax checker của Surgery Engine
        invalid_code = "def bad_syntax_function(\n    print('Missing closing parenthesis')"
        ok, msg = SurgeryEngine.verify_syntax(invalid_code, "test_file.py")
        print(f"   -> [Kiểm tra cú pháp lỗi]: Kết quả={ok} | Chi tiết: {msg}")
        self.assertFalse(ok)
        self.assertIn("SyntaxError", msg)

        valid_code = "def good_function():\n    print('Syntax is absolutely perfect!')"
        ok_good, msg_good = SurgeryEngine.verify_syntax(valid_code, "test_file.py")
        print(f"   -> [Kiểm tra cú pháp chuẩn]: Kết quả={ok_good}")
        self.assertTrue(ok_good)

        # 2. Chạy thử nghiệm phẫu thuật tự sửa lỗi một tệp tin giả định
        temp_file = "d:/Docker/JKAI/scratch_test_failing.py"
        os.makedirs(os.path.dirname(temp_file), exist_ok=True)
        
        original_failing_code = (
            "def calculate_total(price, tax):\n"
            "    # Lỗi nghiêm trọng: syntax error do thừa dấu đóng ngoặc\n"
            "    return price * (1 + tax))\n"
        )
        
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(original_failing_code)

        # Mô phỏng LLM đề xuất bản vá chuẩn JSON
        patch_json = {
            "target_content": "    return price * (1 + tax))\n",
            "replacement_content": "    return price * (1 + tax)\n"
        }
        mock_engine.call_chat = AsyncMock(return_value=json.dumps(patch_json))

        # Chạy phẫu thuật
        surgery = SurgeryEngine()
        success = await surgery.attempt_surgery(
            file_path=temp_file,
            error_message="SyntaxError: unmatched ')' near line 3",
            task_id="t_surgery_99",
            trace_id="tr_surgery_99"
        )
        
        print(f"   -> [Kết quả phẫu thuật tự động]: {success}")
        self.assertTrue(success)

        # Đọc lại file xem đã sửa chưa
        with open(temp_file, "r", encoding="utf-8") as f:
            reconstructed_code = f.read()
        print(f"   -> [Mã nguồn sau phẫu thuật]:\n{reconstructed_code}")
        self.assertIn("return price * (1 + tax)\n", reconstructed_code)
        self.assertNotIn("tax))\n", reconstructed_code)

        # Dọn dẹp tệp thử nghiệm
        if os.path.exists(temp_file):
            os.remove(temp_file)

    # ══════════════════════════════════════════════════════════════════
    # THẨM ĐỊNH 4: BIÊN BAN TRẠNG THÁI (STATE INVARIANT GRAPH)
    # ══════════════════════════════════════════════════════════════════

    def test_state_transition_invariants(self):
        """
        🧪 [TEST INVARIANTS]: Đảm bảo đồ thị trạng thái nguyên tử không cho phép
        bất cứ hành vi nhảy vọt trạng thái phi pháp nào.
        """
        print("\n🛤️ [TEST-4] Thẩm định Biên bản Trạng thái (State Invariants):")
        
        # Hợp lệ: RECEIVED -> VALIDATED
        try:
            StateTransitionGraph.validate_transition(TaskState.RECEIVED, TaskState.VALIDATED)
            print("   -> [Hợp lệ]: RECEIVED -> VALIDATED (Đạt)")
        except StateInvariantViolation:
            self.fail("RECEIVED -> VALIDATED should be legal.")

        # Phi pháp: RECEIVED -> EXECUTING (Bỏ qua khâu kế hoạch, chính sách)
        with self.assertRaises(StateInvariantViolation):
            print("   -> [Kiểm soát phi pháp]: RECEIVED -> EXECUTING (Bị chặn đứng chuẩn xác)")
            StateTransitionGraph.validate_transition(TaskState.RECEIVED, TaskState.EXECUTING)

        # Phi pháp: Đã rơi vào trạng thái Terminal (COMPLETED) thì không được thoát ra
        with self.assertRaises(StateInvariantViolation):
            print("   -> [Kiểm soát Terminal]: COMPLETED -> RETRYING (Bị chặn đứng chuẩn xác)")
            StateTransitionGraph.validate_transition(TaskState.COMPLETED, TaskState.RETRYING)


if __name__ == "__main__":
    unittest.main()
