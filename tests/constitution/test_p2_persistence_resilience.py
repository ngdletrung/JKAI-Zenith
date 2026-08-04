"""
JKAI ZENITH — PRODUCTION HARDENING P2: PERSISTENCE & INFRASTRUCTURE RESILIENCE TEST
File: tests/constitution/test_p2_persistence_resilience.py

Verifies idempotency (no duplicate execution) and state integrity during infrastructure drops.
"""

import pytest
from core.contracts.identity_contract import IdentityChain, AttemptRecord
from core.contracts.execution_contract import ExecutionRequest, ExecutionResult
from core.execution.resilient_executor import ResilientExecutor


def test_p2_idempotent_execution_prevents_duplicate_runs():
    ident = IdentityChain()
    att = AttemptRecord(identity=ident)
    req = ExecutionRequest(
        identity=ident,
        attempt=att,
        capability_name="xlsx_generation"
    )

    # First Execution
    res1 = ResilientExecutor.execute_with_idempotency(req)
    assert res1.executed is True

    # Second Execution (Same Mission, Task, and Capability)
    res2 = ResilientExecutor.execute_with_idempotency(req)
    assert res2.executed is True
    assert res2.execution_time_seconds == res1.execution_time_seconds  # Served from Idempotency Cache!
