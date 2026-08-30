# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ADAPTIVE COMPACTION ENGINE v2.0                  ║
║   Động Cơ Nén Ngữ Cảnh Chọn Lọc, Bảo Tồn DNA & Fast-Path Heuristic║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Dung Lượng Bộ Nhớ & Trí Nhớ Sống. 🧬🧠✨*
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional

from core.utils.engine import engine
from core.knowledge_sources.fact_distiller import fact_distiller

logger = logging.getLogger("JKAI.Compaction")


class CompactionEngine:
    """
    🏗️ COMPACTION ENGINE v2.0
    Nhiệm vụ: Duy trì sự minh mẫn của ngữ cảnh bằng cách nén lịch sử sự kiện (EventStream) 
    thành các Neo ngữ cảnh (Semantic Anchors) kết hợp bảo tồn Data DNA bất khả xâm phạm.
    """

    def __init__(self, token_limit: int = 4096, threshold: float = 0.8):
        self.token_limit = token_limit
        self.threshold = threshold  # 80% capacity triggers compaction
        self.hard_limit = int(token_limit * threshold)

    def _estimate_tokens(self, history: List[Dict[str, Any]]) -> int:
        """Ước lượng token dựa trên ký tự (1 token ~ 4 chars)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in history)
        return total_chars // 4

    async def condense(self, history: List[Dict[str, Any]], task_id: str = "sys", use_fast_heuristic: bool = True) -> List[Dict[str, Any]]:
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
            if len(content) > 3000:
                return False
            has_numbers = any(char.isdigit() for char in content)
            is_result = "Observation:" in content or "Successfully" in content or "•" in content
            return has_numbers and is_result

        engine.publish_mission_log(
            "COMPACTION", 
            f"🧠 [INTELLIGENT-SCAN]: Ngữ cảnh đạt {estimated} tokens. Đang phân loại dữ liệu để nén chọn lọc...",
            task_id
        )

        # 1. Phân tách cấu trúc
        system_msgs = [m for m in history if m.get("role") == "system"]
        core_msgs = [m for m in history if m.get("role") != "system"]
        
        goal_msg = core_msgs[0:1]
        middle_stream = core_msgs[1:-6]
        recent_stream = core_msgs[-6:]

        to_compress = []
        vital_saved = []

        for m in middle_stream:
            if is_vital(m):
                vital_saved.append(m)
            else:
                to_compress.append(m)

        if len(to_compress) < 3:
            return history

        # 2. [DATA-DNA-EXTRACTION]: Trích xuất DNA số liệu trước khi tóm tắt
        pinned_dna_parts = self._extract_data_dna(to_compress)
        pinned_dna_block = ""
        if pinned_dna_parts:
            pinned_dna_block = (
                "📌 [PINNED-DATA-DNA — KHÔNG ĐƯỢC XÓA]: "
                + " | ".join(pinned_dna_parts[:20])
            )

        history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in to_compress])

        # 3. Tóm tắt ngữ cảnh: Ưu tiên Heuristic Fast-Path nếu use_fast_heuristic=True
        summary = ""
        if use_fast_heuristic:
            # Chưng cất siêu tốc bằng FactDistiller v2.0 (<2ms)
            summary = fact_distiller.distill_facts(history_text, max_facts=4)
        else:
            compression_prompt = (
                "Bạn là COMPRESSOR của hệ thống JKAI Zenith.\n"
                "Nhiệm vụ: Tóm tắt các bước TÌM KIẾM và THỦ TỤC dư thừa.\n"
                "YÊU CẦU BẢO VỆ SỰ THẬT:\n"
                "1. KHÔNG được nén các dữ liệu thực tế nếu thấy chúng.\n"
                "2. Chỉ tóm tắt luồng suy nghĩ: 'Đã tìm kiếm X, đã kiểm tra Y...'\n"
                "3. Giữ cho Semantic DNA cực ngắn."
            )
            try:
                raw_sum = await engine.call_chat(
                    messages=[
                        {"role": "system", "content": compression_prompt},
                        {"role": "user", "content": f"[LOGS TO CONDENSE]:\n{history_text}"}
                    ],
                    role="SUMMARIZER",
                    task_id=task_id,
                    options={"temperature": 0.0}
                )
                if isinstance(raw_sum, dict) and "answer" in raw_sum:
                    summary = raw_sum["answer"]
                else:
                    summary = str(raw_sum)
            except Exception as e:
                logger.warning(f"[COMPACTION-FALLBACK-HEURISTIC]: LLM Summarizer failed ({e}). Using FactDistiller.")
                summary = fact_distiller.distill_facts(history_text, max_facts=4)

        # 4. Tái cấu trúc lịch sử
        new_history = system_msgs.copy()
        new_history.extend(goal_msg)
        new_history.extend(vital_saved)

        if pinned_dna_block:
            new_history.append({
                "role": "system",
                "content": pinned_dna_block
            })

        new_history.append({
            "role": "system",
            "content": f"🏛️ [ARCHIVE_DNA]: Tóm lược tiến trình: {summary}"
        })
        new_history.extend(recent_stream)

        engine.publish_mission_log(
            "COMPACTION", 
            f"✨ [EVOLUTION]: Đã bảo tồn {len(vital_saved)} dữ liệu sống, ghim {len(pinned_dna_parts)} DNA, nén {len(to_compress)} tin nhắn thủ tục.",
            task_id
        )
        return new_history

    def _extract_data_dna(self, messages: list) -> list:
        """Trích xuất các mảnh dữ liệu quan trọng không được tóm tắt."""
        dna_parts = []
        seen = set()

        _PATTERNS = [
            (r"[A-Za-z]:\\[\\\w\-\./]+\.\w{2,6}", "PATH"),
            (r"/[\w\-\./]+\.\w{2,6}", "PATH"),
            (r"https?://[^\s\"'<>]{10,120}", "URL"),
            (r"\b[0-9a-f]{8,64}\b", "HASH"),
            (r"\b\d[\d,\.]*\s*(?:%|VND|VN[ĐD]|USD|\$|dong|đồng|bytes?|KB|MB|GB|TB|token|tokens?|req/s|fps|ms)\b", "VALUE"),
            (r"\b\d{1,3}(?:[,\.]\d{3})+\b", "NUMBER"),
            (r"\b\d{5,}\b", "NUMBER"),
            (r"[\w\-]+\.(?:xlsx?|docx?|pdf|csv|json|yaml|py|js|ts|sql|txt|zip|tar)\b", "FILE"),
        ]

        for msg in messages:
            content = str(msg.get("content", ""))
            for pattern, kind in _PATTERNS:
                for match in re.findall(pattern, content, re.IGNORECASE):
                    m_str = match.strip() if isinstance(match, str) else str(match[0]).strip()
                    if m_str and m_str not in seen and len(m_str) > 3:
                        seen.add(m_str)
                        dna_parts.append(f"[{kind}:{m_str}]")

        return dna_parts


compaction_engine = CompactionEngine()
