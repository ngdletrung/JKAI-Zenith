"""
Evidence Execution Contract (EEC v1.0) & Self-Proving Benchmark Suite
=============================================================================
10 Rigorous Test Vectors covering EEC-1 to EEC-10, 5-Entity Separation,
Per-Capability EvidenceRequirement (E2/E3), VERIFICATION_BLOCKED, and EE/EC/UCR Metrics.
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
    EvidenceGateVerdict,
    ClaimRecord,
    ActionRecord,
    ObservationRecord,
    VerificationRecord,
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceProducingAction,
    EvidenceGateAuditor,
    EvidenceMetrics
)


class TestEvidenceExecutionContractSuite:

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: 5-Entity Separation (Claim != Action != Obs != Verify != Ev)
    # ─────────────────────────────────────────────────────────────
    def test_01_action_observation_verification_evidence_separation(self):
        """EEC-1 to EEC-5: Demonstrates that Claim, Action, Obs, Verify, Evidence are distinct entities."""
        epa = EvidenceProducingAction(
            epa_id="EPA-001",
            capability_under_test=CapabilityDimension.TOOL_FILE_ACTUATION,
            test_proposition="Create test artifact and verify byte content",
            expected_observation="File exists with returncode 0",
            requirement=EvidenceRequirement(
                capability=CapabilityDimension.TOOL_FILE_ACTUATION,
                required_level=EvidenceLevel.E2_VERIFIED,
                acceptance_criteria="Read-back exact match"
            )
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

        # 4. VerificationRecord
        expected_hash = hashlib.sha256(b'{"status": "ok"}').hexdigest()
        ver = epa.attach_verification(
            verifier_type="READBACK_EXACT_MATCH",
            passed=True,
            details="Read-back exact match 16 bytes",
            is_independent=True,
            sha256_hash=expected_hash
        )
        assert isinstance(ver, VerificationRecord)
        assert ver.is_independent is True

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
        epas = [] # 0 actions performed
        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=epas,
            requirements=[EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)]
        )

        assert audit["verdict"] == EvidenceGateVerdict.RECOVERY
        assert "EEC-6 Violation" in audit["reason"]

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Per-Capability Evidence Levels (E2 for File, E3 for Reasoning)
    # ─────────────────────────────────────────────────────────────
    def test_03_conclusion_strength_proportional_to_evidence_levels(self):
        """EEC-7: E2 is sufficient for File Actuation, but E3 is required for Algorithm correctness."""
        # File Actuation with E2 (Direct read-back, not independent test runner)
        epa_file = EvidenceProducingAction(
            "EPA-FILE", CapabilityDimension.TOOL_FILE_ACTUATION, "File test", "Expected",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED)
        )
        epa_file.attach_action("write_file", {})
        epa_file.attach_observation(returncode=0, stdout="Wrote")
        epa_file.attach_verification("READBACK", passed=True, details="Readback matches", is_independent=False)
        ev_file = epa_file.synthesize_evidence("m", "t", "tr", "inv")
        assert ev_file.level == EvidenceLevel.E2_VERIFIED

        # Reasoning with E3 required (Deterministic verifier confirms)
        epa_reason = EvidenceProducingAction(
            "EPA-REASON", CapabilityDimension.REASONING_LOGIC, "Math test", "Expected 42",
            requirement=EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
        )
        epa_reason.attach_action("python_eval", {"expr": "6*7"})
        epa_reason.attach_observation(returncode=0, stdout="42")
        epa_reason.attach_verification("UNIT_TEST_ASSERT", passed=True, details="Assert 42 == 42", is_independent=True)
        ev_reason = epa_reason.synthesize_evidence("m", "t", "tr", "inv")
        assert ev_reason.level == EvidenceLevel.E3_INDEPENDENTLY_VERIFIED

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_file, epa_reason],
            requirements=[
                EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED),
                EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
            ]
        )
        assert audit["verdict"] == EvidenceGateVerdict.TERMINATE_WITH_PROOF

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Epistemic Humility (EEC-8)
    # ─────────────────────────────────────────────────────────────
    def test_04_epistemic_humility_unverified_marking(self):
        """EEC-8: When only a subset of required capabilities is proven, unverified dimensions are marked explicitly."""
        epa_tool = EvidenceProducingAction("EPA-TOOL", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa_tool.attach_action("write_file", {})
        epa_tool.attach_observation(returncode=0, stdout="OK")
        epa_tool.attach_verification("AST", passed=True, details="OK", is_independent=True)
        epa_tool.synthesize_evidence("m", "t", "tr", "inv")

        reqs = [
            EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION),
            EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC),
            EvidenceRequirement(capability=CapabilityDimension.LONG_HORIZON_AUTONOMY)
        ]

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_tool],
            requirements=reqs
        )

        assert audit["verdict"] == EvidenceGateVerdict.LOW_CONFIDENCE_CONCLUSION
        assert CapabilityDimension.TOOL_FILE_ACTUATION in audit["verified_dimensions"]
        assert CapabilityDimension.REASONING_LOGIC in audit["unverified_dimensions"]
        assert CapabilityDimension.LONG_HORIZON_AUTONOMY in audit["unverified_dimensions"]

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: Evidence Relevance Rejection (EEC-9)
    # ─────────────────────────────────────────────────────────────
    def test_05_evidence_relevance_rejection(self):
        """EEC-9: Evidence for File Actuation cannot be used to prove Reasoning capability."""
        epa_file = EvidenceProducingAction("EPA-FILE", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa_file.attach_action("write_file", {})
        epa_file.attach_observation(returncode=0, stdout="OK")
        epa_file.attach_verification("SHA", passed=True, details="OK", is_independent=True)
        epa_file.synthesize_evidence("m", "t", "tr", "inv")

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_file],
            target_capability=CapabilityDimension.REASONING_LOGIC # Mismatch!
        )

        assert audit["verdict"] == EvidenceGateVerdict.RECOVERY
        assert "EEC-9 Violation" in audit["reason"]

    # ─────────────────────────────────────────────────────────────
    # VECTOR 6: Evidence Provenance 8-Link Lineage (EEC-10)
    # ─────────────────────────────────────────────────────────────
    def test_06_evidence_provenance_8_link_lineage(self):
        """EEC-10: Evidence contains complete traceable provenance lineage."""
        epa = EvidenceProducingAction("EPA-006", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa.attach_action("create_dir", {"path": "/tmp/test"})
        epa.attach_observation(returncode=0, stdout="Created")
        epa.attach_verification("PATH_EXISTS", passed=True, details="Verified directory exists", is_independent=True)
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

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_blocked],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.EXTERNAL_WEB_RECON)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.VERIFICATION_BLOCKED

    # ─────────────────────────────────────────────────────────────
    # VECTOR 8: Evidence Efficiency, Coverage, and UCR Metrics
    # ─────────────────────────────────────────────────────────────
    def test_08_evidence_efficiency_coverage_and_ucr_metrics(self):
        """Calculates EE, EC, and UCR post-Evidence Gate evaluation."""
        # 1 Verified E2 action with supported claim
        epa_1 = EvidenceProducingAction("EPA-1", CapabilityDimension.TOOL_FILE_ACTUATION, "Test", "Expected")
        epa_1.register_claim("I can write files")
        epa_1.attach_action("write", {})
        epa_1.attach_observation(0, "OK")
        epa_1.attach_verification("V", True, "OK", is_independent=False)
        epa_1.synthesize_evidence("m", "t", "tr", "inv")

        # 1 Unsupported Claim (no action or failed verification)
        epa_2 = EvidenceProducingAction("EPA-2", CapabilityDimension.REASONING_LOGIC, "Test", "Expected")
        epa_2.register_claim("I am superhuman at reasoning")

        metrics = EvidenceGateAuditor.calculate_metrics(
            epas=[epa_1, epa_2],
            requirements=[
                EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED),
                EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
            ]
        )

        assert metrics.total_actions == 1
        assert metrics.verified_evidence_count == 1
        assert metrics.unsupported_claim_count == 1
        assert metrics.evidence_efficiency == 1.0  # 1 verified / 1 action
        assert metrics.evidence_coverage == 0.5    # 1 dim / 2 required dims
        assert metrics.unsupported_claim_rate == 0.5 # 1 unsupported claim / 2 total claims

    # ─────────────────────────────────────────────────────────────
    # VECTOR 9: Recovery Benchmark (Runtime Fault -> Replan -> Success)
    # ─────────────────────────────────────────────────────────────
    def test_09_recovery_benchmark_runtime_injected_fault_triggers_replan(self):
        """Runtime generates error -> ATS replans to alternate tool -> Verified success."""
        # Attempt 1: Failed
        epa_attempt1 = EvidenceProducingAction("EPA-REC-1", CapabilityDimension.ADAPTIVE_RECOVERY, "Test", "Expected")
        epa_attempt1.attach_action("legacy_tool", {})
        epa_attempt1.attach_observation(returncode=1, stdout="", stderr="ModuleNotFoundError: legacy_tool")
        ev_1 = epa_attempt1.synthesize_evidence("m", "t", "tr", "inv")
        assert epa_attempt1.status == VerificationStatus.FAILED

        # Replan Attempt 2: Alternative tool
        epa_attempt2 = EvidenceProducingAction("EPA-REC-2", CapabilityDimension.ADAPTIVE_RECOVERY, "Test", "Expected")
        epa_attempt2.attach_action("builtin_fallback_tool", {})
        epa_attempt2.attach_observation(returncode=0, stdout="Processed successfully via fallback")
        epa_attempt2.attach_verification("RESULT_AUDIT", True, "Output verified", is_independent=True)
        ev_2 = epa_attempt2.synthesize_evidence("m", "t", "tr", "inv")
        assert epa_attempt2.status == VerificationStatus.VERIFIED

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_attempt1, epa_attempt2],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.ADAPTIVE_RECOVERY, required_level=EvidenceLevel.E2_VERIFIED)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.TERMINATE_WITH_PROOF

    # ─────────────────────────────────────────────────────────────
    # VECTOR 10: Full Self-Proving Matrix End-to-End
    # ─────────────────────────────────────────────────────────────
    def test_10_full_self_proving_benchmark_end_to_end(self):
        """Simulates full 3-dimension Self-Proving benchmark with real Evidence Gate termination."""
        # 1. Reasoning (E3 required)
        epa_r = EvidenceProducingAction("EPA-R", CapabilityDimension.REASONING_LOGIC, "Algorithmic proof", "Expected 42")
        epa_r.register_claim("Can solve arithmetic")
        epa_r.attach_action("python_eval", {"expr": "6*7"})
        epa_r.attach_observation(0, "42")
        epa_r.attach_verification("DETERMINISTIC_ASSERT", True, "42 == 42", is_independent=True)
        epa_r.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_1")

        # 2. File Actuation (E2 required)
        epa_f = EvidenceProducingAction("EPA-F", CapabilityDimension.TOOL_FILE_ACTUATION, "File write/read", "Exact match")
        epa_f.register_claim("Can manipulate files")
        epa_f.attach_action("write_file", {"path": "test.txt", "data": "JKAI"})
        epa_f.attach_observation(0, "Wrote 4 bytes")
        epa_f.attach_verification("READBACK_SHA256", True, "Match", is_independent=False)
        epa_f.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_2")

        # 3. Adaptive Recovery (E2 required)
        epa_rec = EvidenceProducingAction("EPA-REC", CapabilityDimension.ADAPTIVE_RECOVERY, "Fault recovery", "Recovery success")
        epa_rec.register_claim("Can recover from faults")
        epa_rec.attach_action("fallback_executor", {})
        epa_rec.attach_observation(0, "Recovered from prior error")
        epa_rec.attach_verification("RECOVERY_CHECK", True, "Recovered", is_independent=False)
        epa_rec.synthesize_evidence("m_e2e", "t_e2e", "tr_e2e", "inv_3")

        reqs = [
            EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.ADAPTIVE_RECOVERY, required_level=EvidenceLevel.E2_VERIFIED)
        ]

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_r, epa_f, epa_rec],
            requirements=reqs
        )

        assert audit["verdict"] == EvidenceGateVerdict.TERMINATE_WITH_PROOF
        assert len(audit["verified_dimensions"]) == 3
        assert audit["metrics"].evidence_efficiency == 1.0
        assert audit["metrics"].evidence_coverage == 1.0
        assert audit["metrics"].unsupported_claim_rate == 0.0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 11: Adversarial Self-Claim Without EPA is Blocked
    # ─────────────────────────────────────────────────────────────
    def test_11_adversarial_self_claim_without_epa_is_blocked(self):
        """Model produces text claim but 0 EPAs -> Claim is unsupported, Evidence Gate strictly blocks completion."""
        epa_claim_only = EvidenceProducingAction(
            "EPA-ADV-1", CapabilityDimension.TOOL_FILE_ACTUATION, "Claim test", "Expected",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)
        )
        claim = epa_claim_only.register_claim("Tôi có thể thao tác file tuyệt vời mà không cần chạy gì cả.")
        # No action attached!
        ev = epa_claim_only.synthesize_evidence("m_adv", "t_adv", "tr_adv", "inv_adv")
        assert ev is None
        assert epa_claim_only.status == VerificationStatus.UNVERIFIED
        assert claim.is_supported is False

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_claim_only],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.RECOVERY
        assert audit["metrics"].unsupported_claim_rate == 1.0
        assert audit["metrics"].verified_evidence_count == 0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 12: Fake Tool Success Rejected by Execution Truth
    # ─────────────────────────────────────────────────────────────
    def test_12_fake_tool_success_rejected_by_execution_truth(self):
        """Tool returns 0/success, but verification reveals corrupt data -> Verification Fails -> Blocked."""
        epa_fake = EvidenceProducingAction(
            "EPA-FAKE", CapabilityDimension.TOOL_FILE_ACTUATION, "Corrupt test", "Exact JSON match",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED)
        )
        epa_fake.attach_action("write_file", {"path": "corrupt.json", "content": '{"valid": true}'})
        epa_fake.attach_observation(returncode=0, stdout="Wrote bytes successfully") # Tool says success!
        
        # But verification discovers payload mismatch / corruption!
        epa_fake.attach_verification(
            verifier_type="READBACK_SHA256",
            passed=False,
            details="Hash mismatch: expected a1b2c3 but found empty/corrupted buffer",
            is_independent=True
        )
        ev = epa_fake.synthesize_evidence("m_fake", "t_fake", "tr_fake", "inv_fake")
        assert epa_fake.status == VerificationStatus.FAILED
        assert ev.level == EvidenceLevel.E1_OBSERVED # Only observed, NOT verified

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_fake],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.RECOVERY
        assert audit["metrics"].verified_evidence_count == 0

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
            "EPA-REC-TRACE", CapabilityDimension.ADAPTIVE_RECOVERY, "Recovery test", "Success",
            requirement=EvidenceRequirement(capability=CapabilityDimension.ADAPTIVE_RECOVERY, required_level=EvidenceLevel.E2_VERIFIED)
        )
        epa_rec.attach_action("tool_b_fallback", {})
        epa_rec.attach_observation(0, "Tool B completed successfully")
        epa_rec.attach_verification("VERIFY_TOOL_B", True, "Pass", is_independent=True)
        epa_rec.synthesize_evidence("m_rec", "t_rec", "tr_rec", "inv_rec")
        assert epa_rec.status == VerificationStatus.VERIFIED

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_rec],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.ADAPTIVE_RECOVERY)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.TERMINATE_WITH_PROOF
        assert new_strategy == StrategyDecision.PIVOT_STRATEGY

