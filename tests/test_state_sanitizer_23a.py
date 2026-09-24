# -*- coding: utf-8 -*-
"""
tests/test_state_sanitizer_23a.py
Test Suite for 2.3a StateSanitizer Sovereign Component

Verifies:
1. Fix a: MAX_STATE_BYTES = 65536 hard cap (truncation prevents memory exhaustion).
2. Fix b: state_hash = hash(sanitized) (integrity derived from sanitized state).
3. Stripping of credentials, PII (CCCD, phone, email, private keys, passwords).
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.sanitizer.state_sanitizer import StateSanitizer


def test_fix_a_max_state_bytes_hard_cap():
    """Fix a: Ensure canonical JSON string never exceeds 65536 bytes."""
    huge_data = {"key": "x" * 100000}
    canonical = StateSanitizer.canonical_json(huge_data)
    encoded = canonical.encode("utf-8")
    assert len(encoded) <= StateSanitizer.MAX_STATE_BYTES
    assert StateSanitizer.MAX_STATE_BYTES == 65536


def test_fix_b_fingerprint_derived_from_sanitized_state():
    """Fix b: Ensure fingerprint changes if raw data changes, but stays same if only secret changes to same redacted."""
    raw_state_1 = {"password": "SuperSecretPassword123!", "user": "master"}
    raw_state_2 = {"password": "DifferentSecretPassword456!", "user": "master"}
    
    # Since 'password' key is redacted to '[REDACTED_SECRET_FIELD]', both sanitized states become identical
    fp1 = StateSanitizer.compute_fingerprint(raw_state_1)
    fp2 = StateSanitizer.compute_fingerprint(raw_state_2)
    assert fp1 == fp2
    assert len(fp1) == 64


def test_sanitizer_strips_pii_and_secrets():
    """Verify Layer 1: PII and secret patterns are cleansed."""
    data = {
        "user_phone": "0912345678",
        "user_email": "admin@example.com",
        "user_cccd": "012345678901",
        "auth": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis"
    }
    sanitized = StateSanitizer.sanitize(data)
    assert "[REDACTED_PHONE]" in sanitized["user_phone"]
    assert "[REDACTED_EMAIL]" in sanitized["user_email"]
    assert "[REDACTED_ID_NUMBER]" in sanitized["user_cccd"]
    assert "[REDACTED_TOKEN]" in sanitized["auth"] or "[REDACTED_JWT]" in sanitized["auth"]
