---
type: python_file
file: utils/knowledge_manager.py
tags: []
---

# knowledge_manager

import os
import re
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.utils.engine import engine

# [GLOBAL-RAM-CACHE]: Biến toàn cục dùng chung cho MỌI Đặc vụ (Dispatcher, Planner, Critic, Executor...)
_GLOBAL_SKILLS_CACHE = None
_GLOBAL_REGISTR

## Links to
- [[os]]
- [[re]]
- [[json]]
- [[time]]
- [[typing]]
- [[pathlib]]
- [[core.utils.engine]]
- [[core.config]]
- [[core.qdrant_client]]
- [[core.utils.embed]]
