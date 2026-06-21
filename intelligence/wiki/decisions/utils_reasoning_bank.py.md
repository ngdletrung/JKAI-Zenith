---
type: python_file
file: utils/reasoning_bank.py
tags: []
---

# reasoning_bank

import json
import time
from typing import List, Dict, Any, Optional
from core.qdrant_client import qdrant_client
from core.utils.embed import embed

class ReasoningBank:
    """
    🧠 [REASONING-BANK]: Đại thư viện nơ-ron tư duy.
    Lưu trữ các mẫu Chain-of-Thought, quyết định kiến trú

## Links to
- [[json]]
- [[time]]
- [[typing]]
- [[core.qdrant_client]]
- [[core.utils.embed]]
