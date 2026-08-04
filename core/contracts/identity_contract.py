"""
JKAI ZENITH — KERNEL CONTRACT: IDENTITY & ATTEMPT CONTRACTS (v2.1)
File: core/contracts/identity_contract.py

Canonical owner for IdentityChain (8 immutable IDs) and AttemptRecord.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time
import uuid


@dataclass(frozen=True)
class IdentityChain:
    """
    Chuỗi định danh 8 định danh bất biến truyền xuyên suốt runtime tác chiến tự chủ.
    Request -> Mission -> Plan -> Task -> Attempt -> Execution -> Observation -> Verification
    """
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:10]}")
    mission_id: str = field(default_factory=lambda: f"mis_{uuid.uuid4().hex[:10]}")
    plan_id: str = field(default_factory=lambda: f"pln_{uuid.uuid4().hex[:10]}")
    task_id: str = field(default_factory=lambda: f"tsk_{uuid.uuid4().hex[:10]}")
    attempt_id: str = field(default_factory=lambda: f"att_{uuid.uuid4().hex[:10]}")
    execution_id: str = field(default_factory=lambda: f"exe_{uuid.uuid4().hex[:10]}")
    observation_id: str = field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:10]}")
    verification_id: str = field(default_factory=lambda: f"ver_{uuid.uuid4().hex[:10]}")


@dataclass(frozen=True)
class AttemptRecord:
    """
    Biểu thị một lần thử chiến lược thực thi tác chiến.
    Lưu vết từng lần thử (Attempt 1 FAIL, Attempt 2 FAIL, Attempt 3 PASS).
    """
    identity: IdentityChain
    attempt_number: int = 1
    strategy_id: str = "default_strategy"
    parent_attempt_id: Optional[str] = None
    recovery_reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
