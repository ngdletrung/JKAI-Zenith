---
type: python_file
file: utils/state_machine.py
tags: []
---

# state_machine

import json
import time
import os
import redis

class ZenithStateMachine:
    """
    ⏳ Cỗ Máy Trạng Thái (State Machine & Checkpointing)
    Lưu trữ và phục hồi trạng thái thực thi của các chiến dịch.
    Được chia sẻ qua Redis để cả ai-control-plane và ai-executor đều dùng được.
    """
    def __

## Links to
- [[json]]
- [[time]]
- [[os]]
- [[redis]]
