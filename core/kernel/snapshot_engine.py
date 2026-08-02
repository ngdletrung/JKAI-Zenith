import json
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
from core.kernel.models import MissionEvent
from core.kernel.mission_state_machine import MissionState, reduce_state
from core.kernel.event_store import EventStore

class SnapshotEngine:
    """
    📸 SnapshotEngine: Quản lý ghi/đọc Snapshot của MissionState để tối ưu hóa hiệu năng.
    Thay vì replay hàng nghìn sự kiện cũ, hệ thống load snapshot gần nhất và chỉ replay các event mới.
    """
    def __init__(self, base_dir: str = "data/missions", event_store: Optional[EventStore] = None):
        self.base_dir = Path(base_dir)
        self.event_store = event_store or EventStore(base_dir)

    def _get_snapshot_path(self, mission_id: str) -> Path:
        return self.base_dir / mission_id / "snapshot.json"

    def save_snapshot(self, state: MissionState, last_event_id: str, last_event_timestamp: datetime) -> None:
        """Lưu trạng thái MissionState hiện tại thành Snapshot trên đĩa sử dụng cơ chế Atomic Write"""
        import os
        snapshot_path = self._get_snapshot_path(state.mission_id)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        snapshot_data = {
            "state": state.model_dump(),
            "last_event_id": last_event_id,
            "last_event_timestamp": last_event_timestamp.isoformat()
        }
        
        # Ghi vào file tạm trước để tránh hỏng file chính thức nếu crash giữa chừng
        temp_path = snapshot_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
            
        # Thay thế nguyên tử (Atomic replace)
        os.replace(temp_path, snapshot_path)

    def load_snapshot(self, mission_id: str) -> Tuple[Optional[MissionState], Optional[str], Optional[datetime]]:
        """Tải snapshot gần nhất của Mission (nếu có)"""
        snapshot_path = self._get_snapshot_path(mission_id)
        if not snapshot_path.exists():
            return None, None, None

        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        state = MissionState(**data["state"])
        last_event_id = data["last_event_id"]
        last_event_timestamp = datetime.fromisoformat(data["last_event_timestamp"])
        
        return state, last_event_id, last_event_timestamp

    def get_latest_state(self, mission_id: str) -> MissionState:
        """
        🚀 Lấy trạng thái mới nhất của Mission:
        1. Đọc Snapshot gần nhất (nếu có).
        2. Lấy tất cả sự kiện từ EventStore.
        3. Nếu có snapshot, chỉ replay các sự kiện xảy ra SAU thời điểm snapshot.
        4. Trả về MissionState hoàn chỉnh.
        """
        from core.kernel.mission_state_machine import reduce_state
        
        snapshot_state, last_event_id, _ = self.load_snapshot(mission_id)
        all_events = self.event_store.get_events(mission_id)
        
        if not all_events:
            return MissionState(mission_id=mission_id)

        if snapshot_state is None:
            # Replay toàn bộ từ đầu
            return reduce_state(mission_id, all_events)
        
        # Tìm vị trí của event cuối cùng đã được snapshot
        last_idx = next((i for i, e in enumerate(all_events) if e.event_id == last_event_id), -1)
        
        # Nếu tìm thấy, lấy toàn bộ event sau đó. Nếu không thấy (hỏng file snapshot cũ), replay từ đầu.
        if last_idx != -1:
            new_events = all_events[last_idx + 1:]
            return reduce_state(mission_id, new_events, base_state=snapshot_state)
        
        return reduce_state(mission_id, all_events)
