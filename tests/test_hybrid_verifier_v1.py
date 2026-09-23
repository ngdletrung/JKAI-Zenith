# -*- coding: utf-8 -*-
"""
tests/test_hybrid_verifier_v1.py
Unit tests for [V1] evidence-based non-code confidence scoring.
Validates that _verify_non_code_calibrated no longer awards 0.98
for mere key presence — confidence must reflect actual evidence.
"""

import pytest
from core.verification.hybrid_verifier import HybridVerifier


class TestNonCodeEvidenceConfidence:
    """Test _verify_non_code_calibrated with various result types."""

    def _verify(self, result):
        return HybridVerifier._verify_non_code_calibrated("read_file", {}, result)

    # ── Reject cases ──────────────────────────────────────────────────────────

    def test_none_result_rejected(self):
        ok, msg, conf = self._verify(None)
        assert ok is False
        assert conf == 0.0

    def test_empty_dict_rejected(self):
        ok, msg, conf = self._verify({})
        assert ok is False

    def test_empty_string_rejected(self):
        ok, msg, conf = self._verify("")
        assert ok is False

    def test_error_status_rejected(self):
        ok, msg, conf = self._verify({"status": "error", "msg": "file not found"})
        assert ok is False
        assert conf == 0.0

    def test_exception_field_rejected(self):
        ok, msg, conf = self._verify({"exception": "NullPointerException"})
        assert ok is False

    def test_trivial_filler_string_low_confidence(self):
        """'ok' as standalone result is low evidence — must not be >= 0.80."""
        ok, msg, conf = self._verify("ok")
        # Should be approved with warning (low confidence) or rejected, never >= 0.80
        assert conf < 0.80, f"'ok' filler string should NOT get confidence >= 0.80, got {conf}"

    # ── V1 key regression: the old false-positive ─────────────────────────────

    def test_empty_content_key_not_0_98(self):
        """OLD BUG: {'content': ''} was awarded 0.98 via truthy check. Must not be >= 0.80."""
        ok, msg, conf = self._verify({"content": ""})
        # empty content fails empty container at higher level OR gets low confidence
        assert conf < 0.80, f"Empty content key must NOT get high confidence, got {conf}"

    def test_empty_items_key_not_high_confidence(self):
        """{'items': []} should NOT be treated as substantive evidence."""
        ok, msg, conf = self._verify({"items": []})
        assert conf < 0.80, f"Empty items list must NOT get high confidence, got {conf}"

    def test_single_trivial_value_penalized(self):
        """{'content': 'x'} — trivially short, single key — low confidence."""
        ok, msg, conf = self._verify({"content": "x"})
        assert conf < 0.80

    # ── Approve cases (evidence present) ─────────────────────────────────────

    def test_substantive_content_string_approved(self):
        """content >= 20 chars → confidence >= 0.80."""
        ok, msg, conf = self._verify({"content": "x" * 50, "status": "success"})
        assert ok is True
        assert conf >= 0.80

    def test_non_empty_items_list_approved(self):
        """Non-empty items list is real evidence."""
        ok, msg, conf = self._verify({"items": ["file1.py", "file2.py", "file3.py"]})
        assert ok is True
        assert conf >= 0.80

    def test_non_empty_results_list_approved(self):
        ok, msg, conf = self._verify({"results": [{"id": 1}, {"id": 2}]})
        assert ok is True
        assert conf >= 0.80

    def test_substantive_stdout_approved(self):
        ok, msg, conf = self._verify({"stdout": "Build successful. 42 tests passed.", "status": "success"})
        assert ok is True
        assert conf >= 0.80

    def test_long_string_result_approved(self):
        ok, msg, conf = self._verify("A" * 150)
        assert ok is True
        assert conf >= 0.80

    def test_list_with_items_approved(self):
        ok, msg, conf = self._verify(["a", "b", "c", "d"])
        assert ok is True
        assert conf >= 0.80

    def test_multiple_meaningful_keys_boost(self):
        """3+ meaningful keys → confidence boosted."""
        ok, msg, conf = self._verify({
            "status": "success",
            "output": "done successfully",
            "files_written": 3,
            "duration_ms": 42,
        })
        assert ok is True
        assert conf >= 0.80
