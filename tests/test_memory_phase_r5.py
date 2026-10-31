"""
Consolidated Unit Tests for Phase R-Memory-5: Production Boundary, Process Lock & Resolved Ledger
File: tests/test_memory_phase_r5.py
Governed by Turn 477, Turn 479 & Turn 481 Consensus:
- 10 Mandatory Unit Tests:
  1. test_default_production_path_rejects_string_verdict
  2. test_missing_execution_ledger_blocks_verified_experience
  3. test_typed_receipt_payload_matches_ledger
  4. test_cross_process_append_serialization
  5. test_partial_line_quarantine_artifact
  6. test_count_scoped_records_before_retrieval
  7. test_reading_unknown_bank_has_no_write_side_effect
  8. test_conflicting_evidence_namespace_fields_rejected
  9. test_store_reflect_receives_bounded_records_only
  10. test_execution_receipt_artifact_hash_binding
"""

from tests.test_memory_phase_r5_cluster1_2 import (
    test_default_production_path_rejects_string_verdict,
    test_missing_execution_ledger_blocks_verified_experience,
    test_typed_receipt_payload_matches_ledger,
    test_conflicting_evidence_namespace_fields_rejected,
    test_execution_receipt_artifact_hash_binding
)

from tests.test_memory_phase_r5_cluster3_4 import (
    test_cross_process_append_serialization,
    test_partial_line_quarantine_artifact,
    test_count_scoped_records_before_retrieval,
    test_reading_unknown_bank_has_no_write_side_effect,
    test_store_reflect_receives_bounded_records_only
)
