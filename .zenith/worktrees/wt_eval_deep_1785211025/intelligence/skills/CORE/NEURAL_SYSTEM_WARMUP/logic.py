import asyncio
from core.utils.engine import engine

class WarmupSkill:
    """
    Skill để chủ động triệu hồi các quân đoàn nơ-ron chiến lược.
    """
    def __init__(self):
        pass

    async def warmup(self, **kwargs):
        """
        🚀 Giao thức Triệu hồi Toàn quân: Kích hoạt trạng thái 'Thức tỉnh' cho các model Elite.
        """
        # engine.warmup_all_models() là một coroutine
        # Chúng ta chạy nó và trả về thông báo cho Master
        asyncio.create_task(engine.warmup_all_models())
        return {
            "status": "success",
            "msg": "🚀 [NEURAL-WARMUP]: Đã kích hoạt giao thức triệu hồi toàn quân. Các đặc vụ đang lần lượt tiến vào VRAM.",
            "details": "Các đặc vụ nòng cốt (PLANNER/EXECUTOR) sẽ được ưu tiên nạp trước."
        }

# Đăng ký instance
_instance = WarmupSkill()
warmup = _instance.warmup
