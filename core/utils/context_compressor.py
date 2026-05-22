import json
import logging
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger('ContextCompressor')

class ContextCompressor:
    """
    🧪 [NEURAL-COMPRESSION v2.0]: Công nghệ nén bối cảnh Hermes-Zenith.
    Tối ưu hóa bộ nhớ nơ-ron bằng cách nén Semantic Trajectory và bảo vệ bối cảnh gần nhất.
    """
    def __init__(self, 
                 threshold_tokens: int = 20000, 
                 protect_head: int = 5, 
                 protect_tail: int = 20):
        self.threshold_tokens = threshold_tokens
        self.protect_head = protect_head
        self.protect_tail = protect_tail
        self._chars_per_token = 4

    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // self._chars_per_token

    def _prune_tool_outputs(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        [SEMANTIC-PRUNING]: Tóm tắt tool output thành 1 dòng giàu thông tin.
        """
        pruned = []
        for msg in messages:
            content = msg.get("content", "")
            if msg.get("role") == "tool" and len(content) > 1000:
                # Trích xuất metadata nếu là JSON
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        summary = f"[tool_result]: List containing {len(data)} items."
                    elif isinstance(data, dict):
                        summary = f"[tool_result]: Object with keys {list(data.keys())}."
                    else:
                        summary = f"[tool_result]: {str(data)[:200]}..."
                except:
                    summary = f"[tool_result]: Raw output ({len(content)} chars). Snippet: {content[:150]}..."
                
                pruned.append({**msg, "content": f"### [PRUNED-TOOL-OUTPUT]:\n{summary}"})
            else:
                pruned.append(msg)
        return pruned

    async def compress(self, messages: List[Dict[str, str]], engine_instance) -> List[Dict[str, str]]:
        """
        🚀 [HERMES-COMPRESSION]: Thực thi nén bối cảnh đa tầng.
        """
        if len(messages) <= (self.protect_head + self.protect_tail + 2):
            return self._prune_tool_outputs(messages)

        tokens = self.estimate_tokens(messages)
        if tokens < self.threshold_tokens:
            return self._prune_tool_outputs(messages)

        logger.info(f"🔄 [HERMES-COMPRESSION]: Đang nén bối cảnh ({tokens} tokens)...")
        
        # 1. Phân đoạn bối cảnh
        head = messages[:self.protect_head]
        tail = messages[-self.protect_tail:]
        middle = messages[self.protect_head:-self.protect_tail]

        # 2. Chuẩn bị nội dung tóm tắt (Middle Summary)
        summary_input = (
            "Hãy tóm tắt cực kỳ súc tích toàn bộ diễn biến hội thoại dưới đây.\n"
            "Chỉ giữ lại: Các quyết định quan trọng, các lỗi đã gặp và cách sửa, các sự kiện file/hệ thống đã thực hiện.\n"
            "Loại bỏ: Các chi tiết kỹ thuật thừa, log code dài dòng.\n\n"
        )
        for msg in middle:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            # Chỉ lấy snippet để tóm tắt cho nhanh
            summary_input += f"[{role}]: {content[:500]}\n\n"

        try:
            # 3. Sử dụng mô hình rẻ (Gemini Flash) để tóm tắt nếu có thể
            summary_result = await engine_instance.chat_completion(
                messages=[{"role": "user", "content": summary_input}],
                role="SUMMARIZER",
                silent_mode=True
            )
            
            summary_text = summary_result if isinstance(summary_result, str) else summary_result.get("summary", str(summary_result))

            # 4. Lắp ghép bối cảnh mới với Fenced Context
            compressed_msg = {
                "role": "system",
                "content": (
                    "<memory-context>\n"
                    "### [HERMES-EVOLUTION: COMPRESSED TRAJECTORY]\n"
                    "Các bước thực thi trước đó đã được nén lại để duy trì trí nhớ vĩnh cửu.\n"
                    f"DIỄN BIẾN CHÍNH:\n{summary_text}\n"
                    "</memory-context>"
                )
            }
            
            return head + [compressed_msg] + tail

        except Exception as e:
            logger.error(f"❌ [COMPRESSION-FAILED]: Hermes compression failed: {e}")
            return self._prune_tool_outputs(messages)


def context_compressor_factory():
    return ContextCompressor()
