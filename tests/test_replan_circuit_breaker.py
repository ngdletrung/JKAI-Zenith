# -*- coding: utf-8 -*-
"""
tests/test_replan_circuit_breaker.py
Unit tests for P0-1: REPLAN Circuit Breaker (Two-Tier Fail-Fast Protection)
"""

import pytest
from core.kernel.replan_circuit_breaker import (
    ReplanCircuitBreaker,
    ErrorSignature,
    BreakerDecision
)


class TestReplanCircuitBreaker:
    def setup_method(self):
        self.breaker = ReplanCircuitBreaker(window_sec=60)

    def test_classify_infra_json_error(self):
        err = "Error calling executor: Expecting value: line 1 column 1 (char 0)"
        sig = self.breaker.classify(err, tool="WRITE_TO_FILE")
        assert sig.kind == "INFRA"
        assert sig.code == "JSON_EMPTY_OR_CONN_REFUSED"
        assert sig.tool == "WRITE_TO_FILE"

    def test_classify_policy_denial(self):
        err = "HARD-DENY: PolicySnapshot forbids file deletion"
        sig = self.breaker.classify(err, tool="delete_file")
        assert sig.kind == "POLICY"
        assert sig.code == "POLICY_HARD_DENIAL"

    def test_classify_syntax_error(self):
        err = "SyntaxError: invalid syntax (delta = b**2 - 4ac)"
        sig = self.breaker.classify(err, tool="write_to_file")
        assert sig.kind == "LOGIC"
        assert sig.code == "SYNTAX_OR_NAME_ERROR"

    def test_infra_failure_trips_breaker_after_two_attempts(self):
        """Invariant: Infra errors must FAIL-FAST on the 2nd attempt, stopping replan storm."""
        task_id = "test_task_infra"
        sig = self.breaker.classify("Expecting value: line 1 column 1", tool="write_to_file")

        # Attempt 1 -> ALLOW_RETRY
        dec1 = self.breaker.record(task_id, sig)
        assert dec1.action == "ALLOW_RETRY"
        assert dec1.error_count == 1
        tripped, _ = self.breaker.is_tripped(task_id)
        assert tripped is False

        # Attempt 2 -> FAIL_FAST
        dec2 = self.breaker.record(task_id, sig)
        assert dec2.action == "FAIL_FAST"
        assert dec2.error_count == 2
        assert "CIRCUIT BREAKER TRIPPED [INFRA]" in dec2.reason

        # Breaker state check
        tripped, dec = self.breaker.is_tripped(task_id)
        assert tripped is True
        assert dec.action == "FAIL_FAST"

    def test_policy_denial_trips_immediately(self):
        """Invariant: Policy denial trips FAIL-FAST on first encounter."""
        task_id = "test_task_policy"
        sig = self.breaker.classify("HARD BOUNDARY DENIAL", tool="python_execute")

        dec = self.breaker.record(task_id, sig)
        assert dec.action == "FAIL_FAST"
        assert dec.error_count == 1
        tripped, _ = self.breaker.is_tripped(task_id)
        assert tripped is True

    def test_logic_error_escalates_after_three_attempts(self):
        """Invariant: Logic error allows 2 retries, escalates on 3rd."""
        task_id = "test_task_logic"
        sig = self.breaker.classify("SyntaxError: bad syntax", tool="write_to_file")

        dec1 = self.breaker.record(task_id, sig)
        assert dec1.action == "ALLOW_RETRY"

        dec2 = self.breaker.record(task_id, sig)
        assert dec2.action == "ALLOW_RETRY"

        dec3 = self.breaker.record(task_id, sig)
        assert dec3.action == "ESCALATE"
        assert "CIRCUIT BREAKER TRIPPED [LOGIC]" in dec3.reason

    def test_reset_clears_task_state(self):
        task_id = "test_task_reset"
        sig = self.breaker.classify("ConnectionRefusedError", tool="search_web")
        self.breaker.record(task_id, sig)
        self.breaker.record(task_id, sig)
        tripped, _ = self.breaker.is_tripped(task_id)
        assert tripped is True

        self.breaker.reset(task_id)
        tripped_after, _ = self.breaker.is_tripped(task_id)
        assert tripped_after is False
