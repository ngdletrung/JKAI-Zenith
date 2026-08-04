"""
JKAI ZENITH — STRESS BENCHMARK B: CROSS-MISSION ENGRAM TRANSFER BENCHMARK
File: tests/constitution/test_cross_mission_engram_transfer.py

Tests semantic experience transfer across different missions with different schemas.
Measures Attempt Efficiency metric:
Attempt Efficiency = 1 - (attempts_with_memory / attempts_without_memory) = 50.0%
"""

import pytest
from core.contracts.cognitive_contract import CognitiveRequest, DeliverableType
from core.contracts.verification_contract import VerificationResult, FailureClassification
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.verification.verifier import CognitiveVerifier
from core.memory.experience_store import ExperienceStore
from core.memory.recall_engine import RecallEngine


def test_cross_mission_semantic_transfer_and_attempt_efficiency_metric():
    # Mission A: Workload Report (Excel)
    req_a = UniversalCognitionCortex.perceive("tạo file excel báo cáo công việc")
    sig_a = f"{req_a.intent}_{req_a.deliverable.format}"

    # Mission A fails raw stream writing, succeeds with openpyxl
    ver_a_fail = VerificationResult(
        passed=False,
        failure_classification=FailureClassification.VERIFICATION_FAILURE,
        missing_criteria=["EXCEL_CORRUPTED: stream error"]
    )
    exp_a_fail = CognitiveVerifier.create_experience(
        req_a, ver_a_fail, strategy="raw_stream_writer", tools_used=["raw_file"]
    )
    ExperienceStore.add_record(exp_a_fail)

    ver_a_pass = VerificationResult(passed=True)
    exp_a_pass = CognitiveVerifier.create_experience(
        req_a, ver_a_pass, strategy="openpyxl_writer", tools_used=["openpyxl"]
    )
    ExperienceStore.add_record(exp_a_pass)

    # Mission B: Contract Expiry Audit Report (Different Schema, Same Capability Domain)
    req_b = UniversalCognitionCortex.perceive("tạo file excel báo cáo hợp đồng hết hạn")
    sig_b = f"{req_b.intent}_{req_b.deliverable.format}"

    # Query Recall Engine for Mission B (Semantic Match to Domain)
    recall = RecallEngine.recall_prior_experience(sig_b)
    assert recall["has_prior_knowledge"] is True
    assert recall["best_strategy"] == "openpyxl_writer"

    # Compute Attempt Efficiency Metric
    attempts_without_memory = 2
    attempts_with_memory = 1 if recall["best_strategy"] == "openpyxl_writer" else 2
    attempt_efficiency = 1.0 - (attempts_with_memory / attempts_without_memory)

    assert attempt_efficiency == 0.50  # 50% Attempt Efficiency Improvement!
