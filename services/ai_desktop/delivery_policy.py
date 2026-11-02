# -*- coding: utf-8 -*-
"""
services/ai_desktop/delivery_policy.py
[DELIVERY / RETRY DISPOSITION - D15]

Ported from agent-desktop (crates/core/src/actions/delivery_semantics.rs;
Apache-2.0 - see NOTICE.md / CREDITS.md). The invariant it preserves: only a
provably undelivered action may be retried automatically. Any action the
provider may have observed - even one that failed after dispatch - is unsafe
to replay, and an action with no delivery evidence at all is unknown rather
than safe by default.

JKAI executor states map as follows:

  NOT_DELIVERED -> SAFE     (pre-dispatch failure; a new lease may retry)
  UNCERTAIN     -> UNSAFE   (provider may have acted)
  PARTIAL       -> UNSAFE   (some steps landed; replay would double-apply)
  DELIVERED_UNVERIFIED / DELIVERED_VERIFIED -> UNSAFE
  anything else -> UNKNOWN
"""

from __future__ import annotations

from typing import Optional

NOT_DELIVERED = "NOT_DELIVERED"
UNCERTAIN = "UNCERTAIN"
PARTIAL = "PARTIAL"
DELIVERED_UNVERIFIED = "DELIVERED_UNVERIFIED"
DELIVERED_VERIFIED = "DELIVERED_VERIFIED"

RETRY_SAFE = "SAFE"
RETRY_UNSAFE = "UNSAFE"
RETRY_UNKNOWN = "UNKNOWN"

_DISPOSITION = {
    NOT_DELIVERED: RETRY_SAFE,
    UNCERTAIN: RETRY_UNSAFE,
    PARTIAL: RETRY_UNSAFE,
    DELIVERED_UNVERIFIED: RETRY_UNSAFE,
    DELIVERED_VERIFIED: RETRY_UNSAFE,
}


class DeliveryPolicyError(ValueError):
    """Raised when a claim pairs a delivery state with a contradicting retry."""


def retry_disposition(delivery_state: Optional[str]) -> str:
    """Automatic-retry safety for a delivery state; unknown states stay UNKNOWN."""
    return _DISPOSITION.get(str(delivery_state or "").upper(), RETRY_UNKNOWN)


def recovery_allowed(delivery_state: Optional[str]) -> bool:
    """A recovery path that re-runs the action is legal only when retry is SAFE."""
    return retry_disposition(delivery_state) == RETRY_SAFE


def assert_consistent_pair(delivery_state: Optional[str], retry: Optional[str]) -> str:
    """Validate a persisted (delivery, retry) pair and return the delivery state.

    Used where a receipt or audit row is deserialized: a row that claims
    DELIVERED + SAFE (or NOT_DELIVERED + UNSAFE) must be rejected instead of
    trusted, exactly as the upstream deserializer did.
    """
    clean_state = str(delivery_state or "").upper()
    clean_retry = str(retry or "").upper()
    expected = retry_disposition(clean_state)
    if expected == RETRY_UNKNOWN or clean_retry != expected:
        raise DeliveryPolicyError(
            f"INCONSISTENT_DELIVERY_PAIR: {delivery_state!r} cannot be retry {retry!r}"
        )
    return clean_state
