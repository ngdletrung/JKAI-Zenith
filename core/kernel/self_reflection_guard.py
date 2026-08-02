import re
import logging
from typing import Dict, Any

logger = logging.getLogger("SelfReflectionGuard")

class SelfReflectionGuard:
    """
    🛡️ [SELF-REFLECTION-GUARD]: Động cơ Phản biện Chống Ảo giác & Code Dở dang.
    Tự động quét phản hồi của LLM để phát hiện các placeholder giả lập (TODO, example.com, code cắt ngang)
    và kích hoạt phản biện yêu cầu hoàn thiện 100%.
    """
    FORBIDDEN_PATTERNS = [
        r"TODO",
        r"your_api_key",
        r"example\.com",
        r"insert_code_here",
        r"replace_with_",
        r"Executed .* under physical-ready sandbox" # 123-char Fallback Stub detector!
    ]

    def audit_response(self, text: str) -> Dict[str, Any]:
        """Kiểm tra xem câu trả lời có chứa placeholder hoặc code dở dang hay không."""
        if not text:
            return {"is_clean": False, "reason": "Empty response"}

        found_issues = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found_issues.append(pattern)

        if found_issues:
            logger.warning(f"🛡️ [REFLECTION-WARN]: Phát hiện placeholder/stub vi phạm: {found_issues}")
            return {
                "is_clean": False,
                "reason": f"Phản hồi chứa placeholder hoặc stub vi phạm: {', '.join(found_issues)}",
                "issues": found_issues
            }

        return {"is_clean": True, "reason": "Clean response"}

    async def reflect_and_fix_if_needed(self, original_goal: str, raw_response: str, role: str = "RECEPTIONIST") -> str:
        """Nếu phát hiện vi phạm, kích hoạt phản biện để ép LLM viết lại bản hoàn chỉnh 100%."""
        audit = self.audit_response(raw_response)
        if audit["is_clean"]:
            return raw_response

        logger.info(f"🔄 [REFLECTION-TRIGGERED]: Đang yêu cầu LLM sửa lại câu trả lời dở dang...")
        from core.utils.engine import engine

        fix_prompt = [
            {"role": "system", "content": "Bạn là Tác tử Phản biện Chống Placeholder. Phản hồi trước của bạn bị chặn vì chứa placeholder hoặc stub dở dang. Hãy viết lại bản mã nguồn / câu trả lời HOÀN CHỈNH 100% không dùng placeholder hay code ví dụ."},
            {"role": "user", "content": f"Yêu cầu ban đầu: {original_goal}\n\nPhản hồi lỗi trước đó:\n{raw_response}\n\nLý do bị từ chối: {audit['reason']}\n\nHãy viết lại bản hoàn chỉnh 100%:"}
        ]

        fixed_text = await engine.call_chat(fix_prompt, role=role, skip_build_final=True)
        return fixed_text or raw_response

self_reflection_guard = SelfReflectionGuard()
