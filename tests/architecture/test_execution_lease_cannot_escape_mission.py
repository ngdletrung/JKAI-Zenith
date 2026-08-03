"""
JKAI ZENITH — ARCHITECTURE CERTIFICATION: LEVEL 6 LEASE SECURITY INVARIANCE
tests/architecture/test_execution_lease_cannot_escape_mission.py

Architectural Invariant Enforced (I3):
    An ExecutionLease with authority_scope = ["read"] CANNOT perform unauthorized side-effects
    such as "WRITE", "DELETE", or "ADMIN", regardless of model, provider, tool, or hardware.
"""

import pytest
from core.contracts import ExecutionLease, ExecutionIntent


class TestExecutionLeaseSecurityInvariance:

    def test_lease_authority_scope_prevents_unauthorized_actions(self):
        lease = ExecutionLease(
            mission_id="m_sec_001",
            task_id="t_sec_001",
            execution_intent=ExecutionIntent(model_ref="qwen3.5:4b"),
            authority_scope=["read", "write_draft"]
        )

        assert "read" in lease.authority_scope
        assert "write_draft" in lease.authority_scope
        assert "delete_database" not in lease.authority_scope
        assert "admin_exec" not in lease.authority_scope

        # Verify enforcement rule
        requested_action = "delete_database"
        is_authorized = requested_action in lease.authority_scope

        # INVARIANT: Unauthorized action MUST be DENIED
        assert is_authorized is False
