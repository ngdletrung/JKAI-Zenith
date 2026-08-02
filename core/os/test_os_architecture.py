# [ZENITH FILE DIRECTIVE]
# - File: core/os/test_os_architecture.py
# - Role: Test Suite for Layer 3, 4, 5 (State, Planning & Execution) using unittest
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0 (Integrated)

import unittest
import time
import asyncio
from core.os.mission_state import MissionState
from core.os.world_state import WorldState, HardwareTelemetry, WorkspaceState
from core.os.execution_plan import ExecutionPlan, ExecutionPlanStep
from core.os.execution_planner import ExecutionPlanner
from core.os.memory_state import MemoryState

class TestOSArchitecture(unittest.TestCase):
    # ── 1. TEST SERILIZATION & STATE STRUCTURE (LAYER 3) ──
    def test_mission_state_serialization(self):
        # Khởi tạo các trạng thái mẫu
        hw = HardwareTelemetry(cpu_percent=50, ram_percent=60, gpu_percent=10, timestamp=time.time())
        ws = WorkspaceState(path="/workspace", active_branch="dev", is_dirty=True, modified_files=["main.py"])
        world = WorldState(hardware=hw, workspace=ws, available_tools=["tool_A"], infrastructure_health={"redis": "online"})
        
        exec_plan = ExecutionPlan(
            selected_pipeline="deep",
            estimated_cost=4.5,
            confidence_score=0.8,
            is_provisional=False,
            steps=[ExecutionPlanStep(step_id="S1_RECON", description="Recon step", assigned_agent="workspace")]
        )
        
        mem = MemoryState(reflex_cache_hit=True, conversation_summary="Cached greeting", learned_patterns=[])
        
        mission = MissionState(
            goal="optimize router",
            original_goal="optimize router",
            task_id="task_123",
            os_intent="code",
            world_state=world,
            execution_plan=exec_plan,
            memory_state=mem
        )
        
        # Thực hiện serialize sang dict
        dump_data = mission.to_dict()
        
        # Xác minh các trường bảo toàn dữ liệu hoàn hảo thưa Master
        self.assertEqual(dump_data["goal"], "optimize router")
        self.assertEqual(dump_data["world_state"]["hardware"]["cpu_percent"], 50)
        self.assertEqual(dump_data["world_state"]["workspace"]["active_branch"], "dev")
        self.assertEqual(dump_data["world_state"]["workspace"]["is_dirty"], True)
        self.assertEqual(dump_data["execution_plan"]["selected_pipeline"], "deep")
        self.assertEqual(dump_data["execution_plan"]["estimated_cost"], 4.5)
        self.assertEqual(dump_data["execution_plan"]["is_provisional"], False)
        self.assertEqual(dump_data["memory_state"]["reflex_cache_hit"], True)
        self.assertEqual(dump_data["memory_state"]["conversation_summary"], "Cached greeting")

    # ── 2. TEST EXECUTION PLANNER COST CALCULATION (LAYER 4) ──
    def test_execution_planner_cost_logic(self):
        # Kịch bản A: Workspace sạch, query đơn giản
        mission_a = MissionState(goal="xin chào", is_deep=False)
        world_a = WorldState(
            hardware=HardwareTelemetry(cpu_percent=10, ram_percent=40),
            workspace=WorkspaceState(is_dirty=False, modified_files=[])
        )
        cost_a = ExecutionPlanner.calculate_planning_cost(mission_a, world_a)
        self.assertEqual(cost_a, 1.0)  # Chi phí cơ bản của chat thường

        # Kịch bản B: Workspace đang dirty, có file bị sửa đổi dở dang
        mission_b = MissionState(goal="cập nhật cấu hình", is_deep=False)
        world_b = WorldState(
            hardware=HardwareTelemetry(cpu_percent=15, ram_percent=45),
            workspace=WorkspaceState(is_dirty=True, modified_files=["config.json", "utils.py"])
        )
        cost_b = ExecutionPlanner.calculate_planning_cost(mission_b, world_b)
        # Cơ bản 1.0 + dirty 1.5 + 2 file * 0.3 = 3.1
        self.assertEqual(cost_b, 3.1)

        # Kịch bản C: Query sửa đổi mã nguồn nhạy cảm
        mission_c = MissionState(goal="tối ưu hóa thuật toán", is_deep=False)
        world_c = WorldState(
            hardware=HardwareTelemetry(cpu_percent=20, ram_percent=40),
            workspace=WorkspaceState(is_dirty=False, modified_files=[])
        )
        cost_c = ExecutionPlanner.calculate_planning_cost(mission_c, world_c)
        # Cơ bản 1.0 + keyword "tối ưu" 2.5 = 3.5
        self.assertEqual(cost_c, 3.5)

    # ── 3. TEST PIPELINE DEVIATION & PROVISIONAL PLAN ROUTING (LAYER 4) ──
    def test_execution_planner_routing_provisional(self):
        # Kịch bản D: IntentCortex độ tự tin cực thấp (0.4) -> is_provisional = True
        mission_d = MissionState(goal="sửa router")
        mission_d.routing_manifest = {"intent": "FIX", "confidence_score": 0.4, "complexity_score": 0.5}
        world_d = WorldState(
            hardware=HardwareTelemetry(cpu_percent=10, ram_percent=40),
            workspace=WorkspaceState(is_dirty=False, modified_files=[]),
            infrastructure_health={"redis": "online", "qdrant": "online", "ollama": "online"}
        )
        
        loop = asyncio.get_event_loop()
        plan_d = loop.run_until_complete(ExecutionPlanner.generate_plan(mission_d, world_d))
        
        # Vì intent là FIX -> dynamic_threshold hạ xuống 2.0
        # Cost = 1.0 (cơ bản) + 2.5 (FIX keyword) = 3.5
        # 3.5 >= 2.0 -> deep pipeline + is_provisional vì confidence 0.4 < 0.7
        self.assertEqual(plan_d.selected_pipeline, "deep")
        self.assertEqual(plan_d.is_provisional, True)
        self.assertEqual(plan_d.confidence_score, 0.4)

if __name__ == "__main__":
    unittest.main()
