import uuid
import logging
from typing import Callable, Coroutine, Any, Dict, Optional
from core.kernel.models import (
    MissionContext,
    MissionPlan,
    MissionNodeState,
    MissionEvent,
    EventType
)
from core.kernel.event_store import EventStore
from core.kernel.snapshot_engine import SnapshotEngine
from core.kernel.dag_scheduler import DAGScheduler
from core.kernel.capability_broker import CapabilityBroker

logger = logging.getLogger("MissionRuntime")

class MissionRuntime:
    """
    🎮 MissionRuntime: Lớp điều phối trung tâm quản lý toàn bộ vòng đời của Mission.
    Kết nối: EventStore + SnapshotEngine + CapabilityBroker + DAGScheduler.
    """
    def __init__(self, base_dir: str = "data/missions", broker: Optional[CapabilityBroker] = None):
        self.event_store = EventStore(base_dir=base_dir)
        self.broker = broker or CapabilityBroker()
        self.snapshot_engine = SnapshotEngine(base_dir=base_dir, event_store=self.event_store)
        self.scheduler = DAGScheduler(event_store=self.event_store, capability_broker=self.broker)

    def submit_mission(self, context: MissionContext) -> str:
        """
        📥 Gửi một Mission mới và lưu sự kiện khởi tạo
        """
        mission_id = f"mission-{uuid.uuid4().hex[:12]}"
        
        event = MissionEvent(
            mission_id=mission_id,
            event_type=EventType.MISSION_CREATED,
            payload={"context": context.model_dump()}
        )
        self.event_store.append_event(event)
        logger.info(f"📥 Đã tạo Mission mới: `{mission_id}` thưa Master.")
        return mission_id

    async def execute_mission(
        self, 
        mission_id: str, 
        plan: MissionPlan,
        executor_func: Callable[[Any, Dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> bool:
        """
        🚀 Chạy Mission từ đầu
        """
        # Nạp plan của Planner
        self.event_store.append_event(MissionEvent(
            mission_id=mission_id,
            event_type=EventType.PLANNER_FINISHED,
            payload={"plan": plan.model_dump()}
        ))

        # Khôi phục trạng thái hiện tại (trong bộ nhớ)
        state = self.snapshot_engine.get_latest_state(mission_id)
        
        # Thiết lập callback để tự động lưu Snapshot mỗi khi có node hoàn thành
        async def wrapped_executor(node, input_ctx):
            output = await executor_func(node, input_ctx)
            # Chụp nhanh snapshot để lưu checkpoint an toàn xuống đĩa
            latest_state = self.snapshot_engine.get_latest_state(mission_id)
            # Lấy event cuối cùng vừa được ghi vào log
            all_events = self.event_store.get_events(mission_id)
            if all_events:
                last_event = all_events[-1]
                self.snapshot_engine.save_snapshot(latest_state, last_event.event_id, last_event.timestamp)
            return output

        success = await self.scheduler.execute_plan(mission_id, state.plan, state.context, wrapped_executor)
        
        # Snapshot lần cuối cùng khi hoàn tất
        final_state = self.snapshot_engine.get_latest_state(mission_id)
        all_events = self.event_store.get_events(mission_id)
        if all_events:
            last_event = all_events[-1]
            self.snapshot_engine.save_snapshot(final_state, last_event.event_id, last_event.timestamp)
            
        return success

    async def resume_mission(
        self, 
        mission_id: str, 
        executor_func: Callable[[Any, Dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> bool:
        """
        🔄 Khôi phục và chạy tiếp một Mission bị tạm dừng hoặc crash trước đó
        """
        # 1. Khôi phục trạng thái mới nhất bằng cách đọc Snapshot + Replay Event Log
        state = self.snapshot_engine.get_latest_state(mission_id)
        if not state or not state.plan:
            raise ValueError(f"Không tìm thấy dữ liệu Kế hoạch (Plan) để resume cho Mission `{mission_id}`")

        logger.info(f"🔄 Khôi phục Mission `{mission_id}`. Trạng thái hiện tại: `{state.status}` thưa Master.")

        # Phát hành sự kiện Resume
        self.event_store.append_event(MissionEvent(
            mission_id=mission_id,
            event_type=EventType.MISSION_RESUMED
        ))

        # Đặt lại trạng thái của các node bị FAILED (nếu có) về PENDING để chạy lại khi resume
        for node in state.plan.nodes.values():
            if node.state in [MissionNodeState.FAILED, MissionNodeState.RUNNING]:
                # Ghi nhận event RETRY_REQUESTED để đồng bộ với State Machine trên đĩa
                self.event_store.append_event(MissionEvent(
                    mission_id=mission_id,
                    event_type=EventType.RETRY_REQUESTED,
                    payload={"node_id": node.id}
                ))
                # Cả những node đang chạy dở lúc crash cũng chuyển về PENDING để Scheduler lập lịch chạy lại
                node.state = MissionNodeState.PENDING
                node.error = None
                node.output = None

        # 2. Khởi chạy lại Scheduler với Plan đã được khôi phục
        async def wrapped_executor(node, input_ctx):
            output = await executor_func(node, input_ctx)
            latest_state = self.snapshot_engine.get_latest_state(mission_id)
            all_events = self.event_store.get_events(mission_id)
            if all_events:
                last_event = all_events[-1]
                self.snapshot_engine.save_snapshot(latest_state, last_event.event_id, last_event.timestamp)
            return output

        success = await self.scheduler.execute_plan(mission_id, state.plan, state.context, wrapped_executor)
        
        # Snapshot lần cuối cùng khi hoàn tất
        final_state = self.snapshot_engine.get_latest_state(mission_id)
        all_events = self.event_store.get_events(mission_id)
        if all_events:
            last_event = all_events[-1]
            self.snapshot_engine.save_snapshot(final_state, last_event.event_id, last_event.timestamp)

        return success
