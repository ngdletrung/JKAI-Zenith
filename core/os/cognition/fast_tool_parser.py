"""
core/os/cognition/fast_tool_parser.py
Lexical Balanced-Brace Tool Parser with Deep Recursion and Loose JSON Repair.
"""

from __future__ import annotations
import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("jkai.fast_tool_parser")


def extract_tool_calls_lexical(content: str, allowed: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """
    Extracts structured tool calls from raw model text output using lexical balanced-brace scanning.
    """
    calls = []
    content_len = len(content)

    # ── Format 1: Action: <name>\nArguments: {...} (Balanced Object Scanner) ──
    for m in re.finditer(r"Action:\s*([A-Za-z0-9_\-\.]+)", content):
        name = m.group(1).strip()
        if allowed is not None and name not in allowed:
            continue
        start_idx = m.end()
        arg_match = re.search(r"Arguments:\s*\{", content[start_idx:])
        if arg_match:
            open_brace_idx = start_idx + arg_match.end() - 1
            depth = 0
            quote_ch = None
            esc = False
            end_brace_idx = -1
            for j in range(open_brace_idx, content_len):
                ch = content[j]
                if quote_ch:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == quote_ch:
                        quote_ch = None
                elif ch in ('"', "'"):
                    quote_ch = ch
                elif ch in ('{', '['):
                    depth += 1
                elif ch in ('}', ']'):
                    depth -= 1
                    if depth == 0 and ch == '}':
                        end_brace_idx = j
                        break
            if end_brace_idx != -1:
                raw_json = content[open_brace_idx : end_brace_idx + 1]
                args = _repair_and_parse_json(raw_json)
                if isinstance(args, dict):
                    calls.append({
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                        }
                    })

    # ── Format 2: Action: <name>(key=val, ...) (Balanced Function Call Scanner) ──
    for m in re.finditer(r"Action:\s*([A-Za-z0-9_\-\.]+)\s*\(", content):
        name = m.group(1).strip()
        if allowed is not None and name not in allowed:
            continue
        start_paren = m.end() - 1
        depth = 0
        quote_ch = None
        esc = False
        end_paren = -1
        for j in range(start_paren, content_len):
            ch = content[j]
            if quote_ch:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote_ch:
                    quote_ch = None
            elif ch in ('"', "'"):
                quote_ch = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end_paren = j
                    break
        if end_paren != -1:
            raw_kwargs = content[start_paren + 1 : end_paren]
            args = _parse_kwargs_string(raw_kwargs)
            if args:
                calls.append({
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args, ensure_ascii=False)
                    }
                })

    return calls


def _repair_and_parse_json(raw_json: str) -> Optional[Dict[str, Any]]:
    """Attempts direct json.loads, then applies progressive AST and regex repairs."""
    try:
        return json.loads(raw_json)
    except Exception:
        pass

    try:
        repaired = re.sub(r'([{,]\s*)([a-zA-Z_0-9]+)\s*:', r'\1"\2":', raw_json)
        repaired = re.sub(r':\s*\'([^\']*)\'', r': "\1"', repaired)
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        return json.loads(repaired)
    except Exception:
        pass

    try:
        val = ast.literal_eval(raw_json)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    return None


def _parse_kwargs_string(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    parts = []
    start = 0
    quote = None
    depth = 0
    esc = False
    for idx, ch in enumerate(raw):
        if quote:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch in ("{", "[", "("):
            depth += 1
        elif ch in ("}", "]", ")"):
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(raw[start:idx])
            start = idx + 1
    parts.append(raw[start:])
    args = {}
    for part in parts:
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key or not key.isidentifier() or not value:
            continue
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            parsed = value.strip("'\"")
        args[key] = parsed
    return args
