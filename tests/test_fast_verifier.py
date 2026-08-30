# -*- coding: utf-8 -*-
"""
Unit test suite cho FastVerifier v3.0 (Deterministic Multimodal Artifact Verifier)
"""

import os
import openpyxl
import pytest
from core.os.cognition.fast_verifier import FastVerifier, fast_verifier


class TestFastVerifierV3:
    """Kiểm tra các phương thức thẩm định đa định dạng của FastVerifier v3.0."""

    def test_verify_python_script_valid(self, tmp_path):
        py_file = tmp_path / "valid_script.py"
        py_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        rec = fast_verifier.verify_python_script(str(py_file))
        assert rec.is_verified is True
        assert rec.artifact_sha256 is not None

    def test_verify_python_script_syntax_error(self, tmp_path):
        py_file = tmp_path / "invalid_script.py"
        py_file.write_text("def broken_syntax(\n    return missing", encoding="utf-8")

        rec = fast_verifier.verify_python_script(str(py_file))
        assert rec.is_verified is False
        assert rec.failure_class == "PYTHON_SYNTAX_ERROR"

    def test_verify_pdf_valid(self, tmp_path):
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%test binary content\n%%EOF")

        rec = fast_verifier.verify_pdf(str(pdf_file))
        assert rec.is_verified is True

    def test_verify_json_valid_and_keys(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text('{"status": "ok", "count": 42}', encoding="utf-8")

        rec = fast_verifier.verify_json(str(json_file), expected_keys=["status", "count"])
        assert rec.is_verified is True

    def test_verify_csv_valid_and_columns(self, tmp_path):
        csv_file = tmp_path / "report.csv"
        csv_file.write_text("STT,Họ tên,Doanh thu\n1,Nguyễn Văn A,5000000\n", encoding="utf-8-sig")

        rec = fast_verifier.verify_csv(str(csv_file), expected_columns=["STT", "Họ tên", "Doanh thu"])
        assert rec.is_verified is True

    def test_verify_text_utf8(self, tmp_path):
        txt_file = tmp_path / "notes.md"
        txt_file.write_text("# Tiêu Đề Báo Cáo\nNội dung chi tiết tiếng Việt có dấu.", encoding="utf-8")

        rec = fast_verifier.verify_text(str(txt_file))
        assert rec.is_verified is True

    def test_verify_excel_semantic_schema(self, tmp_path):
        xlsx_file = tmp_path / "bang_luong.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["STT", "Họ và tên", "Lương thực lĩnh"])
        ws.append([1, "Lê Văn B", 15000000])
        wb.save(xlsx_file)

        # 1. Khớp hoàn toàn
        rec_pass = fast_verifier.verify_excel(str(xlsx_file), expected_columns=["STT", "Họ và tên"])
        assert rec_pass.is_verified is True

        # 2. Thiếu cột
        rec_fail = fast_verifier.verify_excel(str(xlsx_file), expected_columns=["STT", "Chức vụ"])
        assert rec_fail.is_verified is False

    def test_verify_batch_artifacts(self, tmp_path):
        f1 = tmp_path / "file1.txt"
        f1.write_text("Hello text file", encoding="utf-8")
        f2 = tmp_path / "file2.json"
        f2.write_text('{"ok": true}', encoding="utf-8")

        reports = fast_verifier.verify_artifacts([str(f1), str(f2)])
        assert len(reports) == 2
        assert all(r.is_verified for r in reports)
