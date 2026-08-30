# -*- coding: utf-8 -*-
"""
🗣️ [STREAMING INTERACTIVITY & MID-STREAM CORRECTION v1.0]
File: core/interactive/streaming_interceptor.py

Cơ chế Tương Tác Trực Tuyến & Điều Chỉnh Giữa Chừng (Trụ Cột 8):
  1. Interrupt Signal Listener: Bắt tín hiệu ngắt (Cancel/Interrupt) từ Master khi đang stream.
  2. Safe Partial State Capture: Lưu lại chính xác đoạn văn bản/kết quả đã sinh trước khi ngắt.
  3. Incremental Refinement Engine: Ghép nối đoạn cũ + chỉ thị điều chỉnh mới để tiếp tục tạo câu trả lời.
"""

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("JKAI.StreamingInterceptor")


@dataclass
class ActiveStreamSession:
    session_id: str
    task_id: str
    is_interrupted: bool = False
    partially_generated_text: str = ""
    start_time: float = field(default_factory=time.time)
    interrupted_at: Optional[float] = None
    interruption_reason: str = ""


class StreamingInteractivityManager:
    """
    🗣️ Quản Lý Tương Tác & Điều Chỉnh Hội Thoại Giữa Chừng
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.active_sessions: Dict[str, ActiveStreamSession] = {}

    def register_stream(self, session_id: str, task_id: str) -> ActiveStreamSession:
        """Khởi tạo một phiên stream mới."""
        session = ActiveStreamSession(session_id=session_id, task_id=task_id)
        self.active_sessions[session_id] = session
        return session

    def append_stream_chunk(self, session_id: str, chunk: str) -> None:
        """Cập nhật phần văn bản đang sinh theo thời gian thực."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].partially_generated_text += chunk

    def trigger_interrupt(self, session_id: str, reason: str = "User requested interrupt") -> Dict[str, Any]:
        """Bắt tín hiệu ngắt từ Master và lưu lại trạng thái đang dở dang."""
        if session_id in self.active_sessions:
            sess = self.active_sessions[session_id]
            sess.is_interrupted = True
            sess.interrupted_at = time.time()
            sess.interruption_reason = reason
            logger.info(f"🛑 [MID-STREAM-INTERRUPT]: Session '{session_id}' interrupted at len={len(sess.partially_generated_text)}")
            return {
                "status": "INTERRUPTED",
                "session_id": session_id,
                "saved_partial_text": sess.partially_generated_text,
                "message": "Đã ngắt dòng phản hồi theo yêu cầu của Master. Dữ liệu đã sinh được bảo toàn để tiếp tục điều chỉnh."
            }
        return {"status": "NOT_FOUND", "session_id": session_id}

    def compose_refinement_prompt(
        self,
        session_id: str,
        correction_instruction: str
    ) -> str:
        """
        Ghép nối đoạn đã sinh trước đó cùng chỉ thị mới để model tiếp tục sinh chuẩn xác.
        """
        sess = self.active_sessions.get(session_id)
        if not sess or not sess.partially_generated_text:
            return correction_instruction

        refined_prompt = (
            f"[NGỮ CẢNH ĐÃ SINH TRƯỚC KHI ĐƯỢC MASTER ĐIỀU CHỈNH]:\n"
            f"{sess.partially_generated_text[-500:]}\n\n"
            f"[CHỈ THỊ ĐIỀU CHỈNH CỦA MASTER]:\n"
            f"{correction_instruction}\n\n"
            f"Vui lòng tiếp tục phát triển câu trả lời theo đúng chỉ thị điều chỉnh trên, không lặp lại phần đã viết."
        )
        return refined_prompt


stream_manager = StreamingInteractivityManager()
