"""
core/os/cognition/escl/outcome_normalizer.py
E7 — Execution Outcome Normalizer.

Transforms heterogeneous raw tool outputs into typed NormalizedExecutionOutcome objects.
Bridges raw execution with E6 Artifact Semantic Verification.
"""

from __future__ import annotations
import hashlib
import os
import time
from typing import Any, Dict, List
from core.os.cognition.escl.contracts import NormalizedExecutionOutcome


class ExecutionOutcomeNormalizer:
    """Normalizes tool execution results into structured outcomes."""

    def normalize(
        self,
        tool_id: str,
        raw_result: Any,
        execution_id: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> NormalizedExecutionOutcome:
        eid = execution_id or f"exec_{hashlib.sha256(f'{tool_id}:{time.time()}'.encode()).hexdigest()[:10]}"
        
        artifact_paths: List[str] = []
        status = "FAILED"
        stdout = ""
        stderr = ""
        exit_code = 1

        if isinstance(raw_result, dict):
            status_raw = raw_result.get("status", "")
            if status_raw == "success":
                status = "SUCCEEDED"
                exit_code = 0
            elif status_raw == "need_info":
                status = "NEED_INFO"
                exit_code = 0
            else:
                status = "FAILED"
                exit_code = 1

            p = raw_result.get("path") or raw_result.get("file")
            if p and isinstance(p, str) and os.path.exists(p):
                artifact_paths.append(p)

            stdout = str(raw_result.get("content") or raw_result.get("msg") or raw_result.get("question") or "")

        elif isinstance(raw_result, str):
            stdout = raw_result
            if "error" not in raw_result.lower():
                status = "SUCCEEDED"
                exit_code = 0

        return NormalizedExecutionOutcome(
            execution_id=eid,
            tool_id=tool_id,
            status=status,
            artifact_paths=artifact_paths,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            context_hash=hashlib.sha256(stdout.encode("utf-8", errors="ignore")).hexdigest()[:16]
        )


outcome_normalizer = ExecutionOutcomeNormalizer()
