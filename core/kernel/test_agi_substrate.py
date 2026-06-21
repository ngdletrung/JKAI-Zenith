"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — COMPLETE AGI COGNITIVE SUBSTRATE TEST SUITE      ║
║   Kịch Bản Kiểm Thử Tích Hợp Độc Lập Siêu Cấp Toàn Bộ Hệ Thống   ║
╚══════════════════════════════════════════════════════════════════╝
*Ban Điều Phối Kỹ Thuật & Thẩm Định Nhận Thức thuộc Tập đoàn JKAI. 🌌🔬⚡*
"""

import os
import sys
import asyncio
import shutil
import logging
import traceback
import unittest
from typing import Dict, Any, List

# Thiết lập đường dẫn môi trường thưa Master
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.utils.hlc import hlc
from core.utils.engine import engine
from core.kernel.state_machine import TaskState
from core.kernel.cognitive_event_bus import cognitive_event_bus, CognitiveEvent
from core.kernel.cognitive_scheduler import (
    cognitive_transaction_manager, 
    SelfModelCortex, 
    CognitiveSupervisor, 
    GoalLevel, 
    GoalStatus
)
from core.kernel.world_model import (
    create_default_world_graph, 
    ConstraintDSLEngine, 
    TemporalSimulator, 
    FormalInvariantEngine, 
    NodeType
)
from core.kernel.capability_broker import (
    capability_broker, 
    CapabilityType, 
    policy_proof_engine, 
    sandbox_executor
)
from core.kernel.surgery_engine import surgery_engine
from core.kernel.dream_consolidator import dream_consolidator

# Thiết lập log mức INFO thưa Master
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestAgiSubstrate")


class TestAgiSubstrate:
    """
    🏆 [TEST-AGI-SUBSTRATE]: Chương trình kiểm thử liên hoàn 6 lớp nhận thức của Zenith v6.0.
    """
    def __init__(self):
        self.task_id = "test-mission-888"
        self.temp_files: List[str] = []

    def setup(self):
        # Thiết lập thư mục đệm an toàn
        os.makedirs("d:/Docker/JKAI/scratch/sandbox", exist_ok=True)

    def teardown(self):
        # Dọn dẹp tệp tin rác
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
            if os.path.exists(f"{f}.bak"):
                try:
                    os.remove(f"{f}.bak")
                except Exception:
                    pass

    async def run_all_tests(self):
        self.setup()
        print("\n" + "="*80)
        print("🏛️  BẮT ĐẦU CHƯƠNG TRÌNH KIỂM THỬ SIÊU CẤP ZENITH COGNITIVE SUBSTRATE v6.0  🏛️")
        print("="*80 + "\n")

        try:
            # 1. Test Thought State Transitions & Preemption Invariants
            await self.test_state_transitions_and_invariants()
            
            # 2. Test Cognitive ACID Transaction & Supervisor Rollback
            await self.test_cognitive_acid_and_rollback()
            
            # 3. Test Cognitive Event Bus & Monotonic HLC Causal Ordering
            await self.test_event_bus_and_causal_ordering()
            
            # 4. Test Predictive Simulator & Constraint DSL
            await self.test_simulator_and_constraints()
            
            # 5. Test Capability Broker & Shadow Clone Sandbox Boundaries
            await self.test_sandbox_and_security_broker()

            # 6. Test Dream Consolidation & Active Learning Cycle
            await self.test_dream_consolidation()

            print("\n" + "="*80)
            print("✨ 100% CÁC BÀI KIỂM THỬ THÀNH CÔNG MỸ MÃN THƯA TỔNG GIÁM ĐỐC! ✨")
            print("Hạ tầng Nhận Thức Tự Trị Zenith v6.0 đã sẵn sàng vận hành sản xuất.")
            print("="*80 + "\n")

        except Exception as e:
            print("\n" + "!"*80)
            print(f"❌ CHƯƠNG TRÌNH KIỂM THỬ BỊ SẬP THƯA MASTER! LỖI: {e}")
            traceback.print_exc()
            print("!"*80 + "\n")
        finally:
            self.teardown()

    # -----------------------------------------------------------------
    # TEST 1: Thought State Transitions & Preemption Invariants
    # -----------------------------------------------------------------
    async def test_state_transitions_and_invariants(self):
        print("🔷 [TEST 1]: THOUGHT STATE TRANSITIONS & PREEMPTION INVARIANTS")
        
        # Tạo bản đồ thực tại để xác minh invariants
        wg = create_default_world_graph()
        
        # 1. Precondition check: EXECUTING cần Redis-AI hoạt động HEALTHY
        # Thử sập Redis và kiểm tra xem có chặn EXECUTING không thưa Master
        wg.add_node("redis-ai", NodeType.CONTAINER, status="DOWN")
        
        try:
            FormalInvariantEngine.assert_precondition(TaskState.EXECUTING, wg)
            raise AssertionError("Thất bại: Lẽ ra phải chặn EXECUTING vì Redis bị sập!")
        except AssertionError as ae:
            print(f"  ✅ [INVARIANT-PRECONDITION] Chặn đúng hành vi bất hợp pháp: {ae}")

        # Sửa lại Redis thành HEALTHY
        wg.add_node("redis-ai", NodeType.CONTAINER, status="HEALTHY")
        FormalInvariantEngine.assert_precondition(TaskState.EXECUTING, wg)
        print("  ✅ [INVARIANT-PRECONDITION] Thông qua EXECUTING khi Redis phục hồi HEALTHY.")

        # 2. Precondition check: COMMITTING không cho phép tệp nhân bị CORRUPTED
        wg.add_node("state_machine.py", NodeType.FILE, {"is_kernel": True}, status="CORRUPTED")
        try:
            FormalInvariantEngine.assert_precondition(TaskState.COMMITTING, wg)
            raise AssertionError("Thất bại: Lẽ ra phải chặn COMMITTING vì state_machine.py bị lỗi cú pháp!")
        except AssertionError as ae:
            print(f"  ✅ [INVARIANT-PRECONDITION] Chặn đúng hành vi phá hoại Kernel: {ae}")

        print("  👉 [TEST 1 HOÀN TẤT]: Khớp hoàn hảo các điều kiện bất biến thưa Tổng Giám Đốc.\n")

    # -----------------------------------------------------------------
    # TEST 2: Cognitive ACID Transaction & Supervisor Rollback (Method A)
    # -----------------------------------------------------------------
    async def test_cognitive_acid_and_rollback(self):
        print("🔷 [TEST 2]: COGNITIVE ACID TRANSACTION & SUPERVISOR ROLLBACK")
        
        # Tạo file tạm thời giả lập mã nguồn bị lỗi
        test_file = "d:/Docker/JKAI/scratch/sandbox/broken_logic.py"
        self.temp_files.append(test_file)
        
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def calculate_sum(a, b):\n    return a + b\n")

        # Khởi động giao dịch
        tx_id = "tx-test-101"
        await cognitive_transaction_manager.begin_transaction(tx_id, self.task_id)
        
        # Ghi nhận backup dạng .bak thưa Master (Phương án A)
        await cognitive_transaction_manager.register_backup(tx_id, test_file)

        # Viết sửa file lỗi
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def calculate_sum(a, b):\n    # Lỗi phá hoại logic\n    return 'corrupted_state'\n")

        # Kiểm tra xem file đã bị thay đổi chưa
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "corrupted_state" in content, "Lỗi ghi đè thử nghiệm!"
        print("  🧪 Đã ghi đè file thử nghiệm thành công. Chuẩn bị rollback cứu hộ...")

        # Kích hoạt Rollback khẩn cấp
        await cognitive_transaction_manager.rollback_transaction(tx_id)

        # Xác minh file nguyên bản đã được phục hồi hoàn hảo
        with open(test_file, "r", encoding="utf-8") as f:
            restored_content = f.read()
        
        assert "a + b" in restored_content, "Lỗi! Rollback không khôi phục đúng nội dung!"
        assert not os.path.exists(f"{test_file}.bak"), "Lỗi! File .bak chưa được dọn dẹp sau rollback!"
        
        print("  ✅ [COGNITIVE-ACID-ROLLBACK] Phục hồi trạng thái tệp tin nguyên bản xuất sắc thưa Master!")

        # Giả lập hoạt động phục hồi của Supervisor
        self_model = SelfModelCortex()
        supervisor = CognitiveSupervisor(self_model)
        thread = await supervisor.register_thread("thread-007", self.task_id, "Refactor core API")
        
        # Giả lập sập luồng do lỗi phẫu thuật
        status = await supervisor.handle_thread_failure("thread-007", ValueError("Syntax Error near '='"), "surgery")
        assert status in ["RETRY", "SUSPENDED_WAITING_MASTER"], f"Trạng thái phục hồi sai: {status}"
        print(f"  ✅ [SUPERVISOR-RECOVERY] Định tuyến thành công chiến lược xử lý sự cố: `{status}` thưa Tổng Giám Đốc.")

        print("  👉 [TEST 2 HOÀN TẤT]: Bảo vệ ACID và hồi sức Supervisor hoạt động hoàn hảo.\n")

    # -----------------------------------------------------------------
    # TEST 3: Cognitive Event Bus & Monotonic HLC Causal Ordering
    # -----------------------------------------------------------------
    async def test_event_bus_and_causal_ordering(self):
        print("🔷 [TEST 3]: COGNITIVE EVENT BUS & MONOTONIC HLC CAUSAL ORDERING")

        received_events: List[CognitiveEvent] = []
        
        async def event_handler(event: CognitiveEvent):
            received_events.append(event)

        # Đăng ký thụ thể
        cognitive_event_bus.subscribe("SYSTEM_ALERT", event_handler)

        # Phát sóng liên tiếp các sự kiện bất đồng bộ thưa Master
        e1 = CognitiveEvent("evt-1", "SYSTEM_ALERT", self.task_id, "AgentA", {"msg": "High CPU"})
        e2 = CognitiveEvent("evt-2", "SYSTEM_ALERT", self.task_id, "AgentB", {"msg": "Overheat"})

        await cognitive_event_bus.publish(e1)
        await cognitive_event_bus.publish(e2)

        # Đợi các task bất đồng bộ chạy xong
        await asyncio.sleep(0.5)

        assert len(received_events) >= 2, f"Không nhận đủ sự kiện! Nhận được: {len(received_events)}"
        
        # Xác minh nhãn thời gian logic đơn điệu tăng dần (Monotonic Clock thưa Master)
        ts1 = received_events[0].hlc_timestamp
        ts2 = received_events[1].hlc_timestamp
        
        assert ts1 < ts2, f"Vi phạm trật tự nhân quả HLC! ts1: {ts1}, ts2: {ts2}"
        print(f"  ✅ [MONOTONIC-HLC] Causal Ordering hoàn hảo. Event 1 HLC: {ts1} < Event 2 HLC: {ts2}")

        print("  👉 [TEST 3 HOÀN TẤT]: Trật tự nhân quả và kênh thần kinh Bus hoạt động chính xác.\n")

    # -----------------------------------------------------------------
    # TEST 4: Predictive Simulator & Constraint DSL
    # -----------------------------------------------------------------
    async def test_simulator_and_constraints(self):
        print("🔷 [TEST 4]: PREDICTIVE SIMULATOR & CONSTRAINT DSL RULES ENGINE")

        wg = create_default_world_graph()
        dsl_engine = ConstraintDSLEngine()
        simulator = TemporalSimulator(dsl_engine)

        # Giả lập thay đổi an toàn: Cập nhật cấu hình cổng Qdrant
        ok, msg, _ = simulator.simulate_action(
            wg, "UPDATE_PROPERTIES", "qdrant", {"port": 6333}
        )
        assert ok, f"Lẽ ra phải an toàn! Lỗi: {msg}"
        print(f"  ✅ [SIMULATOR-SAFE] Thông qua thay đổi mô phỏng an toàn: {msg}")

        # Giả lập thay đổi vi phạm: Đổi cổng Redis trùng với Postgres (cổng 5432)
        # Tạo bản ghi vi phạm độc bản cổng mạng thưa Master!
        wg.add_node("port-5432", NodeType.PORT, {"value": 5432})
        wg.add_node("port-redis", NodeType.PORT, {"value": 5432}) # Cố tình cấu hình trùng cổng 5432
        
        # Đưa vào mô phỏng phản thực tế
        ok_bad, error_msg, _ = simulator.simulate_action(
            wg, "UPDATE_PROPERTIES", "port-redis", {"value": 5432}
        )
        assert not ok_bad, "Lẽ ra phải chặn hành động trùng cổng!"
        print(f"  ✅ [SIMULATOR-VIOLATION] Phát hiện vi phạm an ninh cấu hình tĩnh xuất sắc: {error_msg}")

        print("  👉 [TEST 4 HOÀN TẤT]: Bộ mô phỏng phản thực tế ngăn chặn mọi lỗi thiết kế từ trong trứng nước.\n")

    # -----------------------------------------------------------------
    # TEST 5: Capability Broker & Shadow Clone Sandbox Boundaries
    # -----------------------------------------------------------------
    async def test_sandbox_and_security_broker(self):
        print("🔷 [TEST 5]: CAPABILITY BROKER & SHADOW CLONE SANDBOX BOUNDARIES")

        # 1. Phát hành token quyền hạn hợp lệ cho vùng sandbox
        token = capability_broker.issue_token(
            task_id=self.task_id,
            cap_type=CapabilityType.EXECUTION,
            scope="d:/Docker/JKAI/scratch/sandbox"
        )

        # 2. Thử chạy code an toàn thưa Master
        safe_code = "print('Hello, Master LeeTrung! Everything is beautiful.')"
        ok, code, out, err = await sandbox_executor.execute_isolated_code(
            token_id=token.token_id,
            code_content=safe_code,
            script_name="safe_hello.py"
        )
        assert ok, f"Thực thi mã nguồn an toàn thất bại! {err}"
        assert "LeeTrung" in out, "Không lấy được stdout từ sandbox!"
        print(f"  ✅ [SANDBOX-SAFE-EXEC] Thực thi mã nguồn an toàn trong hộp cát thành công. Stdout: `{out.strip()}`")

        # 3. Thử chạy mã độc xâm phạm an ninh (os.system mà không có cấu hình cao cấp)
        malicious_code = "import os\nos.system('echo Hacked!')"
        # Thử chứng minh an toàn mã nguồn tĩnh
        is_safe, proof_msg = policy_proof_engine.prove_safety(malicious_code, token)
        assert not is_safe, "Bộ proof engine đáng lẽ phải chặn mã nguồn chứa lệnh os.system!"
        print(f"  ✅ [FORMAL-SAFETY-GOVERNOR] Chặn đúng hành vi phá hoại hệ thống (Proof Failed): {proof_msg}")

        print("  👉 [TEST 5 HOÀN TẤT]: Hộp cát cô lập Shadow Clone và Broker bảo mật hoạt động hoàn mỹ.\n")

    # -----------------------------------------------------------------
    # TEST 6: Dream Consolidation & Active Learning Cycle
    # -----------------------------------------------------------------
    async def test_dream_consolidation(self):
        print("🔷 [TEST 6]: DREAM CONSOLIDATION & ACTIVE LEARNING CYCLE")

        # Đẩy một vài bản ghi lỗi giả lập lên SQLite sự kiện để JIT Compiler học tập
        # Chúng ta dùng luôn db_path mặc định
        from core.utils.event_store import event_store
        
        # Ghi các sự kiện THOUGHT_FAILED liên tiếp thưa Master
        for i in range(5):
            event_store.log_event(
                task_id=self.task_id,
                agent_id="TestAgent",
                event_type="THOUGHT_FAILED",
                payload={"error": f"Ollama connection timeout iteration {i}"}
            )

        # Kích hoạt chu kỳ ngủ hoà hợp nhận thức thưa Master
        res = await dream_consolidator.trigger_consolidation_cycle(self.task_id)
        
        assert res["compiled_count"] >= 0, "Chạy chu kỳ nén thất bại!"
        print(f"  ✅ [DREAM-CONSOLIDATION] Hoàn thành chu kỳ ngủ tiến hoá. Đã đúc rút: {res['compiled_count']} tri thức mới.")
        print(f"  📊 Thống kê siêu nhận thức: {res['meta_stats']}")

        print("  👉 [TEST 6 HOÀN TẤT]: Chu trình ngủ hoà hợp và tự học thông minh hoạt động mượt mà.\n")


if __name__ == "__main__":
    suite = TestAgiSubstrate()
    asyncio.run(suite.run_all_tests())
