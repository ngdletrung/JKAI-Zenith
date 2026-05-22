import os
import json
import asyncio
import ast
from pathlib import Path
# Lazy import cho JKAIIntelligenceEngine sẽ được thực hiện bên trong hàm để tránh lỗi crash khi ToolRouter nạp module.

class ZenithEvolutionEngine:
    """
    🧬 JKAI ZENITH: EVOLUTION ENGINE (v15.0)
    Lõi tự cải tiến tối thượng. Có khả năng tự phẫu thuật mã nguồn.
    """
    def __init__(self):
        self.base_dir = Path(os.getenv("INTELLIGENCE_DIR", "/intelligence"))

    async def phau_thuat_logic(self, skill_id, optimization_goal):
        """Tự động viết lại logic.py của một kỹ năng để tối ưu hóa."""
        logic_path = self.base_dir / "skills" / skill_id / "logic.py"
        if not logic_path.exists():
            return f"❌ [ERROR]: Không tìm thấy mã nguồn của {skill_id}."

        current_code = logic_path.read_text(encoding="utf-8")
        
        prompt = f"""
        [GIAO THỨC PHẪU THUẬT GEN v15.0]
        Mục tiêu: Tối ưu hóa mã nguồn của kỹ năng {skill_id}.
        Yêu cầu Master: {optimization_goal}
        
        MÃ NGUỒN HIỆN TẠI:
        {current_code}
        
        NHIỆM VỤ: Hãy viết lại TOÀN BỘ file logic.py với hiệu năng cao hơn, sạch hơn và mạnh mẽ hơn. 
        ⚠️ TUYỆT ĐỐI BẮT BUỘC: Ở cuối file, phải khởi tạo Singleton `_instance = TenClass()` và tạo các hàm Wrapper cấp module (truyền `**kwargs`) để gọi các method của `_instance` (Giao thức Nhất thể hóa ToolRouter).
        Chỉ trả về mã nguồn Python thuần túy.
        """
        
        # Gọi trí tuệ JKAI để phẫu thuật code
        from core.utils.engine import JKAIIntelligenceEngine
        engine = JKAIIntelligenceEngine()
        new_code = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="BAN KỸ THUẬT"
        )
        
        # 🛡️ KIỂM ĐỊNH AN TOÀN (Syntax Check)
        try:
            ast.parse(new_code)
            logic_path.write_text(new_code, encoding="utf-8")
            return f"✅ [EVOLUTION]: Phẫu thuật thành công kỹ năng {skill_id}. Hệ thống đã được nâng cấp gen!"
        except Exception as e:
            return f"❌ [SAFETY-BLOCK]: Mã nguồn mới có lỗi cú pháp ({e}). Đã hủy bỏ tiến trình để bảo vệ hệ thống."

    async def tu_nang_cap_ban_than(self):
        """Giao thức tối thượng: Kỹ năng tự cải tiến chính nó!"""
        return await self.phau_thuat_logic("skill_tucaitien", "Nâng cấp khả năng tự học và tự tối ưu hóa mã nguồn lên cấp độ vĩ mô.")

# 🚀 Lazy singleton - chỉ khởi tạo khi được gọi, không crash khi import
try:
    _instance = ZenithEvolutionEngine()
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning(f"[SKILL-INIT-WARN] {_e}")
    _instance = None


# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện

async def phau_thuat_logic(**kwargs):
    return await _instance.phau_thuat_logic(**kwargs)

async def tu_nang_cap_ban_than(**kwargs):
    return await _instance.tu_nang_cap_ban_than(**kwargs)
