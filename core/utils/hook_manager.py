import asyncio
import logging
from typing import List, Callable, Any, Dict

logger = logging.getLogger("JKAI.HookManager")

class HookManager:
    """
    🪝 [HOOK-MANAGER]: Quản lý vòng đời tác vụ.
    Cho phép đăng ký các nơ-ron phản xạ (Pre/Post hooks).
    """
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {
            "pre_plan": [],
            "post_plan": [],
            "pre_tool": [],
            "post_tool": [],
            "on_error": []
        }

    def register(self, hook_type: str, func: Callable):
        """Đăng ký một nơ-ron phản xạ mới."""
        if hook_type in self._hooks:
            self._hooks[hook_type].append(func)
            logger.info(f"🪝 [REGISTERED]: Hook {hook_type} -> {func.__name__}")

    async def trigger(self, hook_type: str, *args, **kwargs):
        """Kích hoạt chuỗi nơ-ron phản xạ."""
        if hook_type not in self._hooks: return
        
        tasks = []
        for func in self._hooks[hook_type]:
            if asyncio.iscoroutinefunction(func):
                tasks.append(func(*args, **kwargs))
            else:
                # Chạy đồng bộ trong thread pool nếu cần
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, lambda: func(*args, **kwargs)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Singleton
hook_manager = HookManager()
