"""
Progress Budget & Loop Detector for ProjectAgentLoop.
Tracks action history to detect consecutive duplicates, cycle oscillations (e.g. A -> B -> A -> B),
and stagnation without meaningful state mutations.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional


class ProgressSignal(str, Enum):
    PROCEED = "PROCEED"
    LOOP_DETECTED = "LOOP_DETECTED"
    NO_PROGRESS = "NO_PROGRESS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class ProgressBudget:
    def __init__(self, max_steps: int = 18, loop_threshold: int = 2):
        self.max_steps = max_steps
        self.loop_threshold = loop_threshold
        self.history: List[str] = []
        self.step_count = 0

    def _signature(self, tool: str, params: Dict[str, Any]) -> str:
        norm_tool = str(tool or "none").strip().lower()
        clean_params = {}
        for k, v in sorted((params or {}).items()):
            if k.lower() in ("path", "absolutepath", "targetfile", "target_path", "file_path", "command"):
                clean_params[k.lower()] = str(v).replace("\\", "/").strip().lower()
            elif k.lower() in ("targetcontent", "replacementcontent", "query"):
                clean_params[k.lower()] = str(v)[:100].strip()
        return f"{norm_tool}::{json.dumps(clean_params, sort_keys=True)}"

    def register_action(
        self,
        tool: str,
        params: Optional[Dict[str, Any]] = None,
        outcome_ok: bool = True
    ) -> ProgressSignal:
        self.step_count += 1
        sig = self._signature(tool, params or {})
        self.history.append(sig)

        if self.step_count >= self.max_steps:
            return ProgressSignal.BUDGET_EXHAUSTED

        # 1. Check direct consecutive repetitions: A == B == C
        if len(self.history) >= self.loop_threshold + 1:
            recent = self.history[-(self.loop_threshold + 1):]
            if len(set(recent)) == 1:
                return ProgressSignal.LOOP_DETECTED

        # 2. Check 2-step oscillation: A -> B -> A -> B
        if len(self.history) >= 4:
            if self.history[-1] == self.history[-3] and self.history[-2] == self.history[-4]:
                return ProgressSignal.LOOP_DETECTED

        # 3. Check 3-step oscillation: A -> B -> C -> A -> B -> C
        if len(self.history) >= 6:
            if (
                self.history[-1] == self.history[-4]
                and self.history[-2] == self.history[-5]
                and self.history[-3] == self.history[-6]
            ):
                return ProgressSignal.LOOP_DETECTED

        # 4. Check repeated non-progress / failures
        if not outcome_ok and len(self.history) >= 3:
            if self.history[-1] == self.history[-2]:
                return ProgressSignal.NO_PROGRESS

        return ProgressSignal.PROCEED
