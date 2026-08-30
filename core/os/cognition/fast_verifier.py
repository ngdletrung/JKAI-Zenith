# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — FAST DETERMINISTIC VERIFIER v3.0                 ║
║   Thẩm Định Đa Định Dạng (Excel, Word, PDF, CSV, TXT, MD, Code)  ║
║   Semantic Schema Validation & Batch Verification                ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Bộ Thẩm Định Bằng Chứng Toàn Diện. 🔍🏛️⚡*
"""

from __future__ import annotations
import os
import csv
import ast
import json
import time
import hashlib
import logging
from typing import List, Optional, Dict, Any

from core.os.cognition.fast_schemas import (
    FastVerificationEvidence,
    FastVerificationRecord,
)

logger = logging.getLogger("JKAI.FastVerifier")


class FastVerifier:
    """
    🔍 Bộ Thẩm Định Bằng Chứng Vật Lý Thực Tế v3.0 (Deterministic Epistemic Verifier).
    Hỗ trợ kiểm tra cấu trúc, xác thực cột dữ liệu (Semantic Header), thẩm định hàng loạt (Batch).
    """

    def verify_artifact(
        self,
        artifact_path: str,
        expected_columns: Optional[List[str]] = None,
        expected_min_rows: int = 2,
        **kwargs
    ) -> FastVerificationRecord:
        """Dispatcher tự động nhận diện phần mở rộng và kiểm định định dạng tương ứng."""
        t0 = time.perf_counter()
        if not artifact_path or not os.path.exists(artifact_path):
            rec = FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "Tệp tin không tồn tại", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING",
                recovery_hint="Re-run synthesis with verified output path"
            )
            self._record_telemetry(rec, (time.perf_counter() - t0) * 1000, "MISSING")
            return rec

        ext = os.path.splitext(artifact_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            rec = self.verify_excel(artifact_path, expected_columns=expected_columns, expected_min_rows=expected_min_rows, **kwargs)
        elif ext in (".docx", ".doc"):
            rec = self.verify_word(artifact_path, **kwargs)
        elif ext == ".pdf":
            rec = self.verify_pdf(artifact_path, **kwargs)
        elif ext == ".csv":
            rec = self.verify_csv(artifact_path, expected_columns=expected_columns, expected_min_rows=expected_min_rows, **kwargs)
        elif ext in (".txt", ".md", ".log"):
            rec = self.verify_text(artifact_path, **kwargs)
        elif ext == ".py":
            rec = self.verify_python_script(artifact_path, **kwargs)
        elif ext == ".json":
            rec = self.verify_json(artifact_path, **kwargs)
        else:
            rec = self._verify_generic_file(artifact_path)

        self._record_telemetry(rec, (time.perf_counter() - t0) * 1000, ext)
        return rec

    def verify_artifacts(self, artifact_paths: List[str], **kwargs) -> List[FastVerificationRecord]:
        """Thẩm định hàng loạt (Batch Verification) nhiều artifact đồng thời."""
        return [self.verify_artifact(path, **kwargs) for path in artifact_paths if path]

    def verify_excel(
        self,
        artifact_path: str,
        expected_columns: Optional[List[str]] = None,
        expected_min_rows: int = 2,
        require_formulas: bool = False,
        require_charts: bool = False,
    ) -> FastVerificationRecord:
        """Thẩm định bảng tính Excel (.xlsx) kèm Semantic Column Validation."""
        evidences: List[FastVerificationEvidence] = []
        
        # E1: File exists
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "File does not exist or empty", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING",
                recovery_hint="Re-run synthesis with explicit output directory"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"File exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1_pass"))

        # E2 & E3: XLSX Readable & Valid Structure (Optimized read)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(artifact_path, data_only=False)
            ws = wb.active
            evidences.append(FastVerificationEvidence("E2_FILE_READABLE", True, f"Workbook loaded ({len(wb.sheetnames)} sheets)", "hash_e2_pass"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_FILE_READABLE", False, f"Corrupted XLSX: {e}", "hash_e2_fail")],
                failure_class="MALFORMED_XLSX",
                recovery_hint="Re-generate workbook using safe template"
            )

        # E4: Row Count
        max_r = ws.max_row
        row_pass = max_r >= expected_min_rows
        evidences.append(FastVerificationEvidence(
            "E3_ROW_COUNT", row_pass, f"Found {max_r} rows (required >= {expected_min_rows})", "hash_e3"
        ))

        # E5: Semantic Column Header Validation
        if expected_columns:
            headers = [str(cell.value).strip().lower() for cell in ws[1] if cell.value is not None]
            missing_cols = [col for col in expected_columns if col.lower() not in headers]
            schema_pass = len(missing_cols) == 0
            evidences.append(FastVerificationEvidence(
                "E4_SCHEMA_COLUMNS_MATCH",
                schema_pass,
                f"Matched columns: {len(headers)}. Missing: {missing_cols}" if missing_cols else "All expected columns present",
                "hash_e4_schema"
            ))

        # E6: Formulas & Charts Verification
        has_formulas = False
        formula_count = 0
        for row in ws.iter_rows(values_only=True):
            for val in row:
                if isinstance(val, str) and val.startswith("="):
                    has_formulas = True
                    formula_count += 1
        
        formula_pass = (not require_formulas) or has_formulas
        evidences.append(FastVerificationEvidence(
            "E5_FORMULAS_PRESENT", formula_pass, f"Formulas detected: {formula_count}", "hash_e5"
        ))

        has_charts = len(getattr(ws, "_charts", [])) > 0
        chart_pass = (not require_charts) or has_charts
        evidences.append(FastVerificationEvidence(
            "E6_CHARTS_PRESENT", chart_pass, f"Embedded charts: {len(getattr(ws, '_charts', []))}", "hash_e6"
        ))

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash,
            failure_class=None if all_passed else "VERIFICATION_CRITERIA_FAILED",
            recovery_hint=None if all_passed else "Review failed criteria in evidence list"
        )

    def verify_csv(
        self,
        artifact_path: str,
        expected_columns: Optional[List[str]] = None,
        expected_min_rows: int = 2
    ) -> FastVerificationRecord:
        """Thẩm định tệp tin CSV (.csv)."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "CSV does not exist or empty", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"CSV exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1"))

        try:
            with open(artifact_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)

            row_count = len(rows)
            row_pass = row_count >= expected_min_rows
            evidences.append(FastVerificationEvidence("E2_CSV_ROWS", row_pass, f"Rows: {row_count}", "hash_e2"))

            if expected_columns and rows:
                header = [c.strip().lower() for c in rows[0]]
                missing = [col for col in expected_columns if col.lower() not in header]
                evidences.append(FastVerificationEvidence("E3_CSV_COLUMNS", len(missing) == 0, f"Missing columns: {missing}", "hash_e3"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_CSV_READABLE", False, f"CSV error: {e}", "hash_e2_fail")],
                failure_class="MALFORMED_CSV"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def verify_word(self, artifact_path: str, min_paragraphs: int = 1) -> FastVerificationRecord:
        """Thẩm định văn bản Word (.docx)."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "Word doc does not exist", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"Docx exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1"))

        try:
            import docx
            doc = docx.Document(artifact_path)
            p_count = len(doc.paragraphs)
            t_count = len(doc.tables)
            is_readable = p_count >= min_paragraphs or t_count > 0
            evidences.append(FastVerificationEvidence("E2_DOCX_READABLE", is_readable, f"Paragraphs: {p_count}, Tables: {t_count}", "hash_e2"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_DOCX_READABLE", False, str(e), "hash_e2_fail")],
                failure_class="MALFORMED_DOCX"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def verify_pdf(self, artifact_path: str) -> FastVerificationRecord:
        """Thẩm định tệp tin PDF (.pdf)."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "PDF file does not exist", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"PDF exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1"))

        try:
            with open(artifact_path, "rb") as f:
                header = f.read(5)
            is_valid_header = header.startswith(b"%PDF-")
            evidences.append(FastVerificationEvidence("E2_PDF_MAGIC_BYTES", is_valid_header, f"Header: {header}", "hash_e2"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_PDF_MAGIC_BYTES", False, str(e), "hash_e2_fail")],
                failure_class="MALFORMED_PDF"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def verify_text(self, artifact_path: str, min_chars: int = 5) -> FastVerificationRecord:
        """Thẩm định tệp tin văn bản thuần (.txt, .md, .log)."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "Text file does not exist or empty", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, "Text file exists", "hash_e1"))

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                content = f.read()
            is_valid = len(content.strip()) >= min_chars
            evidences.append(FastVerificationEvidence("E2_TEXT_UTF8_READABLE", is_valid, f"Length: {len(content)} chars", "hash_e2"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_TEXT_UTF8_READABLE", False, f"Encoding error: {e}", "hash_e2_fail")],
                failure_class="MALFORMED_TEXT"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def verify_python_script(self, artifact_path: str) -> FastVerificationRecord:
        """Thẩm định mã nguồn Python (.py) không có lỗi cú pháp."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "Python script does not exist", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"Python file exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1"))

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                code_content = f.read()
            ast.parse(code_content)
            evidences.append(FastVerificationEvidence("E2_PYTHON_AST_VALID", True, "AST syntax check passed", "hash_e2"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_PYTHON_AST_VALID", False, f"Syntax Error: {e}", "hash_e2_fail")],
                failure_class="PYTHON_SYNTAX_ERROR"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def verify_json(self, artifact_path: str, expected_keys: Optional[List[str]] = None) -> FastVerificationRecord:
        """Thẩm định tệp tin JSON (.json)."""
        evidences: List[FastVerificationEvidence] = []
        if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", False, "JSON does not exist", "hash_e1_fail")],
                failure_class="ARTIFACT_MISSING"
            )
        evidences.append(FastVerificationEvidence("E1_FILE_EXISTS", True, f"JSON file exists ({os.path.getsize(artifact_path)} bytes)", "hash_e1"))

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            evidences.append(FastVerificationEvidence("E2_JSON_VALID", True, "JSON structure valid", "hash_e2"))

            if expected_keys and isinstance(data, dict):
                missing_k = [k for k in expected_keys if k not in data]
                evidences.append(FastVerificationEvidence("E3_JSON_KEYS", len(missing_k) == 0, f"Missing keys: {missing_k}", "hash_e3"))
        except Exception as e:
            return FastVerificationRecord(
                is_verified=False,
                evidence_list=evidences + [FastVerificationEvidence("E2_JSON_VALID", False, str(e), "hash_e2_fail")],
                failure_class="MALFORMED_JSON"
            )

        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        all_passed = all(e.passed for e in evidences)
        return FastVerificationRecord(
            is_verified=all_passed,
            evidence_list=evidences,
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def _verify_generic_file(self, artifact_path: str) -> FastVerificationRecord:
        """Thẩm định tệp tin chung."""
        f_size = os.path.getsize(artifact_path)
        with open(artifact_path, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        return FastVerificationRecord(
            is_verified=f_size > 0,
            evidence_list=[FastVerificationEvidence("E1_FILE_EXISTS", f_size > 0, f"Size: {f_size} bytes", "hash_generic")],
            artifact_path=artifact_path,
            artifact_sha256=f_hash
        )

    def _record_telemetry(self, rec: FastVerificationRecord, duration_ms: float, ext: str) -> None:
        try:
            from core.telemetry.observability_engine import observability_engine
            observability_engine.record_span(
                name="fast_verifier_audit",
                category="VERIFICATION",
                duration_ms=duration_ms,
                metadata={"is_verified": rec.is_verified, "ext": ext, "failure_class": rec.failure_class}
            )
        except Exception:
            pass


fast_verifier = FastVerifier()
