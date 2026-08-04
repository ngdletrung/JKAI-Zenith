import logging
from typing import List, Dict

logger = logging.getLogger("CognitiveMemoryBuffer")

class CognitiveMemoryBuffer:
    """
    🧠 [COGNITIVE-MEMORY-BUFFER]: Bộ Đệm Quản lý Ngữ cảnh Nén Tự Động cho Cuộc Thoại Đa Lượt.
    Duy trì trạng thái bối cảnh cuộc trò chuyện dài hạn mà không bị trôi ngữ cảnh (Context Drift) hay quá tải VRAM.
    """
    def __init__(self, max_history_turns: int = 10, max_token_budget: int = 8192):
        self.max_history_turns = max_history_turns
        self.max_token_budget = max_token_budget
        self.engram_summary = ""

    def _estimate_tokens(self, text: str) -> int:
        """Ước lượng số token dựa trên độ dài text (~4 ký tự mỗi token)."""
        return len(text) // 4

    def compress_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Nén danh sách tin nhắn lịch sử, chuyển các tin nhắn cũ hơn max_history_turns thành bản tóm tắt Engram."""
        if not messages or len(messages) <= self.max_history_turns * 2:
            return messages

        total_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)
        if total_tokens <= self.max_token_budget:
            return messages

        system_msg = None
        user_assistant_turns = []

        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
            else:
                user_assistant_turns.append(msg)

        recent_turns = user_assistant_turns[-(self.max_history_turns * 2):]
        old_turns = user_assistant_turns[:-(self.max_history_turns * 2)]

        old_text_block = "\n".join([f"{m.get('role').upper()}: {m.get('content')[:200]}" for m in old_turns])
        self.engram_summary = f"[ENGRAM-SUMMARY]: Tóm tắt {len(old_turns)} tin nhắn trước đó:\n{old_text_block[:1000]}"

        compressed_list = []
        if system_msg:
            new_system = dict(system_msg)
            new_system["content"] += f"\n\n<engram_memory>\n{self.engram_summary}\n</engram_memory>"
            compressed_list.append(new_system)
        else:
            compressed_list.append({"role": "system", "content": f"<engram_memory>\n{self.engram_summary}\n</engram_memory>"})

        compressed_list.extend(recent_turns)
        pruned = total_tokens - sum(self._estimate_tokens(m.get("content", "")) for m in compressed_list)
        logger.info("[MEMORY-COMPRESSED]: Đã nén %s tin nhắn cũ (~%s tokens) vào Engram Summary. Giữ lại %s tin nhắn gần nhất.", len(old_turns), pruned, len(recent_turns))
        return compressed_list

cognitive_memory_buffer = CognitiveMemoryBuffer()
