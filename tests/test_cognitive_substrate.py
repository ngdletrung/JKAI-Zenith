"""
JKAI ZENITH — UNIT TEST SUITE FOR UNIVERSAL COGNITION RUNTIME SUBSTRATE (v2.1)
File: tests/test_cognitive_substrate.py
"""

import pytest
import os
import tempfile
from core.contracts.cognitive_contract import (
    CognitiveRequest,
    DeliverableType,
    RenderingHint,
    IdentityChain,
)
from core.contracts.verification_contract import (
    VerificationResult,
    FailureClassification,
    RecoveryStrategy,
)
from core.contracts.capability_contract import (
    CapabilityRequirement,
    ExecutionProfile,
)
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.verification.verifier import CognitiveVerifier


def test_identity_chain_8_steps():
    ident = IdentityChain()
    assert ident.request_id.startswith("req_")
    assert ident.mission_id.startswith("mis_")
    assert ident.plan_id.startswith("pln_")
    assert ident.task_id.startswith("tsk_")
    assert ident.attempt_id.startswith("att_")
    assert ident.execution_id.startswith("exe_")
    assert ident.observation_id.startswith("obs_")
    assert ident.verification_id.startswith("ver_")


def test_capability_requirement_contract():
    req = CapabilityRequirement(
        capability="spreadsheet_mutation",
        complexity="medium",
        latency="normal"
    )
    assert req.capability == "spreadsheet_mutation"
    assert req.complexity == "medium"
    assert req.verification_required is True


def test_universal_cognition_excel_perception():
    goal = "hãy tạo cho file excel .xlsx về báo cáo tiến độ phân công làm việc của cả 1 đội"
    req = UniversalCognitionCortex.perceive(goal)
    
    assert req.deliverable.type == DeliverableType.FILE_BINARY
    assert req.deliverable.format == "xlsx"
    assert req.deliverable.rendering_hint == RenderingHint.DOWNLOAD_LINK
    assert "MUST_OUTPUT_VALID_XLSX_FILE" in req.constraints


def test_cognitive_verifier_success():
    goal = "tạo file excel báo cáo"
    req = UniversalCognitionCortex.perceive(goal)
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Test"
        ws.append(["ID", "Name", "Progress"])
        ws.append([1, "Alex", "100%"])
        wb.save(tmp.name)
        tmp_path = tmp.name
        
    try:
        ver = CognitiveVerifier.verify(req, {"file_path": tmp_path})
        assert ver.passed is True
        assert ver.score == 1.0
        assert ver.failure_classification == FailureClassification.NONE
        assert ver.recommended_recovery == RecoveryStrategy.NONE
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_cognitive_verifier_missing_file_failure_classification():
    goal = "tạo file pdf báo cáo"
    req = UniversalCognitionCortex.perceive(goal)
    
    ver = CognitiveVerifier.verify(req, {"file_path": "/non/existent/file.pdf"})
    assert ver.passed is False
    assert ver.score < 1.0
    assert ver.failure_classification == FailureClassification.TOOL_FAILURE
    assert ver.recommended_recovery == RecoveryStrategy.SUBSTITUTE_CAPABILITY
    
    exp = CognitiveVerifier.create_experience(req, ver, strategy="python_pdf", tools_used=["pdf_gen"])
    assert exp.outcome == "FAILED"
    assert exp.failure_classification == FailureClassification.TOOL_FAILURE
    assert len(exp.negative_lessons) > 0
