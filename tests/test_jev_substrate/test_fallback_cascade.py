"""
Unit Tests for Dual-Stage Action Firewall, ActionChainState and Fallback Cascade
"""

import pytest
from core.cognitive_bus.jev_substrate_adapter import (
    TriTierJevAdapter,
    ExecutionTier,
    JevPrimitive,
    TypedJudgementPacket
)
from core.security.dual_stage_action_firewall import (
    DualStageActionFirewall,
    FirewallDecision,
    ActionChainState
)


def test_action_firewall_blocks_protected_files():
    firewall = DualStageActionFirewall()
    
    malicious_action = {
        "action": "MUTATE_FILE",
        "target_file": "D:/Docker/JKAI/.keywork.md",
        "content": "Rewrite the constitution"
    }

    verdict = firewall.inspect_action(malicious_action)
    assert verdict.decision == FirewallDecision.DENY
    assert verdict.stage == "STAGE_4_1_DETERMINISTIC"
    assert any(".keywork.md" in r for r in verdict.reasons)


def test_action_firewall_permits_safe_action():
    firewall = DualStageActionFirewall()

    safe_action = {
        "action": "READ_FILE",
        "target_file": "data/assets/report.csv",
        "content": "Display inventory of school desks"
    }

    verdict = firewall.inspect_action(safe_action)
    assert verdict.decision in (FirewallDecision.PERMIT, FirewallDecision.PERMIT_LOG)
    assert verdict.stage == "STAGE_4_2_SEMANTIC"
    assert verdict.risk_score <= 0.30


def test_action_chain_state_quarantines_multi_step_attacks():
    chain = ActionChainState(window_size=5, decay_factor=0.85, quarantine_threshold=0.45)
    assert chain.quarantined is False

    # Step 1: Minor probe
    chain.record_action({"step": 1}, 0.10)
    assert chain.quarantined is False

    # Step 2: Intermediate probe
    chain.record_action({"step": 2}, 0.30)
    assert chain.quarantined is False

    # Step 3: Suspicious activity
    chain.record_action({"step": 3}, 0.60)
    assert chain.quarantined is True  # Threshold 0.45 exceeded!


def test_dynamic_capability_router_and_gce_circuit_breaker():
    firewall = DualStageActionFirewall()

    # Known capability
    prov, conf, is_gap = firewall.route_capability("Check Mikrotik interface traffic and firewall counters")
    assert prov in firewall.CAPABILITY_PROVIDERS
    assert conf >= 0.85

    # Trigger GCE gap 3 times to test circuit breaker
    firewall.gce_circuit_broken = False
    firewall.gce_fail_count = 0

    for _ in range(3):
        firewall.route_capability("Perform hypothetical quantum teleportation")

    assert firewall.gce_circuit_broken is True


def test_fallback_cascade_tier1_to_tier3():
    # Adapter without API key falls back cleanly
    adapter = TriTierJevAdapter(api_key=None, enable_mock=False)
    
    state = {"mission": "Test Fallback"}
    res = adapter.evaluate_noul(state, "Is this mission safe?")
    
    assert res.execution_tier in (ExecutionTier.TIER_2_LOCAL, ExecutionTier.TIER_3_RULE)
    assert res.confidence >= 0.80
