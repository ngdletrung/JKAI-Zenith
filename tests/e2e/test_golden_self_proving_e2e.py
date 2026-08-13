"""
JKAI ZENITH AI OS — GOLDEN SELF-PROVING E2E & 10-GATE AUDIT SUITE
File: tests/e2e/test_golden_self_proving_e2e.py

Operational acceptance audit for Master's 10 Golden Gates (G1 to G10):
- G1: Task Profiler activates EvidencePolicy.REQUIRED for 'hãy tự chứng minh năng lực của bạn'
- G2: Pure text assertion isolated as ClaimRecord (E0), not counted as evidence
- G3: EPA generation across 5-dimension Self-Proving Matrix
- G4: Physical action execution (ActionRecord)
- G5: Grounded runtime truth observation (ObservationRecord)
- G6: Independent verification (VerificationRecord)
- G7: 8-link provenance trace (EEC-10)
- G8: Capability dimension relevance gating (EEC-9)
- G9: Evidence Gate strictly blocks unsupported completion
- G10: Epistemic Humility bounds final answer strictly by verified proof
- Vector 14: Evidence Forgery strictly blocked (hallucinated EV rejected by provenance)
"""

import pytest
import hashlib
from typing import Dict, Any, List

from core.os.cognition.task_profiler import profile_task
from core.os.request_orchestrator import orchestrate_request
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
    EvidenceGateAuditor
)


class TestGoldenSelfProvingE2E:

    def test_gate_g1_task_profiler_activates_evidence_policy_required(self):
        """G1: Verifies prompt 'hãy tự chứng minh năng lực của bạn' yields EvidencePolicy.REQUIRED."""
        goal = "hãy tự chứng minh năng lực của bạn"
        prof = profile_task(goal)
        assert prof.is_self_eval is True
        assert prof.evidence_policy == "REQUIRED"
        assert "SELF_EVALUATION_ACTION_ENFORCED" in prof.reason_codes
        assert prof.target_entity == "AI_SELF"

    def test_gate_g2_claim_isolated_as_e0_not_counted_as_evidence(self):
        """G2: Pure text claims are trapped as ClaimRecord and yield 0 verified evidence count."""
        epa = EvidenceProducingAction(
            "EPA-G2", CapabilityDimension.TOOL_FILE_ACTUATION, "Test claim", "Expected",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)
        )
        claim = epa.register_claim("Tôi nhanh, tôi đa nhiệm, tôi hiểu tiếng Việt")
        assert isinstance(claim, ClaimRecord)
        assert claim.is_supported is False

        # No actions taken
        ev = epa.synthesize_evidence("m", "t", "tr", "inv")
        assert ev is None
        assert epa.status == VerificationStatus.UNVERIFIED

        metrics = EvidenceGateAuditor.calculate_metrics([epa], [EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION)])
        assert metrics.verified_evidence_count == 0
        assert metrics.unsupported_claim_count == 1

    def test_gate_g3_to_g8_full_epa_execution_observation_verification_and_provenance(self):
        """G3 to G8: EPA Action -> Observation -> Verification -> E2/E3 Evidence -> 8-Link Provenance."""
        # 1. ACTUATION (E2 required)
        epa_act = EvidenceProducingAction(
            "EPA-ACT", CapabilityDimension.TOOL_FILE_ACTUATION, "Write/Read file test", "Exact hash match",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED)
        )
        act_rec = epa_act.attach_action("write_file", {"path": "self_test.json", "content": '{"test": "pass"}'})
        assert act_rec.tool_name == "write_file"
        obs_rec = epa_act.attach_observation(returncode=0, stdout="Wrote 16 bytes", output_bytes=16)
        assert obs_rec.returncode == 0
        ver_rec = epa_act.attach_verification("READBACK_SHA256", passed=True, details="Readback matches expected payload", is_independent=False)
        ev_act = epa_act.synthesize_evidence("m_golden", "t_golden", "tr_golden", "inv_01")
        assert ev_act.level == EvidenceLevel.E2_VERIFIED
        assert epa_act.status == VerificationStatus.VERIFIED

        # G7: Check 8-link provenance
        prov = ev_act.provenance_trace
        assert prov["mission_id"] == "m_golden"
        assert prov["task_id"] == "t_golden"
        assert prov["trace_id"] == "tr_golden"
        assert prov["invocation_id"] == "inv_01"
        assert prov["epa_id"] == "EPA-ACT"
        assert ev_act.action_id == act_rec.action_id
        assert ev_act.obs_id == obs_rec.obs_id
        assert ev_act.ver_id == ver_rec.ver_id

        # 2. COMPUTATIONAL_CORRECTNESS (E3 required)
        epa_calc = EvidenceProducingAction(
            "EPA-CALC", CapabilityDimension.REASONING_LOGIC, "Deterministic solution test", "Output 42",
            requirement=EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
        )
        epa_calc.attach_action("python_eval", {"expr": "6*7"})
        epa_calc.attach_observation(returncode=0, stdout="42")
        epa_calc.attach_verification("DETERMINISTIC_ASSERT", passed=True, details="42 == 42", is_independent=True)
        ev_calc = epa_calc.synthesize_evidence("m_golden", "t_golden", "tr_golden", "inv_02")
        assert ev_calc.level == EvidenceLevel.E3_INDEPENDENTLY_VERIFIED

        # G8: Relevance check
        assert ev_act.capability == CapabilityDimension.TOOL_FILE_ACTUATION
        assert ev_calc.capability == CapabilityDimension.REASONING_LOGIC

    def test_gate_g9_and_g10_evidence_gate_blocks_unmet_and_enforces_humility(self):
        """G9 & G10: Gate blocks unverified missions and marks unprobed capabilities as UNVERIFIED."""
        epa_act = EvidenceProducingAction(
            "EPA-ACT", CapabilityDimension.TOOL_FILE_ACTUATION, "Write/Read", "OK",
            requirement=EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED)
        )
        epa_act.attach_action("write_file", {})
        epa_act.attach_observation(0, "OK")
        epa_act.attach_verification("READBACK", True, "OK", is_independent=False)
        epa_act.synthesize_evidence("m", "t", "tr", "inv")

        # Required 5 dimensions from Master's Self-Proving Matrix
        reqs = [
            EvidenceRequirement(capability=CapabilityDimension.TOOL_FILE_ACTUATION, required_level=EvidenceLevel.E2_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.ADAPTIVE_RECOVERY, required_level=EvidenceLevel.E2_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.LONG_HORIZON_AUTONOMY, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED),
            EvidenceRequirement(capability=CapabilityDimension.EXTERNAL_WEB_RECON, required_level=EvidenceLevel.E3_INDEPENDENTLY_VERIFIED)
        ]

        # Audit with only 1 dimension proven -> LOW_CONFIDENCE_CONCLUSION with Epistemic Humility
        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_act],
            requirements=reqs
        )

        assert audit["verdict"] == EvidenceGateVerdict.LOW_CONFIDENCE_CONCLUSION
        assert CapabilityDimension.TOOL_FILE_ACTUATION in audit["verified_dimensions"]
        assert CapabilityDimension.REASONING_LOGIC in audit["unverified_dimensions"]
        assert CapabilityDimension.LONG_HORIZON_AUTONOMY in audit["unverified_dimensions"]
        assert CapabilityDimension.EXTERNAL_WEB_RECON in audit["unverified_dimensions"]
        assert audit["metrics"].evidence_coverage == 0.2

    def test_vector_14_evidence_forgery_strictly_rejected(self):
        """Vector 14: LLM outputs fabricated evidence text without valid Action/Obs/Ver records -> Rejected."""
        # Attempting to synthesize evidence without action/observation records
        epa_forged = EvidenceProducingAction(
            "EPA-FORGED", CapabilityDimension.REASONING_LOGIC, "Forged test", "Expected",
            requirement=EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC)
        )
        # No action, no observation, no verification attached!
        ev = epa_forged.synthesize_evidence("m_fake", "t_fake", "tr_fake", "inv_fake")
        assert ev is None # Synthesizer strictly returns None
        assert epa_forged.status == VerificationStatus.UNVERIFIED

        audit = EvidenceGateAuditor.audit_completion(
            policy=EvidencePolicy.REQUIRED,
            epas=[epa_forged],
            requirements=[EvidenceRequirement(capability=CapabilityDimension.REASONING_LOGIC)]
        )
        assert audit["verdict"] == EvidenceGateVerdict.RECOVERY
        assert audit["metrics"].verified_evidence_count == 0
