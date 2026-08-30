"""
JKAI ZENITH AI OS — OBSERVATION NORMALIZER
File: core/guardrails/observation_normalizer.py

Normalizes execution output from all system tools into a uniform ToolObservation schema.
Computes SHA-256 evidence hash for non-repudiable auditing.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class ToolOutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY_RESULT = "EMPTY_RESULT"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"


@dataclass
class ToolObservation:
    tool_id: str
    invocation_id: str
    status: str              # SUCCESS, EMPTY_RESULT, SCHEMA_ERROR, EXECUTION_ERROR, DENIED
    stdout: str = ""
    stderr: str = ""
    error_code: str = ""
    retryable: bool = True
    suggested_action: str = ""
    changed_state: Dict[str, Any] = field(default_factory=dict)
    evidence_hash: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.evidence_hash:
            raw_payload = f"{self.tool_id}:{self.invocation_id}:{self.status}:{self.error_code}:{self.stdout}:{self.stderr}"
            self.evidence_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def to_llm_feedback(self) -> str:
        """Formats normalized ToolObservation into clear, unambiguous LLM feedback."""
        if self.status == ToolOutcomeStatus.SUCCESS.value:
            return f"[TOOL-RESULT SUCCESS] Tool='{self.tool_id}' | Output:\n{self.stdout}"
        else:
            return (
                f"[TOOL-RESULT {self.status}] Tool='{self.tool_id}' | ErrorCode={self.error_code}\n"
                f"Details: {self.stderr or self.stdout}\n"
                f"Suggested Recovery Action: {self.suggested_action or 'Inspect parameters or switch tool primitive.'}"
            )


class ObservationNormalizer:
    """Standardizes raw tool outputs into immutable ToolObservation objects with typed error semantics."""

    @classmethod
    def normalize(
        cls, 
        tool_id: str, 
        invocation_id: str, 
        raw_result: Any, 
        status: str = "SUCCESS",
        changed_state: Optional[Dict[str, Any]] = None
    ) -> ToolObservation:
        stdout = ""
        stderr = ""
        error_code = ""
        suggested_action = ""
        retryable = True

        if isinstance(raw_result, dict):
            stdout = str(raw_result.get("stdout") or raw_result.get("answer") or raw_result.get("output") or raw_result.get("content") or "")
            stderr = str(raw_result.get("stderr") or raw_result.get("error") or raw_result.get("msg") or "")
            if not stdout and raw_result.get("items"):
                stdout = json.dumps(raw_result.get("items"), ensure_ascii=False)
            elif not stdout:
                stdout = json.dumps(raw_result, ensure_ascii=False)
                
            # Classify error semantics
            if raw_result.get("status") == "error" or stderr:
                err_lower = stderr.lower()
                if "missing" in err_lower or "parameter" in err_lower or "argument" in err_lower or "invalid" in err_lower:
                    status = ToolOutcomeStatus.SCHEMA_ERROR.value
                    error_code = "INVALID_ARGUMENT_SCHEMA"
                    suggested_action = "Inspect tool parameter signature and pass valid required fields."
                else:
                    status = ToolOutcomeStatus.EXECUTION_ERROR.value
                    error_code = "EXECUTION_FAILURE"
                    suggested_action = "Check file path existence or target availability."
            elif not stdout or stdout.strip() in ["[]", "{}", '""', "''", "None"]:
                status = ToolOutcomeStatus.EMPTY_RESULT.value
                error_code = "NO_MATCHES_FOUND"
                suggested_action = "Widen search path or try alternate search keywords."
        elif isinstance(raw_result, str):
            stdout = raw_result
            if not stdout.strip() or stdout.strip() in ["[]", "{}", "No output."]:
                status = ToolOutcomeStatus.EMPTY_RESULT.value
                error_code = "NO_MATCHES_FOUND"
                suggested_action = "Try listing files or widening search scope."
        else:
            stdout = str(raw_result)

        return ToolObservation(
            tool_id=tool_id,
            invocation_id=invocation_id,
            status=status,
            stdout=stdout,
            stderr=stderr,
            error_code=error_code,
            retryable=retryable,
            suggested_action=suggested_action,
            changed_state=changed_state or {}
        )
