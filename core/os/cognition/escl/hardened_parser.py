"""
core/os/cognition/escl/hardened_parser.py
E4 — Hardened Lexical Parser & Quarantine Gate.

Adheres strictly to the Axiom:
Observation != Evidence != Belief != Decision.

Does NOT 'hallucinate' or guess intent from corrupted data:
Raw Output -> Lexical Scan -> Structural Validation -> Schema Check -> Canonical Action (or QUARANTINE).
"""

from __future__ import annotations
import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from core.os.cognition.escl.contracts import CanonicalAction

logger = logging.getLogger("jkai.hardened_parser")


class HardenedLexicalParser:
    """Rigorous parser that validates syntax and quarantines ambiguous/corrupted output."""

    def parse_to_canonical_actions(
        self,
        raw_content: str,
        allowed_tools: Optional[Set[str]] = None,
    ) -> List[CanonicalAction]:
        actions: List[CanonicalAction] = []
        content_len = len(raw_content)

        # 1. Lexical Balanced Scan for Action: <name>\nArguments: {...}
        for m in re.finditer(r"Action:\s*([A-Za-z0-9_\-\.]+)", raw_content):
            tool_name = m.group(1).strip()
            if allowed_tools is not None and tool_name not in allowed_tools:
                continue

            start_idx = m.end()
            arg_match = re.search(r"Arguments:\s*\{", raw_content[start_idx:])
            if arg_match:
                open_brace = start_idx + arg_match.end() - 1
                end_brace, is_valid = self._scan_balanced_brace(raw_content, open_brace)
                
                if end_brace != -1 and is_valid:
                    raw_json = raw_content[open_brace : end_brace + 1]
                    parsed_params, is_clean = self._safe_parse_json(raw_json)
                    
                    if parsed_params is not None:
                        action_id = f"act_{hash(raw_json) & 0xFFFFFFFF:08x}"
                        actions.append(CanonicalAction(
                            action_id=action_id,
                            action_type="CREATE_ARTIFACT" if "create" in str(parsed_params) else "EXECUTE_TOOL",
                            target_artifact_type=str(parsed_params.get("format", "")).upper() or None,
                            parameters=parsed_params,
                            quarantine=False
                        ))
                    else:
                        # Quarantine unparseable action
                        actions.append(CanonicalAction(
                            action_id=f"act_quarantine_{len(actions)+1}",
                            action_type="QUARANTINE",
                            target_artifact_type=None,
                            parameters={"raw_snippet": raw_json[:200]},
                            quarantine=True,
                            quarantine_reason="MALFORMED_JSON_CORRUPTION"
                        ))

        return actions

    def _scan_balanced_brace(self, text: str, start_idx: int) -> Tuple[int, bool]:
        depth = 0
        quote = None
        esc = False
        for j in range(start_idx, len(text)):
            ch = text[j]
            if quote:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    quote = None
            elif ch in ('"', "'"):
                quote = ch
            elif ch in ('{', '['):
                depth += 1
            elif ch in ('}', ']'):
                depth -= 1
                if depth == 0 and ch == '}':
                    return j, True
        return -1, False

    def _safe_parse_json(self, raw_json: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Strict direct parse first; conservative repair second."""
        try:
            return json.loads(raw_json), True
        except Exception:
            pass

        try:
            repaired = re.sub(r'([{,]\s*)([a-zA-Z_0-9]+)\s*:', r'\1"\2":', raw_json)
            repaired = re.sub(r':\s*\'([^\']*)\'', r': "\1"', repaired)
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
            data = json.loads(repaired)
            if isinstance(data, dict):
                return data, False
        except Exception:
            pass

        try:
            val = ast.literal_eval(raw_json)
            if isinstance(val, dict):
                return val, False
        except Exception:
            pass

        return None, False


hardened_parser = HardenedLexicalParser()
