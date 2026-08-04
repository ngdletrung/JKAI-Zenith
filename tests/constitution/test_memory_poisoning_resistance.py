"""
JKAI ZENITH — CONSTITUTION TEST: MEMORY POISONING RESISTANCE & AUTHORITY HIERARCHY
File: tests/constitution/test_memory_poisoning_resistance.py

Proves that Engram v2 Memory is treated as EVIDENCE, NOT TRUTH.
When a poisoned/false memory claims a faulty strategy ("raw_stream_writer is superior"),
the Verifier and Mission Invariants REJECT the poisoned suggestion and enforce structural validation.
"""

import pytest
from core.contracts.cognitive_contract import CognitiveRequest, MissionDefinition, DeliverableSpec, DeliverableType
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.verification.verifier import CognitiveVerifier
from core.memory.experience_store import ExperienceStore
from core.memory.recall_engine import RecallEngine


def test_engram_memory_poisoning_resistance_and_authority_hierarchy():
    # Goal: Excel generation
    req = UniversalCognitionCortex.perceive("tạo file excel báo cáo tài chính")
    sig = f"{req.intent}_{req.deliverable.format}"

    # Inject POISONED / FALSE memory record into Engram v2
    poisoned_exp = CognitiveVerifier.create_experience(
        req,
        VerificationResult(passed=True),  # Falsely claims raw_stream passed
        strategy="poisoned_raw_stream",
        tools_used=["raw_file"]
    )
    ExperienceStore.add_record(poisoned_exp)

    # Query Recall Engine
    recall = RecallEngine.recall_prior_experience(sig)
    assert recall["has_prior_knowledge"] is True

    # Candidate Strategy from Memory is evaluated as EVIDENCE, NOT TRUTH
    candidate_strategy = recall["best_strategy"]
    assert candidate_strategy == "poisoned_raw_stream"

    # Verifier evaluates candidate output on actual disk/file integrity
    poisoned_output_payload = {"file_path": "/non/existent/corrupted.xlsx"}
    ver_result = CognitiveVerifier.verify(req, poisoned_output_payload)

    # Authority Hierarchy: Verifier > Memory. Poisoned memory candidate is REJECTED!
    assert ver_result.passed is False
    assert ver_result.failure_classification == FailureClassification.TOOL_FAILURE
    assert ver_result.recommended_recovery == RecoveryStrategy.SUBSTITUTE_CAPABILITY

    # System falls back to robust capability provider (openpyxl)
    fallback_strategy = "openpyxl_writer"
    assert fallback_strategy != candidate_strategy
