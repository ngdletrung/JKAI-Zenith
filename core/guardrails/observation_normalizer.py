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


@dataclass
class ToolObservation:
    tool_id: str
    invocation_id: str
    status: str              # SUCCESS, FAILED, DENIED
    stdout: str = ""
    stderr: str = ""
    changed_state: Dict[str, Any] = field(default_factory=dict)
    evidence_hash: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.evidence_hash:
            raw_payload = f"{self.tool_id}:{self.invocation_id}:{self.status}:{self.stdout}:{self.stderr}"
            self.evidence_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


class ObservationNormalizer:
    """Standardizes raw tool outputs into immutable ToolObservation objects."""

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

        if isinstance(raw_result, dict):
            stdout = str(raw_result.get("stdout") or raw_result.get("answer") or raw_result.get("output") or json.dumps(raw_result))
            stderr = str(raw_result.get("stderr") or raw_result.get("error") or "")
        elif isinstance(raw_result, str):
            stdout = raw_result
        else:
            stdout = str(raw_result)

        return ToolObservation(
            tool_id=tool_id,
            invocation_id=invocation_id,
            status=status,
            stdout=stdout,
            stderr=stderr,
            changed_state=changed_state or {}
        )
