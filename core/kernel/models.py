from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class MissionNodeState(str, Enum):
    """
    📌 Trạng thái chi tiết của từng Node trong đồ thị thực thi (DAG)
    """
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    WAITING_USER = "WAITING_USER"
    WAITING_TOOL = "WAITING_TOOL"

class EventType(str, Enum):
    """
    🌀 Các loại sự kiện trong hệ thống Event Sourcing của Mission
    """
    MISSION_CREATED = "MISSION_CREATED"
    PLANNER_FINISHED = "PLANNER_FINISHED"
    NODE_SCHEDULED = "NODE_SCHEDULED"
    NODE_STARTED = "NODE_STARTED"
    NODE_COMPLETED = "NODE_COMPLETED"
    NODE_FAILED = "NODE_FAILED"
    NODE_PAUSED = "NODE_PAUSED"
    NODE_RESUMED = "NODE_RESUMED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RETRY_REQUESTED = "RETRY_REQUESTED"
    MISSION_PAUSED = "MISSION_PAUSED"
    MISSION_RESUMED = "MISSION_RESUMED"
    MISSION_CANCELLED = "MISSION_CANCELLED"
    MISSION_COMPLETED = "MISSION_COMPLETED"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"

class MissionContext(BaseModel):
    """
    🌐 Mission Context: Ngữ cảnh chung toàn bộ Mission, các node đều có thể đọc
    """
    goal: str = Field(..., description="Mục tiêu chính của nhiệm vụ")
    constraints: List[str] = Field(default_factory=list, description="Các ràng buộc khi thực hiện")
    budget_tokens: Optional[int] = Field(None, description="Ngân sách token tối đa")
    budget_usd: Optional[float] = Field(None, description="Ngân sách USD tối đa")
    deadline: Optional[datetime] = Field(None, description="Hạn chót thực hiện")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Tùy chọn cấu hình của người dùng")
    world_state: Dict[str, Any] = Field(default_factory=dict, description="Trạng thái thế giới hiện tại (hệ thống, file,...)")
    policies: List[str] = Field(default_factory=list, description="Các chính sách an toàn/bảo mật áp dụng")

class MissionNode(BaseModel):
    """
    🎯 MissionNode: Đại diện cho một nút tác vụ trong đồ thị (DAG)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID duy nhất của Node")
    name: str = Field(..., description="Tên tác vụ gợi nhớ")
    capability: str = Field(..., description="Năng lực yêu cầu (Capability), ví dụ: 'web_search', 'write_file'")
    input_context_keys: List[str] = Field(
        default_factory=list, 
        description="Context Policy: Danh sách các key dữ liệu node này cần lấy từ node cha"
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="Tham số tĩnh cấu hình cho tác vụ")
    state: MissionNodeState = Field(default=MissionNodeState.PENDING, description="Trạng thái hiện tại của nút")
    output: Optional[Any] = Field(None, description="Kết quả đầu ra của tác vụ")
    error: Optional[str] = Field(None, description="Chi tiết lỗi nếu nút bị FAILED")
    retries_count: int = Field(default=0, description="Số lần đã thử lại")
    max_retries: int = Field(default=3, description="Số lần thử lại tối đa cho nút này")

class MissionEdge(BaseModel):
    """
    🔗 MissionEdge: Định nghĩa quan hệ phụ thuộc giữa các node (source -> target)
    """
    source: str = Field(..., description="ID của Node cha (phải hoàn thành trước)")
    target: str = Field(..., description="ID của Node con (chạy sau)")

class MissionPlan(BaseModel):
    """
    🗺️ MissionPlan: Cấu trúc của toàn bộ kế hoạch (DAG) do Planner sinh ra
    """
    nodes: Dict[str, MissionNode] = Field(..., description="Bản đồ các Node ID -> Node object")
    edges: List[MissionEdge] = Field(..., description="Danh sách các cạnh liên kết dependencies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Siêu dữ liệu bổ sung")

class MissionEvent(BaseModel):
    """
    📦 MissionEvent: Mô hình hóa một Event để ghi vào Event Log (Event Sourcing)
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID duy nhất của Event")
    mission_id: str = Field(..., description="ID của Mission tương ứng")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Thời điểm xảy ra sự kiện (UTC)")
    event_type: EventType = Field(..., description="Loại sự kiện")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dữ liệu payload đi kèm sự kiện")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung")
