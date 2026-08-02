# 🧬 JKAI Zenith: ADAPTIVE COMPACTION ENGINE (Sovereign Context Condenser)
# Inspired by OpenHands Context Management | Optimized for 0.6B/4B Models

import json
import logging
from typing import List, Dict, Any
from core.utils.engine import engine

logger = logging.getLogger("COMPACTION")

class CompactionEngine:
    """
    🏗️ COMPACTION ENGINE
    Nhiệm vụ: Duy trì sự minh mẫn của nơ-ron bằng cách nén lịch sử sự kiện (EventStream) 
    thành các Neo ngữ cảnh (Semantic Anchors).
    """

    def __init__(self, token_limit: int = 4096, threshold: float = 0.8):
        self.token_limit = token_limit
        self.threshold = threshold  # 80% capacity triggers compaction
        self.hard_limit = int(token_limit * threshold)

    def _estimate_tokens(self, history: List[Dict[str, Any]]) -> int:
        """Ước lượng token dựa trên ký tự (1 token ~ 4 chars)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in history)
        return total_chars // 4

    async def condense(self, history: List[Dict[str, Any]], task_id: str = "sys") -> List[Dict[str, Any]]:
        """
        🧠 [SELECTIVE-COMPACTION-V2]: Giao thức nén chọn lọc thông minh.
        """
        if not history or len(history) < 8:
            return history

        estimated = self._estimate_tokens(history)
        if estimated < self.hard_limit:
            return history

        # 🛡️ [PROTECTION-LOGIC]: Xác định các tin nhắn "bất khả xâm phạm"
        def is_vital(msg):
            content = str(msg.get("content", ""))
            # 🚨 [SIZE-GATE]: Dù là dữ liệu sống nhưng nếu quá dài (>3000 chars) 
            # vẫn phải nén để bảo vệ Context cho mô hình 3B thưa Master.
            if len(content) > 3000: return False
            
            # Giữ lại tin nhắn chứa số liệu quan trọng hoặc kết quả thành công
            has_numbers = any(char.isdigit() for char in content)
            is_result = "Observation:" in content or "Successfully" in content
            return has_numbers and is_result

        engine.publish_mission_log(
            "COMPACTION", 
            f"🧠 [INTELLIGENT-SCAN]: Ngữ cảnh đạt {estimated} tokens. Đang phân loại dữ liệu để nén chọn lọc...",
            task_id
        )

        # 1. Phân tách cấu trúc
        system_msgs = [m for m in history if m.get("role") == "system"]
        core_msgs = [m for m in history if m.get("role") != "system"]
        
        # Luôn giữ lại tin nhắn đầu tiên (Mục tiêu của Master)
        goal_msg = core_msgs[0:1]
        
        # Phân loại phần còn lại
        middle_stream = core_msgs[1:-6]
        recent_stream = core_msgs[-6:]

        to_compress = []
        vital_saved = []

        for m in middle_stream:
            if is_vital(m):
                vital_saved.append(m)
            else:
                to_compress.append(m)

        if len(to_compress) < 3: # Không bõ công nén
            return history

        # 2. Triệu tập SUMMARIZER cho phần rác/thủ tục
        compression_prompt = (
            "Bạn là COMPRESSOR của hệ thống JKAI Zenith.\n"
            "Nhiệm vụ: Tóm tắt các bước TÌM KIẾM và THỦ TỤC dư thừa.\n"
            "YÊU CẦU:\n"
            "1. KHÔNG được nén các dữ liệu thực tế nếu thấy chúng.\n"
            "2. Chỉ tóm tắt luồng suy nghĩ: 'Đã tìm kiếm X, đã kiểm tra Y...'\n"
            "3. Giữ cho Semantic DNA cực ngắn."
        )

        history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in to_compress])
        
        try:
            summary = await engine.call_chat(
                messages=[
                    {"role": "system", "content": compression_prompt},
                    {"role": "user", "content": f"[LOGS TO CONDENSE]:\n{history_text}"}
                ],
                role="SUMMARIZER",
                task_id=task_id,
                options={"temperature": 0.0}
            )

            if isinstance(summary, dict) and "answer" in summary:
                summary = summary["answer"]

            # 3. Tái cấu trúc lịch sử: [SYSTEM] + [GOAL] + [VITAL_DATA] + [DNA] + [RECENT]
            new_history = system_msgs.copy()
            new_history.extend(goal_msg)
            new_history.extend(vital_saved)
            new_history.append({
                "role": "system",
                "content": f"🏛️ [ARCHIVE_DNA]: Tóm lược tiến trình nền: {summary}"
            })
            new_history.extend(recent_stream)

            engine.publish_mission_log(
                "COMPACTION", 
                f"✨ [EVOLUTION]: Đã bảo tồn {len(vital_saved)} dữ liệu sống và nén {len(to_compress)} tin nhắn thủ tục.",
                task_id
            )
            return new_history

        except Exception as e:
            logger.error(f"❌ [COMPACTION-ERR]: {e}")
            return history

# 🚀 SINGLETON
compaction_engine = CompactionEngine()
