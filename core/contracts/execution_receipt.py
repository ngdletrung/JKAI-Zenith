# -*- coding: utf-8 -*-
"""
core/contracts/execution_receipt.py
🏛️ EXECUTION RECEIPT & COMPLETION CERTIFICATE CONTRACTS (P0.3)
Enforces Separation of Powers:
- Executor emits ONLY ExecutionReceipt (Status: EXECUTED). Never COMPLETED.
- CompletionAuthority issues CompletionCertificate (Status: COMPLETED)
  iff (Artifact_Exists AND Schema_Valid AND State_Changed).
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    TIMEOUT = "TIMEOUT"


class CompletionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    ABORTED = "ABORTED"


@dataclass
class ExecutionReceipt:
    """
    Receipt issued by tool executors upon finishing an execution step.
    Executor is strictly forbidden from declaring a mission COMPLETED.
    """
    task_id: str
    tool_name: str
    exit_code: int                                  # 0 = tool ran without crash, NOT mission completion
    status: ExecutionStatus = ExecutionStatus.EXECUTED
    output_artifact_path: Optional[str] = None
    output_artifact_sha256: Optional[str] = None
    output_artifact_size_bytes: Optional[int] = None
    side_effects: List[str] = field(default_factory=list)
    execution_timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    raw_output: Any = None


@dataclass
class CompletionCertificate:
    """
    Certificate issued exclusively by CompletionAuthority.
    The ONLY legal proof in JKAI Zenith that a mission is truly COMPLETED.
    """
    certificate_id: str = field(default_factory=lambda: f"cert-{uuid.uuid4().hex[:12]}")
    mission_id: str = "default"
    status: CompletionStatus = CompletionStatus.FAILED_VERIFICATION
    artifact_exists: bool = False
    schema_valid: bool = False
    state_changed: bool = False
    sha256_checksum: str = ""
    evidence_count: int = 0
    issued_at: float = field(default_factory=time.time)
    issued_by: str = "CompletionAuthority"
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
