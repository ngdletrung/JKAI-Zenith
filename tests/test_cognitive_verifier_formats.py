# -*- coding: utf-8 -*-
"""
Unit test suite cho CognitiveVerifier mở rộng (JSON, CSV, PDF, Excel)
"""

import os
import pytest
from core.contracts.cognitive_contract import CognitiveRequest, DeliverableSpec, DeliverableType
from core.contracts.identity_contract import IdentityChain
from core.verification.verifier import CognitiveVerifier


class TestCognitiveVerifierFormats:
    """Kiểm tra khả năng thẩm định tính toàn vẹn đa định dạng của CognitiveVerifier."""

    def test_verify_valid_json_file(self, tmp_path):
        json_file = str(tmp_path / "data.json")
        with open(json_file, "w", encoding="utf-8") as f:
            f.write('{"status": "ok", "items": [1, 2, 3]}')

        req = CognitiveRequest(
            identity=IdentityChain(task_id="t1", mission_id="m1"),
            intent="OFFICE",
            goal="Xuất file JSON",
            deliverable=DeliverableSpec(type=DeliverableType.FILE_CODE, format="json", target_path=json_file)
        )
        res = CognitiveVerifier.verify(req, {"file_path": json_file})
        assert res.passed is True
        assert res.score == 1.0

    def test_verify_corrupted_json_file(self, tmp_path):
        bad_json = str(tmp_path / "bad.json")
        with open(bad_json, "w", encoding="utf-8") as f:
            f.write('{"status": "ok", "items": [1, 2,')  # Lỗi thiếu ngoặc đóng

        req = CognitiveRequest(
            identity=IdentityChain(task_id="t2", mission_id="m2"),
            intent="OFFICE",
            goal="Xuất file JSON",
            deliverable=DeliverableSpec(type=DeliverableType.FILE_CODE, format="json", target_path=bad_json)
        )
        res = CognitiveVerifier.verify(req, {"file_path": bad_json})
        assert res.passed is False
        assert any("JSON_CORRUPTED" in m for m in res.missing_criteria)

    def test_verify_valid_csv_file(self, tmp_path):
        csv_file = str(tmp_path / "output.csv")
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("id,name,value\n1,Alpha,100\n2,Beta,200\n")

        req = CognitiveRequest(
            identity=IdentityChain(task_id="t3", mission_id="m3"),
            intent="OFFICE",
            goal="Xuất file CSV",
            deliverable=DeliverableSpec(type=DeliverableType.FILE_CODE, format="csv", target_path=csv_file)
        )
        res = CognitiveVerifier.verify(req, {"file_path": csv_file})
        assert res.passed is True

    def test_verify_pdf_header(self, tmp_path):
        pdf_file = str(tmp_path / "doc.pdf")
        with open(pdf_file, "wb") as f:
            f.write(b"%PDF-1.4\n%JKAI Zenith PDF Binary Content\n%%EOF")

        req = CognitiveRequest(
            identity=IdentityChain(task_id="t4", mission_id="m4"),
            intent="OFFICE",
            goal="Xuất file PDF",
            deliverable=DeliverableSpec(type=DeliverableType.FILE_BINARY, format="pdf", target_path=pdf_file)
        )
        res = CognitiveVerifier.verify(req, {"file_path": pdf_file})
        assert res.passed is True

    def test_classify_expanded_failures(self):
        from core.verification.failure_classifier import FailureClassifier
        from core.contracts.verification_contract import FailureClassification, RecoveryStrategy

        f_cls, strat = FailureClassifier.classify_failure(["DOCX_CORRUPTED: Missing XML"], [])
        assert f_cls == FailureClassification.VERIFICATION_FAILURE
        assert strat == RecoveryStrategy.DIAGNOSE_AND_REPAIR

        f_cls2, strat2 = FailureClassifier.classify_failure(["MODULE_NOT_FOUND: docx"], [])
        assert f_cls2 == FailureClassification.TOOL_FAILURE
        assert strat2 == RecoveryStrategy.SUBSTITUTE_CAPABILITY
