# [ZENITH FILE DIRECTIVE]
# - File: core/os/execution_planner.py
# - Role: Execution Planner v2 (Layer 4) with IntentCortex integrations
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v2.0 (Integrated)

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from core.os.mission_state import MissionState
from core.os.world_state import WorldState
from core.os.execution_plan import ExecutionPlan, ExecutionPlanStep
from core.config import settings

logger = logging.getLogger("jkai.os.planner")

class ExecutionPlanner:
    @staticmethod
    def calculate_planning_cost(mission: MissionState, world: WorldState) -> float:
        """Tính toán Planning Cost động dựa trên trạng thái thế giới và IntentCortex metadata."""
        cost = 1.0  # Chi phí cơ bản của một yêu cầu hội thoại

        # 1. Tích hợp dữ liệu từ thế giới thực (World State)
        ws = world.workspace
        if ws.is_dirty:
            cost += 1.5  # Phụ phí nếu repo đang có thay đổi chưa commit
        cost += len(ws.modified_files) * 0.3

        # Phụ phí nếu tài nguyên phần cứng bị quá tải
        hw = world.hardware
        cpu_threshold = getattr(settings, "OS_OVERLOAD_CPU", 85)
        if hw.cpu_percent > cpu_threshold or hw.ram_percent > 90:
            cost += 1.0

        # 2. Tích hợp dữ liệu IntentCortex (routing_manifest) nếu có thưa Master
        manifest = mission.routing_manifest
        if manifest and isinstance(manifest, dict):
            # Lấy độ phức tạp từ IntentCortex (scale từ 0.0 đến 1.0 hoặc cao hơn)
            complexity = float(manifest.get("complexity_score") or manifest.get("complexity", 0.0))
            cost += complexity * 4.0  # Chuyển đổi thành Planning Cost (tối đa +4.0)

            # Cộng chi phí lập lịch dựa trên mức độ yêu thích công cụ (tool affinity)
            tool_affinity = manifest.get("tool_affinity", [])
            if isinstance(tool_affinity, list):
                cost += len(tool_affinity) * 0.3
        else:
            # Fallback nếu thiếu manifest: Phân tích keyword cơ bản từ Goal
            goal_lower = mission.goal.lower()
            mutation_keywords = ["sửa", "viết", "tạo", "xóa", "cải tiến", "tối ưu", "edit", "write", "create", "delete", "run", "execute", "modify", "update"]
            if any(kw in goal_lower for kw in mutation_keywords):
                cost += 2.5

        # Nếu Master chủ động yêu cầu chạy chế độ deep
        if mission.is_deep:
            cost += 3.0

        return round(cost, 2)

    @classmethod
    async def generate_plan(cls, mission: MissionState, world: WorldState) -> ExecutionPlan:
        """Sinh sơ đồ kế hoạch ExecutionPlan dựa trên hai luồng trạng thái."""
        cost = cls.calculate_planning_cost(mission, world)
        # Trích xuất độ tin cậy của manifest thưa Master
        manifest = mission.routing_manifest
        conf = 1.0
        if manifest and isinstance(manifest, dict):
            conf = float(manifest.get("confidence") or manifest.get("confidence_score") or 1.0)

        plan = ExecutionPlan(
            estimated_cost=cost,
            confidence_score=conf,
            is_provisional=(conf < 0.7)
        )
        
        # 1. Phán quyết chọn Pipeline
        infra = world.infrastructure_health
        is_qdrant_online = infra.get("qdrant") == "online"
        is_ollama_online = infra.get("ollama") == "online"
        
        route_reasons = []

        # Check if resolved skill requires deep mode and can bypass Ollama offline check
        resolved = None
        if manifest and isinstance(manifest, dict):
            resolved = manifest.get("resolved_skill_ids")
        elif manifest and hasattr(manifest, "resolved_skill_ids"):
            resolved = getattr(manifest, "resolved_skill_ids")
        if not resolved and hasattr(mission, "known_facts") and isinstance(mission.known_facts, dict):
            resolved = mission.known_facts.get("resolved_skill_ids")
        if not resolved and hasattr(mission, "kwargs") and isinstance(mission.kwargs, dict):
            resolved = mission.kwargs.get("resolved_skill_ids")
        
        has_deep_skill = False
        if resolved:
            try:
                from core.utils.deep_routing import _DEEP_SKILLS
                if any(sid in _DEEP_SKILLS for sid in resolved):
                    has_deep_skill = True
            except Exception:
                pass

        if not is_ollama_online and not has_deep_skill:
            plan.selected_pipeline = "fast"
            try:
                from core.utils.engine import engine
                engine._increment_stat("ollama_offline")
            except Exception:
                pass
            plan.reasoning_route = "⚠️ LÕI OLLAMA OFFLINE: Không thể chạy mô hình cục bộ. Định tuyến về Fast Pipeline để sử dụng API ngoài."
            plan.steps.append(ExecutionPlanStep(
                step_id="S0_FALLBACK",
                description="Sử dụng mô hình dự phòng (cloud/external API) để phản hồi yêu cầu do Ollama offline.",
                assigned_agent="general"
            ))
            return plan

        # Ngưỡng chuyển đổi động (Dynamic Threshold) thưa Master
        # Ngưỡng tiêu chuẩn được cấu hình tập trung trong settings
        base_threshold = getattr(settings, "OS_COST_THRESHOLD", 3.0)
        dynamic_threshold = base_threshold
        manifest = mission.routing_manifest

        # 🧠 [FAST-MISSION-BYPASS]: Nếu orchestrator đã quyết định is_fast=True (ví dụ: skill thông thường),
        # tôn trọng quyết định đó ngay lập tức — không tính cost thêm
        if getattr(mission, "is_fast", False) and not has_deep_skill:
            plan.selected_pipeline = "fast"
            desc = "Phản xạ nhanh với RAG." if is_qdrant_online else "Phản xạ nhanh (Qdrant offline)."
            plan.steps.append(ExecutionPlanStep(
                step_id="S1_FAST_REACTIVE",
                description=desc,
                assigned_agent="general",
                required_tools=["SEARCH_WEB_GLOBAL"]
            ))
            plan.reasoning_route = "is_fast=True từ Orchestrator → Fast Pipeline tức thì."
            return plan

        # 🧠 [FAST-SKILL-BYPASS]: Nếu có kích hoạt skill thông thường và không tác động workspace, ép chạy Fast Pipeline
        # Bỏ qua bypass nếu goal đã được SSM làm giàu (skill cần thực thi thực tế, không chỉ tra cứu)
        has_workspace_target = bool(getattr(mission, "workspace_target", None))
        ssm_activated = "<ZENITH_SKILL_ACTIVATED>" in getattr(mission, "goal", "")
        if resolved and not has_deep_skill and not has_workspace_target and not ssm_activated:
            cost = 1.0  # Reset cost về mức thấp để chạy Fast
            route_reasons.append("Chỉ kích hoạt skill thông thường (Fast-routing)")

        if manifest and isinstance(manifest, dict):
            # Nếu IntentCortex đánh dấu là FIX hoặc BUILD -> Hạ thấp ngưỡng để ưu tiên Deep Pipeline chạy an toàn
            intent = str(manifest.get("intent", "")).upper()
            if intent in ["FIX", "BUILD"]:
                dynamic_threshold = base_threshold - 1.0

        if cost >= dynamic_threshold:
            plan.selected_pipeline = "deep"
            route_reasons.append(f"Planning Cost cao ({cost} >= {dynamic_threshold})")
            
            # Trích xuất danh sách tool thích hợp từ manifest
            allocated_tools = ["list_dir", "grep_search"]
            if manifest and isinstance(manifest, dict):
                affinity = manifest.get("tool_affinity", [])
                if isinstance(affinity, list):
                    allocated_tools = list(set(allocated_tools + [str(t) for t in affinity]))

            # Xây dựng các bước thực thi sâu
            plan.steps.append(ExecutionPlanStep(
                step_id="S1_RECON",
                description="Quét thư mục làm việc, định vị tệp tin và thu thập tri thức.",
                assigned_agent="workspace",
                required_tools=allocated_tools if is_qdrant_online else []
            ))
            plan.steps.append(ExecutionPlanStep(
                step_id="S2_FORGE",
                description="Lập kế hoạch sửa đổi và tiến hành ghi code.",
                assigned_agent="workspace",
                required_tools=["replace_file_content", "write_to_file"]
            ))
            plan.steps.append(ExecutionPlanStep(
                step_id="S3_VERIFY",
                description="Chạy kiểm tra thử (Reflex test/lint/compile) để xác minh tính ổn định.",
                assigned_agent="workspace",
                required_tools=["run_command"]
            ))
            plan.steps.append(ExecutionPlanStep(
                step_id="S4_AUDIT",
                description="Gửi phản hồi qua Hội đồng nơ-ron (Critic) để thẩm định chất lượng đầu ra.",
                assigned_agent="critic"
            ))
        else:
            plan.selected_pipeline = "fast"
            route_reasons.append(f"Planning Cost thấp ({cost} < {dynamic_threshold})")
            
            # Các bước nhanh
            desc = "Phản xạ nhanh với RAG để trả lời câu hỏi của Master." if is_qdrant_online else "Phản xạ nhanh (Không dùng RAG vì Qdrant DB offline)."
            plan.steps.append(ExecutionPlanStep(
                step_id="S1_FAST_REACTIVE",
                description=desc,
                assigned_agent="general",
                required_tools=["SEARCH_WEB_GLOBAL"]
            ))

        plan.reasoning_route = " -> ".join(route_reasons)
        return plan
