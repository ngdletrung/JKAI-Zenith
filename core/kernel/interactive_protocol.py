import os
import sys
import json
import logging
import uuid
from core.kernel.event_waiter import event_waiter_manager

logger = logging.getLogger("InteractiveProtocol")

class InteractiveProtocol:
    """
    ❓ [INTERACTIVE-QUESTION-PROTOCOL]: Giao thức tạo câu hỏi tương tác đa lựa chọn (Multiple-Choice UI Card).
    Hỗ trợ CLI Terminal Interactive Menu, WebSocket Dispatcher và Async Event Waiter chờ phản hồi Master.
    """
    @staticmethod
    async def ask_question_async(question: str, options: list, is_multi_select: bool = False, timeout_seconds: float = 60.0) -> dict:
        """Tạo câu hỏi trắc nghiệm, đẩy tín hiệu UI Card và TẠM DỪNG LUỒNG chờ Master chọn trên UI."""
        question_id = f"q_{uuid.uuid4().hex[:8]}"
        card = {
            "type": "interactive_modal_question",
            "question_id": question_id,
            "question": question,
            "options": options,
            "is_multi_select": is_multi_select,
            "status": "WAITING_USER_SELECTION"
        }
        logger.info(f"❓ [ASK-QUESTION-ASYNC]: Khởi tạo câu hỏi ID `{question_id}`: '{question}'")

        try:
            from core.utils.engine import engine
            r = engine._get_redis()
            if r:
                r.xadd("stream:ui:interactive_questions", {"payload": json.dumps(card, ensure_ascii=False)}, maxlen=500)
        except Exception:
            pass

        # Tạm dừng bất đồng bộ luồng chờ Master phản hồi
        default_val = options[0] if options else None
        res = await event_waiter_manager.wait_for_selection(question_id, timeout_seconds=timeout_seconds, default_selection=default_val)
        return res

    @staticmethod
    def ask_question(question: str, options: list, is_multi_select: bool = False, auto_prompt_cli: bool = False) -> dict:
        """Tạo cấu trúc thẻ câu hỏi trắc nghiệm chuẩn UI Modal và gửi tín hiệu tương tác."""
        card = {
            "type": "interactive_modal_question",
            "question": question,
            "options": options,
            "is_multi_select": is_multi_select,
            "status": "WAITING_USER_SELECTION"
        }
        logger.info(f"❓ [ASK-QUESTION]: Khởi tạo câu hỏi làm rõ ý định: '{question}' ({len(options)} options)")
        
        # Đẩy tín hiệu tới Redis Stream để Frontend / Telegram Bot hiển thị Interactive Button Card
        try:
            from core.utils.engine import engine
            r = engine._get_redis()
            if r:
                r.xadd("stream:ui:interactive_questions", {"payload": json.dumps(card, ensure_ascii=False)}, maxlen=500)
        except Exception:
            pass

        # Nếu đang ở chế độ CLI trực tiếp, hiển thị menu trắc nghiệm tương tác
        if auto_prompt_cli and sys.stdin.isatty():
            return InteractiveProtocol.prompt_user_cli(question, options)

        return card

    @staticmethod
    def prompt_user_cli(question: str, options: list) -> dict:
        """Hiển thị giao diện menu trắc nghiệm tương tác trực tiếp trên Terminal CLI."""
        print("\n" + "═"*60)
        print(f"❓ [INTERACTIVE QUESTION]: {question}")
        print("─"*60)
        for idx, opt in enumerate(options, 1):
            print(f"  [{idx}] {opt}")
        print("═"*60)
        try:
            choice = input("👉 Nhập số thứ tự lựa chọn của Master: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                selected = options[int(choice) - 1]
                return {"status": "user_selected", "selection": selected, "choice_index": int(choice)}
        except Exception:
            pass
        return {"status": "default_fallback", "selection": options[0]}

interactive_protocol = InteractiveProtocol()
