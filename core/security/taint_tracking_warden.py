# -*- coding: utf-8 -*-
"""
core/security/taint_tracking_warden.py
======================================
Information-Flow Taint Tracking Engine (Phase A7 / SOTA 2).
Enforces provenance labels (`TRUSTED_SYSTEM`, `TRUSTED_MASTER`, `UNTRUSTED_EXTERNAL`)
and prevents untrusted external web/retrieval payloads from directly invoking
privileged execution sinks (`terminal_exec`, `write_file`, `delete_file`, `execute_command`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set


class ProvenanceLevel(str, Enum):
    TRUSTED_SYSTEM = "TRUSTED_SYSTEM"
    TRUSTED_MASTER = "TRUSTED_MASTER"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"


HIGH_IMPACT_SINKS: Set[str] = {
    "terminal_exec",
    "execute_command",
    "write_file",
    "replace_file_content",
    "delete_file",
    "system_core_executor",
    "bash",
    "powershell",
}


class TaintViolationError(PermissionError):
    """Raised when an UNTRUSTED_EXTERNAL payload attempts to trigger a privileged sink without Master approval."""


@dataclass(frozen=True)
class TaintedValue:
    """Immutable wrapper binding a value to its cryptographic SHA-256 digest and provenance label."""

    content: str
    provenance: ProvenanceLevel
    source_uri: str = ""
    sha256: str = field(default="")
    sanitized: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sha256:
            digest = hashlib.sha256(str(self.content or "").encode("utf-8")).hexdigest()
            object.__setattr__(self, "sha256", digest)

    @property
    def is_untrusted(self) -> bool:
        return self.provenance == ProvenanceLevel.UNTRUSTED_EXTERNAL

    def to_envelope(self) -> str:
        """Frames untrusted data explicitly so the reasoning model treats it strictly as data, never instructions."""
        if self.provenance == ProvenanceLevel.UNTRUSTED_EXTERNAL:
            return (
                f"[UNTRUSTED_WEB_CONTENT source=\"{self.source_uri}\" sha256=\"{self.sha256}\"]\n"
                f"{self.content}\n"
                f"[/UNTRUSTED_WEB_CONTENT]"
            )
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provenance": self.provenance.value,
            "source_uri": self.source_uri,
            "sha256": self.sha256,
            "sanitized": self.sanitized,
            "metadata": dict(self.metadata),
        }


class TaintTrackingWarden:
    """
    Deterministic Information-Flow Guard:
    1. Propagates worst-case taint across combined inputs (`UNTRUSTED_EXTERNAL` dominates).
    2. Blocks `UNTRUSTED_EXTERNAL` values from flowing into high-impact execution sinks
       unless explicit Master endorsement (`master_approved=True`) is provided.
    """

    @staticmethod
    def tag_external(content: str, source_uri: str = "", metadata: Optional[Dict[str, Any]] = None) -> TaintedValue:
        return TaintedValue(
            content=str(content or ""),
            provenance=ProvenanceLevel.UNTRUSTED_EXTERNAL,
            source_uri=source_uri,
            sanitized=True,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def tag_trusted(
        content: str,
        level: ProvenanceLevel = ProvenanceLevel.TRUSTED_SYSTEM,
        source_uri: str = "kernel",
    ) -> TaintedValue:
        if level == ProvenanceLevel.UNTRUSTED_EXTERNAL:
            raise ValueError("Cannot use tag_trusted with UNTRUSTED_EXTERNAL level")
        return TaintedValue(
            content=str(content or ""),
            provenance=level,
            source_uri=source_uri,
            sanitized=True,
        )

    @staticmethod
    def combine_provenance(items: Iterable[TaintedValue]) -> ProvenanceLevel:
        levels = {item.provenance for item in items}
        if ProvenanceLevel.UNTRUSTED_EXTERNAL in levels:
            return ProvenanceLevel.UNTRUSTED_EXTERNAL
        if ProvenanceLevel.TRUSTED_MASTER in levels:
            return ProvenanceLevel.TRUSTED_MASTER
        return ProvenanceLevel.TRUSTED_SYSTEM

    @classmethod
    def enforce_tool_sink_safety(
        cls,
        tool_name: str,
        inputs: Iterable[TaintedValue],
        master_approved: bool = False,
    ) -> Dict[str, Any]:
        norm_tool = str(tool_name or "").strip().lower()
        effective_prov = cls.combine_provenance(inputs)
        if norm_tool in HIGH_IMPACT_SINKS and effective_prov == ProvenanceLevel.UNTRUSTED_EXTERNAL and not master_approved:
            raise TaintViolationError(
                f"[TAINT-WARDEN-BLOCKED] Rejecting execution of privileged sink '{tool_name}' "
                f"because input provenance is '{effective_prov.value}' without Master approval."
            )
        return {
            "allowed": True,
            "tool_name": tool_name,
            "effective_provenance": effective_prov.value,
            "master_approved": bool(master_approved),
        }
