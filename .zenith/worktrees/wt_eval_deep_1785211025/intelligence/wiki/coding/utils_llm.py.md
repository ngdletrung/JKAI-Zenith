---
type: python_file
file: utils/llm.py
tags: []
---

# llm

"""
🧠 LLM Utils V4 — Unified Ollama Caller (Optimized)
- Hỗ trợ nhiều mode: fast, reason, code
- Retry logic + timeout
- Structured output support (JSON)
- Logging chi tiết
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional

import requests

logger = logging

## Links to
- [[os]]
- [[json]]
- [[logging]]
- [[time]]
- [[typing]]
- [[requests]]
