---
type: python_file
file: utils/hook_manager.py
tags: []
---

# hook_manager

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


## Links to
- [[asyncio]]
- [[logging]]
- [[typing]]
