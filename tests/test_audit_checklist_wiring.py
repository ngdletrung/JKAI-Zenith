"""
Unit test proving true physical wiring between AUDIT_CHECKLIST and ast_code_auditor.
Verifies that checklist items dynamically drive auditor findings.
"""
import pytest
from pathlib import Path
from core.utils.code_review_checklist import AUDIT_CHECKLIST, AuditChecklistItem
from core.utils.ast_code_auditor import audit_python_file, format_audit_report, get_checklist_map


def test_checklist_not_empty():
    assert len(AUDIT_CHECKLIST) >= 7
    codes = [item.code for item in AUDIT_CHECKLIST]
    assert "B1_B2" in codes
    assert "B5" in codes
    assert "B6" in codes


def test_auditor_uses_checklist_metadata(tmp_path):
    test_file = tmp_path / "sample.py"
    test_file.write_text('cur.execute("SELECT * FROM foo WHERE id = " + str(x))\n', encoding="utf-8")

    findings = audit_python_file(str(test_file))
    assert len(findings) > 0
    f = findings[0]
    assert f["code"] == "B1_B2"
    assert f["risk"] == "CRITICAL"
    assert "SQL Injection" in f["name"]


def test_custom_checklist_changes_auditor_behavior(tmp_path):
    test_file = tmp_path / "sample2.py"
    test_file.write_text('cur.execute("SELECT * FROM foo WHERE id = " + str(x))\n', encoding="utf-8")

    # Tạo custom checklist với mô tả và mức rủi ro thay đổi
    custom_rule = AuditChecklistItem(
        code="B1_B2",
        category="An Ninh Cao Cấp",
        name="Custom SQLi Rule",
        description="Phat hien noi chuoi SQL tuy bien!",
        risk_level="EXTREME",
        sample_pattern=""
    )
    custom_checklist = [custom_rule]

    findings = audit_python_file(str(test_file), checklist=custom_checklist)
    assert len(findings) > 0
    f = findings[0]
    # Xác nhận metadata hoàn toàn lấy từ custom_checklist (chứng minh đấu nối thật 100%)
    assert f["category"] == "An Ninh Cao Cấp"
    assert f["name"] == "Custom SQLi Rule"
    assert f["risk"] == "EXTREME"
    assert f["detail"] == "Phat hien noi chuoi SQL tuy bien!"

    report = format_audit_report(str(test_file), checklist=custom_checklist)
    assert "[EXTREME] Custom SQLi Rule" in report
    assert "Phat hien noi chuoi SQL tuy bien!" in report
