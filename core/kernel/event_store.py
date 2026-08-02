import os
import json
from typing import List
from pathlib import Path
from datetime import datetime
from core.kernel.models import MissionEvent

_REDIS_STREAM_MAXLEN = 5000

class EventStore:
    """
    🗄️ EventStore: Quản lý ghi/đọc Event Log — Redis Streams làm primary, JSONL file làm fallback.
    Mỗi Mission có một Redis Stream riêng (stream:mission:events:{mission_id}) và file log dự phòng.
    """
    def __init__(self, base_dir: str = "data/missions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            try:
                from core.utils.engine import engine
                self._redis = engine._get_redis()
            except Exception:
                pass
        return self._redis

    def _get_mission_dir(self, mission_id: str) -> Path:
        mission_dir = self.base_dir / mission_id
        mission_dir.mkdir(parents=True, exist_ok=True)
        return mission_dir

    def _get_event_log_path(self, mission_id: str) -> Path:
        return self._get_mission_dir(mission_id) / "events.jsonl"

    def append_event(self, event: MissionEvent) -> None:
        """Ghi sự kiện vào Redis Stream (primary), ghi file JSONL (fallback)."""
        event_dict = event.model_dump()
        event_dict["timestamp"] = event.timestamp.isoformat()
        payload = json.dumps(event_dict, ensure_ascii=False)

        # Primary: Redis Streams
        r = self._get_redis()
        if r:
            try:
                r.xadd(f"stream:mission:events:{event.mission_id}", {"payload": payload}, maxlen=_REDIS_STREAM_MAXLEN)
                return
            except Exception:
                pass

        # Fallback: file JSONL (single-process only)
        log_path = self._get_event_log_path(event.mission_id)
        with open(log_path, mode="a", encoding="utf-8") as f:
            f.write(payload + "\n")

    def get_events(self, mission_id: str) -> List[MissionEvent]:
        """Đọc lại chuỗi sự kiện từ Redis Streams (primary) hoặc file log (fallback)."""
        r = self._get_redis()
        if r:
            try:
                raw = r.xrevrange(f"stream:mission:events:{mission_id}", count=_REDIS_STREAM_MAXLEN)
                if raw:
                    events = []
                    for entry_id, fields in raw:
                        payload = fields.get(b"payload", fields.get("payload", ""))
                        if isinstance(payload, bytes):
                            payload = payload.decode()
                        if payload:
                            data = json.loads(payload)
                            if "timestamp" in data:
                                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                            events.append(MissionEvent(**data))
                    events.reverse()
                    return events
            except Exception:
                pass

        # Fallback: đọc từ file
        log_path = self._get_event_log_path(mission_id)
        if not log_path.exists():
            return []
        events = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line.strip())
                if "timestamp" in data:
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                events.append(MissionEvent(**data))
        return events
