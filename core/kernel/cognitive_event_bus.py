"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL COGNITIVE EVENT BUS                      ║
║   Hệ Thần Kinh Trung Ương & Điều Phối Sự Kiện Không Đồng Bộ      ║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị Hệ Thần Kinh & Vận Hành của Tập đoàn JKAI. 🌌🏢⚡*
"""

import json
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable, Awaitable, Optional

from core.utils.hlc import hlc, HlcTimestamp
from core.utils.event_store import event_store
from core.redis_client import redis_safe
from core.utils.engine import engine

logger = logging.getLogger("CognitiveEventBus")

@dataclass(frozen=True)
class CognitiveEvent:
    event_id: str
    event_type: str
    task_id: str
    agent_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    hlc_timestamp: str = field(default_factory=lambda: str(hlc.now()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "hlc_timestamp": self.hlc_timestamp,
            "payload": self.payload,
            "created_at": self.created_at
        }

@dataclass(frozen=True)
class ObservationEvent(CognitiveEvent):
    """
    🔬 [OBSERVATION-EVENT]: Phản hồi từ thực địa sau khi thực thi công cụ.
    Bao gồm metadata về hiệu năng và trạng thái hệ thống.
    """
    def __init__(self, task_id: str, agent_id: str, tool_name: str, output: Any, 
                 exit_code: int = 0, duration: float = 0.0, metadata: Dict = None):
        payload = {
            "tool": tool_name,
            "output": output,
            "exit_code": exit_code,
            "duration_ms": round(duration * 1000, 2),
            "metadata": metadata or {}
        }
        object.__setattr__(self, 'event_id', f"obs_{int(time.time()*1000)}")
        object.__setattr__(self, 'event_type', "OBSERVATION")
        object.__setattr__(self, 'task_id', task_id)
        object.__setattr__(self, 'agent_id', agent_id)
        object.__setattr__(self, 'payload', payload)
        object.__setattr__(self, 'hlc_timestamp', str(hlc.now()))
        object.__setattr__(self, 'created_at', time.time())


class CognitiveEventBus:
    """
    ⚡ [COGNITIVE-EVENT-BUS]: Hệ thần kinh Bus không đồng bộ hạt nhân thưa Master.
    Bóc tách hoàn toàn sự phụ thuộc trực tiếp giữa các module trong hệ thống.
    Đảm bảo tính Replayability thông qua lưu trữ chuỗi sự kiện tuần tự (Event Sourcing).
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[CognitiveEvent], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()
        logger.info("[EVENT-BUS-INIT]: Khởi tạo thành công hệ thống đường truyền thần kinh lõi Zenith v6.0.")

    def subscribe(self, event_type: str, callback: Callable[[CognitiveEvent], Awaitable[None]]):
        """
        📥 [ĐĂNG KÝ THỤ THỂ]: Lắng nghe một tín hiệu thần kinh nhận thức cụ thể thưa Master.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug("[SUBSCRIBE]: Đã gắn thụ thể callback '%s' cho tín hiệu '%s'.", callback.__name__, event_type)

    async def publish(self, event: CognitiveEvent):
        """
        ⚡ [PHÁT SÓNG NƠ-RON]: Lan truyền tín hiệu nhận thức bất đồng bộ ra toàn hệ thống thưa Tổng Giám Đốc.
        Lưu trữ sự kiện tự động vào SQLite (Event Sourcing) và phát sóng qua Redis Hot Path.
        """
        event_data = event.to_dict()
        event_str = json.dumps(event_data, ensure_ascii=False)

        # 🏢 LOG VĂN PHÒNG CHUẨN DOANH NGHIỆP
        engine.publish_mission_log(
            "EVENT_BUS",
            f"[NƠ-RON PHÁT SÓNG] Tín hiệu: {event.event_type} | HLC: {event.hlc_timestamp} | Actor: {event.agent_id}",
            event.task_id,
            "sys"
        )

        # 1. Ghi nhận sự kiện vào SQLite (Event Sourcing - Cold Path)
        try:
            # Sử dụng event_store có sẵn để bảo đảm tính tương thích dữ liệu SQLite
            event_store.log_event(
                task_id=event.task_id,
                agent_id=event.agent_id,
                event_type=event.event_type,
                payload={
                    "event_id": event.event_id,
                    "hlc_timestamp": event.hlc_timestamp,
                    "payload": event.payload,
                    "created_at": event.created_at
                }
            )
        except Exception as e:
            logger.error("[EVENT-BUS-SQLITE-ERR]: Lỗi lưu trữ Cold Path thưa Master: %s", e)

        # 2. Phát sóng nóng thông qua Redis Pub/Sub (Hot Path)
        def _redis_publish(r):
            # Phát tín hiệu lên kênh chung để các monitor/dashboard khác bắt được
            r.publish("monitor:cognitive_events", event_str)
            # Đồng thời ghi vào danh sách sự kiện gần đây của task
            key = f"task_events:{event.task_id}"
            r.rpush(key, event_str)
            r.expire(key, 86400 * 3) # Bảo lưu trong 3 ngày
        
        redis_safe(_redis_publish)

        # 3. Kích hoạt toàn bộ thụ thể đã đăng ký trong Kernel Space bất đồng bộ
        callbacks = self._subscribers.get(event.event_type, [])
        if not callbacks:
            return

        # Thực thi không chặn (fire-and-forget) để không làm nghẽn bus chính
        async def _dispatch_all():
            tasks = []
            for cb in callbacks:
                try:
                    tasks.append(asyncio.create_task(cb(event)))
                except Exception as ex:
                    logger.error("[DISPATCH-ERR]: Thụ thể '%s' lỗi đăng ký: %s", cb.__name__, ex)
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for cb, res in zip(callbacks, results):
                    if isinstance(res, Exception):
                        logger.error("[CALLBACK-EXEC-ERR]: Thụ thể '%s' sập khi xử lý '%s' thưa Master: %s", cb.__name__, event.event_type, res)

        asyncio.create_task(_dispatch_all())

# Singleton Hệ thống thần kinh Bus thưa Master
cognitive_event_bus = CognitiveEventBus()
