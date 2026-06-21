---
type: python_file
file: utils/test_hlc.py
tags: []
---

# test_hlc

import sys
import os
import time

# Thêm đường dẫn
sys.path.append(os.getcwd())

from hlc import hlc, compare_hlc

def test_hlc_monotonicity():
    print("🛡️ [TEST]: Kiểm tra tính đơn điệu của HLC...")
    t1 = hlc.now()
    t2 = hlc.now()
    t3 = hlc.now()
    
    print(f"T1: {t1}")
 

## Links to
- [[sys]]
- [[os]]
- [[time]]
- [[hlc]]
