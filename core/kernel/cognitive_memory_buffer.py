# -*- coding: utf-8 -*-
"""
core/kernel/cognitive_memory_buffer.py
🧠 [COGNITIVE-MEMORY-BUFFER v2.0]: Bộ Đệm Quản lý Ngữ cảnh Nén Tự Động cho Cuộc Thoại Đa Lượt.
Bịt kín lỗ hổng P0.1: Phân lập không gian bộ nhớ ephemeral theo MissionID,
ngăn chặn triệt để rò rỉ ngữ cảnh (State Contamination & Cache Leak).
"""

import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("CognitiveMemoryBuffer")


class CognitiveMemoryBuffer:
    """
    Context Window Governor & Ephemeral Memory Manager.
    Duy trì trạng thái bối cảnh cuộc trò chuyện dài hạn mà không bị trôi ngữ cảnh (Context Drift),
    đồng thời cô lập tuyệt đối dữ liệu giữa các Mission.
    """
    def __init__(self, max_history_turns: int = 10, max_token_budget: int = 8192):
        self.max_history_turns = max_history_turns
        self.max_token_budget = max_token_budget
        self._mission_engrams: Dict[str, str] = {}
        self._default_engram: str = ""

    @property
    def engram_summary(self) -> str:
        """Backward compatibility property returning the default or most recent engram."""
        return self._default_engram

    @engram_summary.setter
    def engram_summary(self, val: str) -> None:
        self._default_engram = val
        self._mission_engrams["default"] = val

    def _estimate_tokens(self, text: str) -> int:
        """Ước lượng số token dựa trên độ dài text (~4 ký tự mỗi token)."""
        return len(text) // 4 if text else 0

    def get_mission_engram(self, mission_id: str = "default") -> str:
        """Truy xuất memory engram của riêng mission chỉ định."""
        return self._mission_engrams.get(mission_id, "")

    def clear_mission(self, mission_id: str) -> None:
        """
        P0.1 Ephemeral Scope Cleanup:
        Tiêu hủy hoàn toàn không gian bộ nhớ của mission khi vòng đời kết thúc.
        """
        if mission_id in self._mission_engrams:
            del self._mission_engrams[mission_id]
            logger.info("🧹 [P0.1-PURGE] Cleaned ephemeral memory for mission '%s'", mission_id)
        if mission_id == "default":
            self._default_engram = ""

    def clear_all(self) -> None:
        """Dọn sạch toàn bộ bộ nhớ đệm."""
        self._mission_engrams.clear()
        self._default_engram = ""

    @staticmethod
    def generate_cache_key(mission_id: str, payload: Any) -> str:
        """
        P0.1 Trace Keying cho Cache:
        Mọi key cache buộc phải gắn tiền tố MissionID hoặc hash bất biến của đầu vào.
        cache_key = hash(MissionID + InputPayload)
        """
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        else:
            payload_str = str(payload)
        
        raw_key = f"{mission_id}:{payload_str}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def compress_messages(
        self,
        messages: List[Dict[str, str]],
        mission_id: str = "default"
    ) -> List[Dict[str, str]]:
        """
        Nén danh sách tin nhắn lịch sử, chuyển các tin nhắn cũ hơn max_history_turns
        thành bản tóm tắt Engram lưu riêng theo MissionID.
        """
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

        old_text_block = "\n".join([f"{m.get('role', '').upper()}: {str(m.get('content', ''))[:200]}" for m in old_turns])
        summary = f"[ENGRAM-SUMMARY]: Tóm tắt {len(old_turns)} tin nhắn trước đó (Mission: {mission_id}):\n{old_text_block[:1000]}"
        
        # Scoped to mission_id
        self._mission_engrams[mission_id] = summary
        self._default_engram = summary

        compressed_list = []
        if system_msg:
            new_system = dict(system_msg)
            new_system["content"] += f"\n\n<engram_memory mission_id=\"{mission_id}\">\n{summary}\n</engram_memory>"
            compressed_list.append(new_system)
        else:
            compressed_list.append({
                "role": "system",
                "content": f"<engram_memory mission_id=\"{mission_id}\">\n{summary}\n</engram_memory>"
            })

        compressed_list.extend(recent_turns)
        pruned = total_tokens - sum(self._estimate_tokens(m.get("content", "")) for m in compressed_list)
        logger.info(
            "[MEMORY-COMPRESSED]: Mission '%s' - Đã nén %s tin nhắn cũ (~%s tokens) vào Scoped Engram Summary. Giữ lại %s tin nhắn gần nhất.",
            mission_id, len(old_turns), pruned, len(recent_turns)
        )
        return compressed_list


cognitive_memory_buffer = CognitiveMemoryBuffer()
