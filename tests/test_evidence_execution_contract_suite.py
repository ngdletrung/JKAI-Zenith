"""
Evidence Execution Contract (EEC v2.0) — Regression Suite (migrated from v1.0)
=============================================================================
13 vectors covering EEC-1 to EEC-10, migrated to v2.0 API:
  - EvidenceRequirement now uses Proposition (not capability= directly)
  - attach_verification uses verifier_independence_class (not is_independent)
  - audit_completion returns CompletionVerdict (not dict)
  - EvidenceGateVerdict compat aliases still available for legacy verdict comparison
=============================================================================
"""

import hashlib
import time
import pytest
from typing import Dict, Any, Set

from core.os.cognition.evidence_execution_contract import (
    EvidencePolicy,
    EvidenceLevel,
    CapabilityDimension,
    VerificationStatus,
    EvidenceGateVerdict,      # v1.0 compat alias
    CompletionState,
    ClaimRecord,
    ActionRecord,
    ObservationRecord,
    VerificationRecord,
    EvidenceRecord,
    EvidenceRequirement,
    Proposition,
    EvidenceProducingAction,  # v1.0 alias for EvidenceExecutionTrace
    EvidenceGateAuditor,
    EvidenceMetrics,
    VerifierIndependenceClass,
)


# ── Helper: build an EvidenceRequirement from a CapabilityDimension (v1.0 compat) ──
def req(
    cap: CapabilityDimension,
    required_level: EvidenceLevel = EvidenceLevel.E2_VERIFIED,
    acceptance_criteria: str = "",
) -> EvidenceRequirement:
    """Convenience factory matching old v1.0 EvidenceRequirement(capability=...) signature."""
    prop = Proposition(
        proposition_id=cap.value,
        description=acceptance_criteria or cap.value,
        capability_dimension=cap,
        minimum_level=required_level,
    )
    return EvidenceRequirement(
        requirement_id=f"REQ_{cap.value}",
        proposition=prop,
        minimum_level=required_level,
        required_verifier="",
        required_fields=(),
    )


class TestEvidenceExecutionContractSuite:

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: 5-Entity Separation (Claim != Action != Obs != Verify != Ev)
    # ─────────────────────────────────────────────────────────────
    def test_01_action_observation_verification_evidence_separation(self):
        """EEC-1 to EEC-5: Demonstrates that Claim, Action, Obs, Verify, Evidence are distinct entities."""
        epa = EvidenceProducingAction(
            eet_id="EPA-001",
            capability_under_test=CapabilityDimension.TOOL_FILE_ACTUATION,
            test_proposition="Create test artifact and verify byte content",
            expected_observation="File exists with returncode 0",
            requirement=req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED, "Read-back exact match")
        )

        # 1. ClaimRecord
        claim = epa.register_claim("I can create and persist file artifacts")
        assert isinstance(claim, ClaimRecord)
        assert claim.is_supported is False

        # 2. ActionRecord
        act = epa.attach_action("write_file", {"file_path": "probe_01.json", "content": '{"status": "ok"}'})
        assert isinstance(act, ActionRecord)
        assert act.tool_name == "write_file"

        # 3. ObservationRecord
        obs = epa.attach_observation(returncode=0, stdout="Wrote 16 bytes", output_bytes=16, latency_ms=12.5)
        assert isinstance(obs, ObservationRecord)
        assert obs.returncode == 0

        # 4. VerificationRecord — v2.0: is_independent=True → STRONG independence
        expected_hash = hashlib.sha256(b'{"status": "ok"}').hexdigest()
        ver = epa.attach_verification(
            verifier_type="READBACK_EXACT_MATCH",
            passed=True,
            details="Read-back exact match 16 bytes",
            verifier_independence_class=VerifierIndependenceClass.STRONG,
            verification_source="/disk",
            writer_source="/memory",
            sha256_hash=expected_hash
        )
        assert isinstance(ver, VerificationRecord)
        assert ver.verifier_independence_class == VerifierIndependenceClass.STRONG

        # 5. EvidenceRecord
        ev = epa.synthesize_evidence(
            mission_id="m_eec_01",
            task_id="t_eec_01",
            trace_id="tr_eec_01",
            invocation_id="inv_eec_01"
        )
        assert isinstance(ev, EvidenceRecord)
        assert ev.level == EvidenceLevel.E3_INDEPENDENTLY_VERIFIED
        assert epa.status == VerificationStatus.VERIFIED
        assert epa.claim.is_supported is True

    # ─────────────────────────────────────────────────────────────
    # VECTOR 2: NO_EVIDENCE_NO_COMPLETION Enforced (EEC-6)
    # ─────────────────────────────────────────────────────────────
    def test_02_no_evidence_no_completion_enforced(self):
        """EEC-6: When policy=REQUIRED, 0 evidence strictly forbids completion and kicks off RECOVERY."""
        epas = []  # 0 actions performed
        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=epas,
            requirements=[req(CapabilityDimension.TOOL_FILE_ACTUATION)]
        )

        assert verdict.verdict == CompletionState.RECOVERY
        assert any("EEC-6" in r for r in verdict.gate_fail_reasons)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Per-Capability Evidence Levels (E2 for File, E3 for Reasoning)
    # ─────────────────────────────────────────────────────────────
    def test_03_conclusion_strength_proportional_to_evidence_levels(self):
        """EEC-7: E2 is sufficient for File Actuation, but E3 is required for Algorithm correctness."""
        # File Actuation with E2 (WEAK independence → E2)
        epa_file = EvidenceProducingAction(
            "EPA-FILE", CapabilityDimension.TOOL_FILE_ACTUATION,
            "TOOL_FILE_ACTUATION",  # must match req() proposition_id = cap.value
            "Expected",
            requirement=req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED)
        )
        epa_file.attach_action("write_file", {})
        epa_file.attach_observation(returncode=0, stdout="Wrote")
        epa_file.attach_verification("READBACK", passed=True, details="Readback matches",
                                     verifier_independence_class=VerifierIndependenceClass.WEAK)
        ev_file = epa_file.synthesize_evidence("m", "t", "tr", "inv")
        assert ev_file.level == EvidenceLevel.E2_VERIFIED

        # Reasoning with E3 required (STRONG independence → E3)
        epa_reason = EvidenceProducingAction(
            "EPA-REASON", CapabilityDimension.REASONING_LOGIC,
            "REASONING_LOGIC",  # must match req() proposition_id = cap.value
            "Expected 42",
            requirement=req(CapabilityDimension.REASONING_LOGIC, EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
        )
        epa_reason.attach_action("python_eval", {"expr": "6*7"})
        epa_reason.attach_observation(returncode=0, stdout="42")
        epa_reason.attach_verification("UNIT_TEST_ASSERT", passed=True, details="Assert 42 == 42",
                                       verifier_independence_class=VerifierIndependenceClass.STRONG,
                                       verification_source="/test_runner", writer_source="/eval_buffer")
        ev_reason = epa_reason.synthesize_evidence("m", "t", "tr", "inv")
        assert ev_reason.level == EvidenceLevel.E3_INDEPENDENTLY_VERIFIED

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_file, epa_reason],
            requirements=[
                req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED),
                req(CapabilityDimension.REASONING_LOGIC, EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
            ]
        )
        assert verdict.verdict == CompletionState.VERIFIED

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Epistemic Humility (EEC-8)
    # ─────────────────────────────────────────────────────────────
    def test_04_epistemic_humility_unverified_marking(self):
        """EEC-8: When only a subset of required capabilities is proven, partial coverage detected."""
        epa_tool = EvidenceProducingAction("EPA-TOOL", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa_tool.attach_action("write_file", {})
        epa_tool.attach_observation(returncode=0, stdout="OK")
        epa_tool.attach_verification("AST", passed=True, details="OK",
                                     verifier_independence_class=VerifierIndependenceClass.STRONG,
                                     verification_source="/disk", writer_source="/mem")
        epa_tool.synthesize_evidence("m", "t", "tr", "inv")

        reqs = [
            req(CapabilityDimension.TOOL_FILE_ACTUATION),
            req(CapabilityDimension.REASONING_LOGIC),
            req(CapabilityDimension.LONG_HORIZON_AUTONOMY)
        ]

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_tool],
            requirements=reqs
        )

        # Partial coverage — not VERIFIED
        assert verdict.verdict in (CompletionState.LOW_CONFIDENCE, CompletionState.RECOVERY)
        assert verdict.evidence_coverage < 1.0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: Evidence Relevance Rejection (EEC-9)
    # ─────────────────────────────────────────────────────────────
    def test_05_evidence_relevance_rejection(self):
        """EEC-9: Evidence for File Actuation cannot be used to prove Reasoning capability."""
        epa_file = EvidenceProducingAction("EPA-FILE", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa_file.attach_action("write_file", {})
        epa_file.attach_observation(returncode=0, stdout="OK")
        epa_file.attach_verification("SHA", passed=True, details="OK",
                                     verifier_independence_class=VerifierIndependenceClass.STRONG,
                                     verification_source="/disk", writer_source="/mem")
        epa_file.synthesize_evidence("m", "t", "tr", "inv")

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_file],
            target_capability=CapabilityDimension.REASONING_LOGIC  # Mismatch!
        )

        assert verdict.verdict in (CompletionState.RECOVERY, CompletionState.ABSTAIN)
        assert any("EEC-9" in r for r in verdict.gate_fail_reasons)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 6: Evidence Provenance 8-Link Lineage (EEC-10)
    # ─────────────────────────────────────────────────────────────
    def test_06_evidence_provenance_8_link_lineage(self):
        """EEC-10: Evidence contains complete traceable provenance lineage."""
        epa = EvidenceProducingAction("EPA-006", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa.attach_action("create_dir", {"path": "/tmp/test"})
        epa.attach_observation(returncode=0, stdout="Created")
        epa.attach_verification("PATH_EXISTS", passed=True, details="Verified directory exists",
                                verifier_independence_class=VerifierIndependenceClass.STRONG,
                                verification_source="/filesystem", writer_source="/memory")
        ev = epa.synthesize_evidence(
            mission_id="m_prov_001",
            task_id="t_prov_001",
            trace_id="tr_prov_001",
            invocation_id="inv_prov_001"
        )

        assert ev.provenance_trace["mission_id"] == "m_prov_001"
        assert ev.provenance_trace["task_id"] == "t_prov_001"
        assert ev.provenance_trace["trace_id"] == "tr_prov_001"
        assert ev.provenance_trace["invocation_id"] == "inv_prov_001"
        assert ev.provenance_trace["epa_id"] == "EPA-006"

    # ─────────────────────────────────────────────────────────────
    # VECTOR 7: VERIFICATION_BLOCKED State Distinct from FAILED
    # ─────────────────────────────────────────────────────────────
    def test_07_verification_blocked_state_distinct_from_failed(self):
        """Action succeeded physically, but no independent verifier exists -> VERIFICATION_BLOCKED."""
        epa_blocked = EvidenceProducingAction("EPA-BLOCKED", CapabilityDimension.EXTERNAL_WEB_RECON, "Test", "Expected")
        epa_blocked.attach_action("http_get", {"url": "https://internal.test"})
        epa_blocked.attach_observation(returncode=0, stdout="HTTP 200 OK")
        # No verification attached
        ev = epa_blocked.synthesize_evidence("m", "t", "tr", "inv")

        assert epa_blocked.status == VerificationStatus.VERIFICATION_BLOCKED
        assert ev.level == EvidenceLevel.E1_OBSERVED

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_blocked],
            requirements=[req(CapabilityDimension.EXTERNAL_WEB_RECON)]
        )
        assert verdict.verdict == CompletionState.VERIFICATION_BLOCKED

    # ─────────────────────────────────────────────────────────────
    # VECTOR 8: Evidence Efficiency, Coverage, and UCR Metrics
    # ─────────────────────────────────────────────────────────────
    def test_08_evidence_efficiency_coverage_and_ucr_metrics(self):
        """Calculates EE, EC, and UCR post-Evidence Gate evaluation."""
        # test_proposition must match req() proposition_id = cap.value for EC tracking
        epa_1 = EvidenceProducingAction("EPA-1", CapabilityDimension.TOOL_FILE_ACTUATION,
                                        "TOOL_FILE_ACTUATION", "Expected")
        epa_1.register_claim("I can write files")
        epa_1.attach_action("write", {})
        epa_1.attach_observation(0, "OK")
        epa_1.attach_verification("V", True, "OK",
                                  verifier_independence_class=VerifierIndependenceClass.WEAK)
        epa_1.synthesize_evidence("m", "t", "tr", "inv")

        # 1 Unsupported Claim (no action or failed verification)
        epa_2 = EvidenceProducingAction("EPA-2", CapabilityDimension.REASONING_LOGIC, "REASONING_LOGIC", "Expected")
        epa_2.register_claim("I am superhuman at reasoning")

        reqs = [
            req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED),
            req(CapabilityDimension.REASONING_LOGIC, EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
        ]
        metrics = EvidenceGateAuditor.calculate_metrics(
            eets=[epa_1, epa_2],
            requirements=reqs
        )

        assert metrics.total_actions == 1
        assert metrics.verified_evidence_count == 1
        assert metrics.unsupported_claim_count == 1
        assert metrics.evidence_efficiency == 1.0   # 1 verified / 1 action
        assert metrics.evidence_coverage == 0.5     # 1 proposition / 2 required propositions
        assert metrics.ucr_s == 0.5                 # 1 unsupported / 2 total claims

    # ─────────────────────────────────────────────────────────────
    # VECTOR 9: Recovery Benchmark (Runtime Fault -> Replan -> Success)
    # ─────────────────────────────────────────────────────────────
    def test_09_recovery_benchmark_runtime_injected_fault_triggers_replan(self):
        """Runtime generates error -> replans to alternate tool -> Verified success."""
        # Attempt 1: Failed
        epa_attempt1 = EvidenceProducingAction("EPA-REC-1", CapabilityDimension.ADAPTIVE_RECOVERY, "ADAPTIVE_RECOVERY", "Expected")
        epa_attempt1.attach_action("legacy_tool", {})
        epa_attempt1.attach_observation(returncode=1, stdout="", stderr="ModuleNotFoundError: legacy_tool")
        ev_1 = epa_attempt1.synthesize_evidence("m", "t", "tr", "inv")
        assert epa_attempt1.status == VerificationStatus.FAILED

        # Replan Attempt 2: Alternative tool
        epa_attempt2 = EvidenceProducingAction("EPA-REC-2", CapabilityDimension.ADAPTIVE_RECOVERY, "ADAPTIVE_RECOVERY", "Expected")
        epa_attempt2.attach_action("builtin_fallback_tool", {})
        epa_attempt2.attach_observation(returncode=0, stdout="Processed successfully via fallback")
        epa_attempt2.attach_verification("RESULT_AUDIT", True, "Output verified",
                                         verifier_independence_class=VerifierIndependenceClass.STRONG,
                                         verification_source="/audit_log", writer_source="/tool_buffer")
        ev_2 = epa_attempt2.synthesize_evidence("m", "t", "tr", "inv")
        assert epa_attempt2.status == VerificationStatus.VERIFIED

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_attempt1, epa_attempt2],
            requirements=[req(CapabilityDimension.ADAPTIVE_RECOVERY, EvidenceLevel.E2_VERIFIED)]
        )
        assert verdict.verdict == CompletionState.VERIFIED

    # ─────────────────────────────────────────────────────────────
    # VECTOR 10: Full Self-Proving Matrix End-to-End
    # ─────────────────────────────────────────────────────────────
    def test_10_full_self_proving_benchmark_end_to_end(self):
        """Simulates full 3-dimension Self-Proving benchmark with real Evidence Gate termination."""
        # 1. Reasoning (E3 required)
        epa_r = EvidenceProducingAction("EPA-R", CapabilityDimension.REASONING_LOGIC, "REASONING_LOGIC", "Expected 42")
        epa_r.register_claim("Can solve arithmetic")
        epa_r.attach_action("python_eval", {"expr": "6*7"})
        epa_r.attach_observation(0, "42")
        epa_r.attach_verification("DETERMINISTIC_ASSERT", True, "42 == 42",
                                   verifier_independence_class=VerifierIndependenceClass.STRONG,
                                   verification_source="/test_runner", writer_source="/eval")
        epa_r.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_1")

        # 2. File Actuation (E2 required)
        epa_f = EvidenceProducingAction("EPA-F", CapabilityDimension.TOOL_FILE_ACTUATION, "TOOL_FILE_ACTUATION", "Exact match")
        epa_f.register_claim("Can manipulate files")
        epa_f.attach_action("write_file", {"path": "test.txt", "data": "JKAI"})
        epa_f.attach_observation(0, "Wrote 4 bytes")
        epa_f.attach_verification("READBACK_SHA256", True, "Match",
                                   verifier_independence_class=VerifierIndependenceClass.WEAK)
        epa_f.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_2")

        # 3. Adaptive Recovery (E2 required)
        epa_rec = EvidenceProducingAction("EPA-REC", CapabilityDimension.ADAPTIVE_RECOVERY, "ADAPTIVE_RECOVERY", "Recovery success")
        epa_rec.register_claim("Can recover from faults")
        epa_rec.attach_action("fallback_executor", {})
        epa_rec.attach_observation(0, "Recovered from prior error")
        epa_rec.attach_verification("RECOVERY_CHECK", True, "Recovered",
                                    verifier_independence_class=VerifierIndependenceClass.WEAK)
        epa_rec.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_3")

        reqs = [
            req(CapabilityDimension.REASONING_LOGIC, EvidenceLevel.E3_INDEPENDENTLY_VERIFIED),
            req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED),
            req(CapabilityDimension.ADAPTIVE_RECOVERY, EvidenceLevel.E2_VERIFIED)
        ]

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_r, epa_f, epa_rec],
            requirements=reqs
        )

        assert verdict.verdict == CompletionState.VERIFIED
        assert verdict.evidence_coverage == 1.0
        assert verdict.metrics.evidence_efficiency == 1.0
        assert verdict.metrics.ucr_s == 0.0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 11: Adversarial Self-Claim Without EPA is Blocked
    # ─────────────────────────────────────────────────────────────
    def test_11_adversarial_self_claim_without_epa_is_blocked(self):
        """Model produces text claim but 0 EPAs -> Claim is unsupported, Evidence Gate strictly blocks."""
        epa_claim_only = EvidenceProducingAction(
            "EPA-ADV-1", CapabilityDimension.TOOL_FILE_ACTUATION, "Claim test", "Expected",
            requirement=req(CapabilityDimension.TOOL_FILE_ACTUATION)
        )
        claim = epa_claim_only.register_claim("Tôi có thể thao tác file tuyệt vời mà không cần chạy gì cả.")
        # No action attached!
        ev = epa_claim_only.synthesize_evidence("m_adv", "t_adv", "tr_adv", "inv_adv")
        assert ev is None
        assert epa_claim_only.status == VerificationStatus.UNVERIFIED
        assert claim.is_supported is False

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_claim_only],
            requirements=[req(CapabilityDimension.TOOL_FILE_ACTUATION)]
        )
        assert verdict.verdict == CompletionState.RECOVERY
        assert verdict.metrics.ucr_s == 1.0
        assert verdict.metrics.verified_evidence_count == 0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 12: Fake Tool Success Rejected by Execution Truth
    # ─────────────────────────────────────────────────────────────
    def test_12_fake_tool_success_rejected_by_execution_truth(self):
        """Tool returns 0/success, but verification reveals corrupt data -> EVIDENCE_INVALID."""
        epa_fake = EvidenceProducingAction(
            "EPA-FAKE", CapabilityDimension.TOOL_FILE_ACTUATION, "Corrupt test", "Exact JSON match",
            requirement=req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED)
        )
        epa_fake.attach_action("write_file", {"path": "corrupt.json", "content": '{"valid": true}'})
        epa_fake.attach_observation(returncode=0, stdout="Wrote bytes successfully")  # Tool says success!

        # But verification discovers payload mismatch / corruption!
        epa_fake.attach_verification(
            verifier_type="READBACK_SHA256",
            passed=False,
            details="Hash mismatch: expected a1b2c3 but found empty/corrupted buffer",
            verifier_independence_class=VerifierIndependenceClass.STRONG,
            verification_source="/disk", writer_source="/memory"
        )
        ev = epa_fake.synthesize_evidence("m_fake", "t_fake", "tr_fake", "inv_fake")
        # v2.0: verifier FAIL → EVIDENCE_INVALID (stronger signal than v1.0 FAILED)
        assert epa_fake.status == VerificationStatus.EVIDENCE_INVALID
        assert ev.level == EvidenceLevel.E1_OBSERVED  # Only observed, NOT verified

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_fake],
            requirements=[req(CapabilityDimension.TOOL_FILE_ACTUATION, EvidenceLevel.E2_VERIFIED)]
        )
        # v2.0: EVIDENCE_INVALID (more precise than RECOVERY)
        assert verdict.verdict in (CompletionState.EVIDENCE_INVALID, CompletionState.RECOVERY)
        assert verdict.metrics.verified_evidence_count == 0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 13: Belief Revision Telemetry in Adaptive Recovery
    # ─────────────────────────────────────────────────────────────
    def test_13_belief_revision_telemetry_in_recovery_loop(self):
        """Failure -> Observation -> Belief Revised -> Strategy Revised -> Action -> Verified."""
        from core.os.cognition.adaptive_solver.models import ExpectedVsActual, StrategyConfidenceTracker, StrategyDecision

        # Step 1: Initial belief divergence & strategy decay
        tracker = StrategyConfidenceTracker(initial_confidence=0.95)
        eva = ExpectedVsActual(
            expected_state="Tool A is available and operational",
            observed_reality="Execution failed with 404 resource not found",
            is_divergent=True,
            divergence_reason="Execution failed with 404 resource not found"
        )
        assert eva.is_divergent is True

        # Anomaly recorded -> confidence decays -> strategy invalidated
        tracker.record_anomaly("Tool A failed with 404", penalty=0.60)
        assert tracker.is_invalidated is True
        new_strategy = StrategyDecision.PIVOT_STRATEGY

        # Step 2: EPA with recovery
        epa_rec = EvidenceProducingAction(
            "EPA-REC-TRACE", CapabilityDimension.ADAPTIVE_RECOVERY, "ADAPTIVE_RECOVERY", "Success",
            requirement=req(CapabilityDimension.ADAPTIVE_RECOVERY, EvidenceLevel.E2_VERIFIED)
        )
        epa_rec.attach_action("tool_b_fallback", {})
        epa_rec.attach_observation(0, "Tool B completed successfully")
        epa_rec.attach_verification("VERIFY_TOOL_B", True, "Pass",
                                    verifier_independence_class=VerifierIndependenceClass.STRONG,
                                    verification_source="/audit", writer_source="/tool_cache")
        epa_rec.synthesize_evidence("m_rec", "t_rec", "tr_rec", "inv_rec")
        assert epa_rec.status == VerificationStatus.VERIFIED

        verdict = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            eets=[epa_rec],
            requirements=[req(CapabilityDimension.ADAPTIVE_RECOVERY)]
        )
        assert verdict.verdict == CompletionState.VERIFIED
        assert new_strategy == StrategyDecision.PIVOT_STRATEGY
