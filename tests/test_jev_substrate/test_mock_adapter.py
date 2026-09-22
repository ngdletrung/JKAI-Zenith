"""
Unit Tests for TriTierJevAdapter & Mock Integration
Ensures 100% deterministic offline compatibility and non-regression.
"""

import pytest
from core.cognitive_bus.jev_substrate_adapter import (
    TriTierJevAdapter,
    StateSanitizer,
    JevPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
    CircuitBreaker,
    AdaptiveLatencyGuard
)


def test_state_sanitizer_removes_secrets_and_pii():
    raw_state = {
        "user_email": "admin@school.edu.vn",
        "user_phone": "0987654321",
        "api_key": "sk-test123456789",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDcSemACt8x4iTMC6Y5nV3iMWqJWW5QgNAWWJURQs",
        "command": "SELECT * FROM assets WHERE department = 'IT'",
        "national_id": "123456789012"
    }

    sanitized = StateSanitizer.sanitize(raw_state)

    assert "[REDACTED_EMAIL]" in sanitized["user_email"]
    assert "[REDACTED_PHONE]" in sanitized["user_phone"]
    assert any(tok in sanitized["authorization"] for tok in ["[REDACTED_JWT]", "[REDACTED_TOKEN]"])
    assert "[REDACTED_ID_NUMBER]" in sanitized["national_id"]
    # Structural domain command preserved
    assert sanitized["command"] == "SELECT * FROM assets WHERE department = 'IT'"


def test_state_fingerprint_deterministic():
    state1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
    state2 = {"a": 1, "c": [3, 2, 1], "b": 2}

    fp1 = StateSanitizer.compute_fingerprint(state1)
    fp2 = StateSanitizer.compute_fingerprint(state2)

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA256 hex


def test_mock_adapter_deterministic_noul_and_choice():
    adapter = TriTierJevAdapter(enable_mock=True)

    state = {"action": "QUERY_ASSET", "payload": "SELECT * FROM school_assets"}
    
    # Evaluate Noul
    q_safe = "Is this database query safe from injection?"
    res_safe = adapter.evaluate_noul(state, q_safe)
    assert res_safe.primitive == JevPrimitive.NOUL
    assert res_safe.confidence >= 0.85
    assert res_safe.result <= 0.05  # Maliciousness prob low

    # Evaluate Choice
    q_route = "Which provider should handle this query?"
    options = ["mariadb", "postgres", "mikrotik_router", "none"]
    res_choice = adapter.evaluate_choice(state, q_route, options)
    assert res_choice.primitive == JevPrimitive.CHOICE
    assert res_choice.result in options
    assert res_choice.confidence >= 0.85


def test_circuit_breaker_exponential_backoff():
    cb = CircuitBreaker(failure_threshold=2, backoff_steps=(1, 2, 5))
    assert cb.is_available() is True

    cb.record_failure()
    assert cb.is_available() is True  # threshold is 2

    cb.record_failure()
    assert cb.is_available() is False  # Now OPEN
    assert cb.state == "OPEN"

    cb.record_success()
    assert cb.is_available() is True
    assert cb.state == "CLOSED"


def test_adaptive_latency_guard_p95():
    guard = AdaptiveLatencyGuard(window_size=50, max_p95_ms=200.0)

    for i in range(10):
        guard.record_latency(100.0 + i * 5)

    assert guard.is_degraded() is False
    assert guard.get_p95() <= 150.0

    # Inject latency spikes
    for _ in range(5):
        guard.record_latency(500.0)

    assert guard.is_degraded() is True
