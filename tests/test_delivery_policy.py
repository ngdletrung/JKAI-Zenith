# -*- coding: utf-8 -*-
"""
tests/test_delivery_policy.py
[UNIT TESTS FOR THE DELIVERY -> RETRY DISPOSITION PORT]

Only NOT_DELIVERED may be retried automatically; every state where the
provider may have acted is UNSAFE, and missing evidence is UNKNOWN.
"""

import sys
import unittest

sys.path.insert(0, ".")

from services.ai_desktop.delivery_policy import (
    DELIVERED_UNVERIFIED,
    DELIVERED_VERIFIED,
    PARTIAL,
    RETRY_SAFE,
    RETRY_UNKNOWN,
    RETRY_UNSAFE,
    UNCERTAIN,
    DeliveryPolicyError,
    assert_consistent_pair,
    recovery_allowed,
    retry_disposition,
)


class TestRetryDisposition(unittest.TestCase):
    def test_01_only_not_delivered_is_safe_to_retry(self):
        self.assertEqual(retry_disposition("NOT_DELIVERED"), RETRY_SAFE)

    def test_02_provider_may_have_acted_states_are_unsafe(self):
        for state in (UNCERTAIN, PARTIAL, DELIVERED_UNVERIFIED, DELIVERED_VERIFIED):
            self.assertEqual(retry_disposition(state), RETRY_UNSAFE, state)

    def test_03_missing_or_unknown_state_is_unknown(self):
        for state in (None, "", "SOMETHING_ELSE"):
            self.assertEqual(retry_disposition(state), RETRY_UNKNOWN, state)

    def test_04_state_is_normalized_before_lookup(self):
        self.assertEqual(retry_disposition("not_delivered"), RETRY_SAFE)
        self.assertEqual(retry_disposition("partial"), RETRY_UNSAFE)

    def test_05_recovery_requires_safe_retry(self):
        self.assertTrue(recovery_allowed("NOT_DELIVERED"))
        self.assertFalse(recovery_allowed("UNCERTAIN"))
        self.assertFalse(recovery_allowed("PARTIAL"))
        self.assertFalse(recovery_allowed(None))


class TestConsistentPairs(unittest.TestCase):
    def test_06_matching_pairs_are_accepted(self):
        self.assertEqual(
            assert_consistent_pair("NOT_DELIVERED", "SAFE"), "NOT_DELIVERED"
        )
        self.assertEqual(assert_consistent_pair("PARTIAL", "UNSAFE"), "PARTIAL")

    def test_07_contradicting_pairs_are_rejected(self):
        with self.assertRaises(DeliveryPolicyError):
            assert_consistent_pair("DELIVERED_VERIFIED", "SAFE")
        with self.assertRaises(DeliveryPolicyError):
            assert_consistent_pair("NOT_DELIVERED", "UNSAFE")

    def test_08_unknown_states_cannot_assert_a_retry(self):
        with self.assertRaises(DeliveryPolicyError):
            assert_consistent_pair("MYSTERY", "SAFE")


class TestWorkerClaimIntegration(unittest.TestCase):
    def _claim(self, delivery_state):
        from scripts.host_mutation_worker import HostMutationWorker
        from services.ai_desktop.uia_click_executor import UIAClickError

        exc = UIAClickError("X", "detail", delivery_state=delivery_state)
        return HostMutationWorker._claim_from_executor_error(
            exc,
            {
                "status": "BLOCKED",
                "receipt": "CLAIMED_NOT_DELIVERED",
                "claim_state": "CLAIMED_NOT_DELIVERED",
                "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
            },
            "click",
            12345,
            "Line down",
        )

    def test_09_pre_dispatch_claim_is_retry_safe(self):
        self.assertEqual(self._claim("NOT_DELIVERED")["retry_disposition"], RETRY_SAFE)

    def test_10_uncertain_and_partial_claims_are_retry_unsafe(self):
        self.assertEqual(self._claim("UNCERTAIN")["retry_disposition"], RETRY_UNSAFE)
        self.assertEqual(self._claim("PARTIAL")["retry_disposition"], RETRY_UNSAFE)


if __name__ == "__main__":
    unittest.main()
