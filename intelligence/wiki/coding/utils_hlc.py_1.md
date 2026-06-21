---
type: python_file
file: utils/hlc.py
tags: []
---

# hlc

import time
import threading
from typing import Dict, Any, Optional

class HlcTimestamp:
    """
    🧬 [HLC-DNA]: Hybrid Logical Clock Timestamp.
    Nhất thể hóa thời gian vật lý và thứ tự logic.
    """
    def __init__(self, physical_ms: int, logical: int, node_id: str):
      

## Links to
- [[time]]
- [[threading]]
- [[typing]]

## Linked by
- [[utils/test_hlc.py]]
