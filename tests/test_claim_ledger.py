# -*- coding: utf-8 -*-
"""
Unit test suite for DEMS ClaimLedger (Phase 5.6-C).
Verifies:
  - I-DEMS-02: Evidence Provenance
  - I-DEMS-03: Claim != Belief
  - I-DEMS-04: No Silent Resolution (Conflict between equal authority -> CONTESTED)
  - Supersession when higher authority arrives
"""

import os
import shutil
import tempfile
import pytest
from core.governor.claim_ledger import ClaimLedger, ClaimScope, ClaimStatus, EvidenceItem


@pytest.fixture
def temp_ledger():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_claims.db")
    ledger = ClaimLedger(db_path=db_path)
    yield ledger
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_claim_registration_and_provenance(temp_ledger):
    ev = EvidenceItem(
        evidence_id="ev_001",
        trace_id="tr_001",
        source_type="file_read",
        provenance="config/app.json",
        scope=ClaimScope.STATIC_CONFIG,
        timestamp=1000.0,
        verification_hash="hash123",
        payload={"port": 8080}
    )
    temp_ledger.add_evidence(ev)

    claim = temp_ledger.register_claim(
        subject="gateway_service",
        predicate="port",
        object_val="8080",
        scope=ClaimScope.STATIC_CONFIG,
        evidence_id="ev_001",
        authority_level=2
    )

    assert claim.status == ClaimStatus.ACTIVE
    assert claim.subject == "gateway_service"
    assert claim.predicate == "port"
    assert claim.object_val == "8080"
    assert "ev_001" in claim.evidence_refs


def test_conflict_resolution_higher_authority_supersedes(temp_ledger):
    # 1. Config says port 8080 (Authority = 2)
    c1 = temp_ledger.register_claim(
        subject="service_x",
        predicate="port",
        object_val="8080",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_config",
        authority_level=2
    )
    assert c1.status == ClaimStatus.ACTIVE

    # 2. Runtime netstat says port 9000 (Authority = 4)
    c2 = temp_ledger.register_claim(
        subject="service_x",
        predicate="port",
        object_val="9000",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_netstat",
        authority_level=4
    )

    # c2 must become ACTIVE, c1 must become SUPERSEDED
    assert c2.status == ClaimStatus.ACTIVE

    claims = temp_ledger.get_claims_by_predicate("service_x", "port", ClaimScope.RUNTIME)
    c1_updated = [c for c in claims if c.claim_id == c1.claim_id][0]
    assert c1_updated.status == ClaimStatus.SUPERSEDED
    assert c1_updated.superseded_by == c2.claim_id


def test_conflict_resolution_equal_authority_is_contested(temp_ledger):
    # Tool A (Authority = 4) says port 8080
    c1 = temp_ledger.register_claim(
        subject="service_x",
        predicate="port",
        object_val="8080",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_tool_a",
        authority_level=4
    )

    # Tool B (Authority = 4) says port 9000
    c2 = temp_ledger.register_claim(
        subject="service_x",
        predicate="port",
        object_val="9000",
        scope=ClaimScope.RUNTIME,
        evidence_id="ev_tool_b",
        authority_level=4
    )

    # I-DEMS-04: No silent resolution! Both must become CONTESTED
    claims = temp_ledger.get_claims_by_predicate("service_x", "port", ClaimScope.RUNTIME)
    assert len(claims) == 2
    assert all(c.status == ClaimStatus.CONTESTED for c in claims)
