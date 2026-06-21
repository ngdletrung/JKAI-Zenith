---
type: python_file
file: ai-brain/omni_parser.py
tags: []
---

# omni_parser

from __future__ import annotations

import ast
import json          # FIX 1: import bị thiếu trong bản gốc
import logging
import os
import re
from abc import ABC, abstractmethod   # FIX 2: enforce interface đúng cách
from collections import defaultdict
from dataclasses import dataclass, field
from p

## Links to
- [[__future__]]
- [[ast]]
- [[json]]
- [[logging]]
- [[os]]
- [[re]]
- [[abc]]
- [[collections]]
- [[dataclasses]]
- [[pathlib]]
- [[typing]]
- [[asyncio]]

## Linked by
- [[ai-brain/knowledge_graph.py]]
