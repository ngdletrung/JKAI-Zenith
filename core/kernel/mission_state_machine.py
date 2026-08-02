from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.kernel.models import (
    MissionNodeState,
    EventType,
    MissionContext,
    MissionPlan,
    MissionEvent,
    MissionNode
)

# 🛤️ Định nghĩa quy tắc chuyển đổi trạng thái hợp lệ của từng Node
ALLOWED_NODE_TRANSITIONS = {
    MissionNodeState.PENDING: {MissionNodeState.RUNNING, MissionNodeState.CANCELLED, MissionNodeState.FAILED},
    MissionNodeState.RUNNING: {MissionNodeState.SUCCESS, MissionNodeState.FAILED, MissionNodeState.PAUSED, MissionNodeState.TIMEOUT, MissionNodeState.WAITING_USER, MissionNodeState.WAITING_TOOL, MissionNodeState.PENDING},
    MissionNodeState.PAUSED: {MissionNodeState.RUNNING, MissionNodeState.CANCELLED},
    MissionNodeState.WAITING_USER: {MissionNodeState.RUNNING, MissionNodeState.CANCELLED, MissionNodeState.FAILED},
    MissionNodeState.WAITING_TOOL: {MissionNodeState.RUNNING, MissionNodeState.CANCELLED, MissionNodeState.FAILED},
    MissionNodeState.SUCCESS: {MissionNodeState.PENDING, MissionNodeState.CANCELLED, MissionNodeState.FAILED},  # Cho phép chuyển sang FAILED nếu validation node báo thất bại
    MissionNodeState.FAILED: {MissionNodeState.PENDING, MissionNodeState.CANCELLED},  # Hỗ trợ RETRY (chuyển về PENDING)
    MissionNodeState.CANCELLED: set(), # Terminal
    MissionNodeState.TIMEOUT: {MissionNodeState.PENDING, MissionNodeState.CANCELLED}
}

class InvalidNodeStateTransition(Exception):
    """Lỗi khi cố gắng chuyển đổi trạng thái của node sai quy định"""
    pass

class MissionState(BaseModel):
    """
    📈 MissionState: Trạng thái hiện tại của một nhiệm vụ, được tái tạo (reduced) từ Event Log
    """
    mission_id: str
    status: str = Field(default="CREATED", description="Trạng thái tổng thể của Mission (CREATED, PLANNING, EXECUTING, PAUSED, CANCELLED, COMPLETED, FAILED)")
    context: Optional[MissionContext] = Field(None, description="Ngữ cảnh chung của Mission")
    plan: Optional[MissionPlan] = Field(None, description="Đồ thị kế hoạch (DAG) hiện tại")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung")


def validate_node_transition(node_name: str, current: MissionNodeState, target: MissionNodeState):
    """Kiểm tra và thực thi tính hợp lệ của việc chuyển đổi trạng thái Node"""
    if current == target:
        return
    allowed = ALLOWED_NODE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidNodeStateTransition(
            f"Lỗi chuyển trạng thái Node '{node_name}': Không thể chuyển từ '{current.value}' sang '{target.value}'"
        )


def reduce_state(mission_id: str, events: List[MissionEvent], base_state: Optional[MissionState] = None) -> MissionState:
    """
    🌀 Reducer function: Replay chuỗi Event để tái tạo lại MissionState hiện tại.
    Hỗ trợ nhận base_state để tối ưu hóa việc khôi phục từ snapshot.
    """
    state = base_state.model_copy(deep=True) if base_state else MissionState(mission_id=mission_id)

    for event in events:
        payload = event.payload
        e_type = event.event_type

        # 1. Khởi tạo Mission
        if e_type == EventType.MISSION_CREATED:
            state.status = "CREATED"
            if "context" in payload:
                state.context = MissionContext(**payload["context"])
            state.metadata = payload.get("metadata", {})

        # 2. Bắt đầu/kết thúc Planning
        elif e_type == EventType.NODE_SCHEDULED:
            state.status = "EXECUTING"
        elif e_type == EventType.PLANNER_FINISHED:
            state.status = "PLANNING_COMPLETED"
            if "plan" in payload:
                state.plan = MissionPlan(**payload["plan"])

        # 3. Trạng thái của từng Node trong DAG
        elif e_type == EventType.NODE_STARTED:
            node_id = payload.get("node_id")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.RUNNING)
                node.state = MissionNodeState.RUNNING

        elif e_type == EventType.NODE_COMPLETED:
            node_id = payload.get("node_id")
            output_data = payload.get("output")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.SUCCESS)
                node.state = MissionNodeState.SUCCESS
                node.output = output_data

        elif e_type == EventType.NODE_FAILED:
            node_id = payload.get("node_id")
            error_msg = payload.get("error")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.FAILED)
                node.state = MissionNodeState.FAILED
                node.error = error_msg

        elif e_type == EventType.NODE_PAUSED:
            node_id = payload.get("node_id")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.PAUSED)
                node.state = MissionNodeState.PAUSED

        elif e_type == EventType.NODE_RESUMED:
            node_id = payload.get("node_id")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.RUNNING)
                node.state = MissionNodeState.RUNNING

        # 4. Trạng thái tổng thể của Mission
        elif e_type == EventType.MISSION_PAUSED:
            state.status = "PAUSED"
        elif e_type == EventType.MISSION_RESUMED:
            state.status = "EXECUTING"
        elif e_type == EventType.MISSION_CANCELLED:
            state.status = "CANCELLED"
            # Hủy tất cả các node chưa chạy/đang chạy
            if state.plan:
                for node in state.plan.nodes.values():
                    if node.state in [MissionNodeState.PENDING, MissionNodeState.RUNNING, MissionNodeState.PAUSED]:
                        node.state = MissionNodeState.CANCELLED

        elif e_type == EventType.MISSION_COMPLETED:
            state.status = "COMPLETED"

        elif e_type == EventType.VALIDATION_FAILED:
            node_id = payload.get("node_id")
            reason = payload.get("reason")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.FAILED)
                node.state = MissionNodeState.FAILED
                node.error = f"Validation Failed: {reason}"

        elif e_type == EventType.RETRY_REQUESTED:
            node_id = payload.get("node_id")
            if state.plan and node_id in state.plan.nodes:
                node = state.plan.nodes[node_id]
                validate_node_transition(node.name, node.state, MissionNodeState.PENDING)
                node.state = MissionNodeState.PENDING
                node.retries_count += 1
                node.error = None
                node.output = None

    return state
