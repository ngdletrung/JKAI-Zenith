"""
CONSTITUTION TEST 10: IDENTITY CHAIN TRACEABILITY
File: tests/constitution/test_identity_chain.py
"""

import pytest
from core.contracts.cognitive_contract import IdentityChain
from core.contracts.verification_contract import VerificationResult, FailureClassification


def test_identity_chain_structure_and_attempt_record():
    ident = IdentityChain()
    assert ident.request_id.startswith("req_")
    assert ident.mission_id.startswith("mis_")
    assert ident.plan_id.startswith("pln_")
    assert ident.task_id.startswith("tsk_")
    assert ident.attempt_id.startswith("att_")
    assert ident.execution_id.startswith("exe_")
    assert ident.observation_id.startswith("obs_")
    assert ident.verification_id.startswith("ver_")


def test_aborted_terminal_state():
    res = VerificationResult(
        passed=False,
        failure_classification=FailureClassification.POLICY_FAILURE
    )
    assert res.failure_classification == FailureClassification.POLICY_FAILURE
