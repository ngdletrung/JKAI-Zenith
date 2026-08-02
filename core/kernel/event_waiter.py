import asyncio
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("EventWaiter")

class EventWaiterManager:
    """
    ⏳ [EVENT-WAITER-MANAGER]: Quản lý việc tạm dừng bất đồng bộ luồng thi công của Agent (Async Waiter)
    để chờ phản hồi trắc nghiệm từ Master trên Web UI / Telegram Bot.
    """
    def __init__(self):
        self._waiters: Dict[str, asyncio.Future] = {}

    def create_waiter(self, question_id: str) -> asyncio.Future:
        """Khởi tạo một Future chờ sự kiện chọn của người dùng."""
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._waiters[question_id] = fut
        logger.info(f"⏳ [WAITER-CREATED]: Bắt đầu chờ phản hồi của Master cho Question `{question_id}`")
        return fut

    def resolve_waiter(self, question_id: str, selection_result: Dict[str, Any]) -> bool:
        """Được gọi bởi WebSocket / API Callback khi Master bấm chọn nút trên UI."""
        fut = self._waiters.get(question_id)
        if fut and not fut.done():
            fut.set_result(selection_result)
            logger.info(f"✅ [WAITER-RESOLVED]: Master đã phản hồi cho Question `{question_id}`: {selection_result}")
            return True
        return False

    async def wait_for_selection(self, question_id: str, timeout_seconds: float = 60.0, default_selection: Any = None) -> Dict[str, Any]:
        """Tạm dừng luồng Agent kiên nhẫn để chờ Master chọn. Nếu quá thời gian timeout, trả về mặc định."""
        fut = self.create_waiter(question_id)
        try:
            result = await asyncio.wait_for(fut, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"⏰ [WAITER-TIMEOUT]: Hết thời gian {timeout_seconds}s chờ Master cho Question `{question_id}`. Sử dụng mặc định.")
            return {"status": "timeout_fallback", "selection": default_selection}
        finally:
            self._waiters.pop(question_id, None)

event_waiter_manager = EventWaiterManager()
