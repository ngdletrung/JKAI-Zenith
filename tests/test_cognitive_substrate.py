"""
JKAI ZENITH — UNIT TEST SUITE FOR UNIVERSAL COGNITION RUNTIME SUBSTRATE
File: tests/test_cognitive_substrate.py
"""

import pytest
import os
import tempfile
from core.contracts.cognitive_contract import (
    CognitiveRequest,
    DeliverableType,
    RenderingHint,
)
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.cognitive.verifier import CognitiveVerifier


def test_universal_cognition_excel_perception():
    goal = "hãy tạo cho file excel .xlsx về báo cáo tiến độ phân công làm việc của cả 1 đội"
    req = UniversalCognitionCortex.perceive(goal)
    
    assert req.deliverable.type == DeliverableType.FILE_BINARY
    assert req.deliverable.format == "xlsx"
    assert req.deliverable.rendering_hint == RenderingHint.DOWNLOAD_LINK
    assert req.execution_depth == "DEEP_PLANNING"
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
        assert len(ver.missing_criteria) == 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_cognitive_verifier_missing_file():
    goal = "tạo file pdf báo cáo"
    req = UniversalCognitionCortex.perceive(goal)
    
    ver = CognitiveVerifier.verify(req, {"file_path": "/non/existent/file.pdf"})
    assert ver.passed is False
    assert ver.score < 1.0
    assert any("PHYSICAL_FILE_MISSING" in m for m in ver.missing_criteria)
    
    exp = CognitiveVerifier.create_experience(req, ver, strategy="python_pdf", tools_used=["pdf_gen"])
    assert exp.outcome == "FAILED"
    assert len(exp.negative_lessons) > 0
