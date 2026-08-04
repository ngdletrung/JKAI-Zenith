"""
JKAI ZENITH — KERNEL CONTRACT: EXECUTION & RECOVERY POLICY (v2.1)
File: core/contracts/execution_contract.py

Canonical owner for ExecutionRequest, ExecutionResult, and RecoveryPolicy budget.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.contracts.identity_contract import IdentityChain, AttemptRecord


@dataclass(frozen=True)
class RecoveryPolicy:
    """
    Giới hạn ngân sách tự phục hồi (Recovery Budget Policy).
    Ngăn chặn autonomous execution chạy lặp vô hạn khi phục hồi từ thất bại.
    """
    max_attempts: int = 3
    max_replans: int = 2
    max_model_changes: int = 2
    max_tool_substitutions: int = 2
    timeout_seconds: float = 300.0


@dataclass(frozen=True)
class ExecutionRequest:
    """Yêu cầu thực thi capability."""
    identity: IdentityChain
    attempt: AttemptRecord
    capability_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class ExecutionResult:
    """Kết quả thực thi capability."""
    identity: IdentityChain
    attempt: AttemptRecord
    executed: bool
    result_data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
