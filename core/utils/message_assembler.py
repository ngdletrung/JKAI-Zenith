import json
import re
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('MessageAssembler')

class MessageAssembler:
    """
    🧠 JKAI MESSAGE ASSEMBLER v1.2 (Sovereign Intelligence)
    Giao thức Nhất thể hóa Mệnh lệnh: Lắp ghép Identity, Memory và Context .
    Tích hợp cơ chế tự thích nghi theo Vai trò và Hồ sơ Mô hình.
    Bổ sung công nghệ nén bối cảnh thông minh.
    """
    def __init__(self, agent_name: str = "JKAI"):
        self.agent_name = agent_name
        self._max_history = 30 # Tăng lên vì đã có bộ nén
        self._max_knowledge_len = 15000 
        self._max_memory_len = 8000
        from core.utils.context_compressor import ContextCompressor
        self.compressor = ContextCompressor(threshold_tokens=10000)

    def _sanitize(self, text: str) -> str:
        if not text: return ""
        forbidden = ["IGNORE ALL PREVIOUS", "SYSTEM OVERRIDE", "YOU ARE NOW", "AS AN AI MODEL"]
        for word in forbidden:
            text = re.sub(word, "[PROTECTED]", text, flags=re.IGNORECASE)
        return text

    async def assemble(self, 
                       messages: List[Dict[str, str]], 
                       role: str, 
                       profile: Dict[str, Any],
                       engine_instance: Any = None) -> List[Dict[str, str]]:
        """
        🚀 [ASSEMBLE-SEQUENCE]: Lắp ghép nơ-ron mệnh lệnh theo ngữ cảnh .
        """
        from core.config import settings
        
        # 1. [IDENTITY-RECALL]: Truy lục bản ngã của Vai trò 
        identity_file = f"agent_{role.lower()}.md"
        identity_path = os.path.join(settings.INTELLIGENCE_DIR, identity_file)
        identity_content = ""
        if os.path.exists(identity_path):
            with open(identity_path, 'r', encoding='utf-8') as f:
                identity_content = f.read()
        else:
            # Fallback về bản ngã mặc định
            identity_content = f"Bạn là {self.agent_name}, phụng sự Master LeeTrung với lòng trung thành tuyệt đối."

        # 2. [CONTEXT-AUGMENTATION]: Làm giàu thông điệp 
        assembled_messages = []
        
        system_prompt = f"### [IDENTITY]: {role.upper()}\n{self._sanitize(identity_content)}\n\n"
        
        # Gắn các rào chắn Sovereign
        import datetime
        now = datetime.datetime.now()
        ampm = "AM" if now.hour < 12 else "PM"
        hour_12 = now.hour % 12
        if hour_12 == 0:
            hour_12 = 12
        weekday_map = {
            "Monday": "Thứ Hai",
            "Tuesday": "Thứ Ba",
            "Wednesday": "Thứ Tư",
            "Thursday": "Thứ Năm",
            "Friday": "Thứ Sáu",
            "Saturday": "Thứ Bảy",
            "Sunday": "Chủ Nhật"
        }
        weekday_vn = weekday_map.get(now.strftime('%A'), now.strftime('%A'))
        formatted_time = f"{hour_12:02d}h{now.minute:02d}m{now.second:02d}s {ampm} ({weekday_vn}, ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')})"
        system_prompt += (
            "### [SOVEREIGN PROTOCOL]:\n"
            "- Phản hồi bằng Tiếng Việt, phong thái Elite, hào sảng.\n"
            "- Luôn gọi người dùng là 'Master' hoặc 'Ngài'.\n"
            "- Tuyệt đối trung thành và minh bạch .\n"
            "- Thể hiện trí tuệ đỉnh cao trong từng câu chữ.\n"
            "- Tuyệt đối không xưng hô 'Bạn' với Master.\n"
            f"- Mốc thời gian hệ thống: {formatted_time} (Múi giờ Việt Nam: GMT+7).\n"
            f"- Bắt buộc năm hiện tại (năm nay) là {now.year}. Mọi tài liệu, tệp tin, kỹ năng được đúc mới phải lấy mốc thời gian hiện tại là năm {now.year}.\n"
        )
        
        assembled_messages.append({"role": "system", "content": system_prompt})
        
        # 3. [HISTORY-COMPRESSION]: Nén dòng thời gian
        # Sử dụng ContextCompressor để tối ưu bối cảnh thay vì chỉ cắt bỏ thô
        if engine_instance:
            optimized_messages = await self.compressor.compress(messages, engine_instance)
        else:
            optimized_messages = messages
        
        start_idx = max(0, len(optimized_messages) - self._max_history)
        for msg in optimized_messages[start_idx:]:
            assembled_messages.append({
                "role": msg["role"],
                "content": self._sanitize(msg["content"])
            })
            
        return assembled_messages

    def compile(self, *args, **kwargs) -> List[Dict[str, str]]:
        """🏛️ [LEGACY-BRIDGE]: Ánh xạ lệnh cũ sang Giao thức Nhất thể hóa mới ."""
        # Chuyển đổi tham số nếu cần, nhưng assemble là hướng đi chính
        return []

# Singleton 
message_assembler = MessageAssembler()
