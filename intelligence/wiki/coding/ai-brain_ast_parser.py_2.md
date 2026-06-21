---
type: python_file
file: ai-brain/ast_parser.py
tags: []
---

# ast_parser

import ast
import os
from typing import Dict, List, Any

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports = []
        self.definitions = []
        self.calls = []
        self.current_scope = []
        
    def visit

## Links to
- [[ast]]
- [[os]]
- [[typing]]
