---
type: python_file
file: utils/event_store.py
tags: []
---

# event_store

import sqlite3
import json
import time
import os
from typing import List, Dict, Any, Optional
from core.utils.hlc import hlc

class EventStore:
    """
    🏛️ [EVENT-STORE]: Lõi lưu trữ sự kiện nơ-ron.
    Triển khai Event Sourcing (ADR-007) để đảm bảo tính nhất quán và khả năng hậu kiểm

## Links to
- [[sqlite3]]
- [[json]]
- [[time]]
- [[os]]
- [[typing]]
- [[core.utils.hlc]]
