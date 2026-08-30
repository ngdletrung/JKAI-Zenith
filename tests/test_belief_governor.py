# -*- coding: utf-8 -*-
"""
Unit test suite for DEMS BeliefGovernor & EvidenceDebt (Phase 5.6-D).
Verifies:
  - I-DEMS-03: Claim != Belief
  - I-DEMS-04: No Silent Resolution (Contested stays CONTESTED)
  - I-DEMS-05: UNKNOWN is a valid belief state and generates EvidenceDebt
  - EvidenceDebt generation & Next Best Action recommendations
"""

import os
import shutil
import tempfile
import pytest
from core.governor.claim_ledger import ClaimLedger, ClaimScope, ClaimStatus
from core.governor.belief_governor import BeliefGovernor
from core.governor.evidence_debt import EvidenceDebt


@pytest.fixture
def temp_governor():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_belief_claims.db")
    ledger = ClaimLedger(db_path=db_path)
    gov = BeliefGovernor(ledger=ledger)
    yield gov, ledger
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_unknown_belief_generation(temp_governor):
    gov, ledger = temp_governor
    # No claims exist yet
    belief = gov.resolve_belief(
        subject="redis_service",
        predicate="port",
        scope=ClaimScope.RUNTIME,
        mission_id="m_test_1"
    )

    assert belief.status == ClaimStatus.UNKNOWN
    assert belief.effective_object is None
    assert belief.confidence == 0.0
    assert belief.evidence_debt is not None
    assert belief.evidence_debt.has_debt is True
    assert "redis_service.port" in belief.evidence_debt.missing_dimensions

    next_act = belief.evidence_debt.recommend_next_action()
    assert next_act is not None
    assert next_act["action"] == "RECON_PROBE"


def test_active_belief_with_evidence_debt_on_missing_dimension(temp_governor):
    gov, ledger = temp_governor

    # Register port claim
    ledger.register_claim(
        subject="service_alpha",
        predicate="port",
        object_val="8000",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_001",
        authority_level=4
    )

    # Resolve belief with required dimension "status" which is missing
    belief = gov.resolve_belief(
        subject="service_alpha",
        predicate="port",
        scope=ClaimScope.RUNTIME,
        required_dimensions=["status"],
        mission_id="m_test_2"
    )

    assert belief.status == ClaimStatus.ACTIVE
    assert belief.effective_object == "8000"
    assert belief.confidence > 0.7
    assert belief.evidence_debt is not None
    assert belief.evidence_debt.has_debt is True
    assert "service_alpha.status" in belief.evidence_debt.missing_dimensions


def test_contested_belief_resolution(temp_governor):
    gov, ledger = temp_governor

    # Add 2 conflicting claims with equal authority (4)
    ledger.register_claim(
        subject="service_beta",
        predicate="port",
        object_val="8080",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_tool1",
        authority_level=4
    )
    ledger.register_claim(
        subject="service_beta",
        predicate="port",
        object_val="9090",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_tool2",
        authority_level=4
    )

    belief = gov.resolve_belief(
        subject="service_beta",
        predicate="port",
        scope=ClaimScope.RUNTIME,
        mission_id="m_test_3"
    )

    assert belief.status == ClaimStatus.CONTESTED
    assert belief.effective_object is None
    assert belief.evidence_debt is not None
    assert len(belief.evidence_debt.contested_claims) == 2

    next_act = belief.evidence_debt.recommend_next_action()
    assert next_act is not None
    assert next_act["action"] == "CROSS_VERIFY"
