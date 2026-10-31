import pytest
from core.kernel.coverage_ledger import CoverageLedger
from core.utils.findings_schema import (
    AuditReport,
    FindingItem,
    validate_findings_dict,
    validate_findings_json,
)


def test_coverage_ledger_goal_parsing():
    goal = (
        "Kiểm toán 2 tệp core/security/egress_gate.py và core/security/data_leak_guard.py. "
        "Yêu cầu: đếm số dòng, tính mã băm sha256, liệt kê class, hàm, giải thích cơ chế phối hợp "
        "và đính kèm mã canary NP3-CANARY-1234."
    )
    ledger = CoverageLedger("TASK-001", goal)
    assert len(ledger.required_files) == 2
    assert "core/security/egress_gate.py" in ledger.required_files
    assert "core/security/data_leak_guard.py" in ledger.required_files
    assert "line_count" in ledger.required_checks
    assert "sha256" in ledger.required_checks
    assert "class_list" in ledger.required_checks
    assert "function_list" in ledger.required_checks
    assert "mechanism_explanation" in ledger.required_checks
    assert "canary_verification" in ledger.required_checks


def test_coverage_ledger_tracking_and_completion():
    goal = "Kiểm toán core/security/egress_gate.py và core/security/data_leak_guard.py với mã băm sha256."
    ledger = CoverageLedger("TASK-001", goal)
    
    # Chưa đọc file nào
    rep0 = ledger.evaluate_coverage()
    assert rep0["coverage_percent"] == 0.0
    assert not rep0["is_complete"]
    assert len(rep0["missing_files"]) == 2

    # Đọc 1 file
    ledger.record_file_read("core/security/egress_gate.py", lines=150, sha256_prefix="a5932abe94b11d1e")
    rep1 = ledger.evaluate_coverage()
    assert rep1["coverage_percent"] > 0.0
    assert not rep1["is_complete"]
    assert len(rep1["missing_files"]) == 1

    # Đọc nốt file 2 và hoàn thành check sha256
    ledger.record_file_read("core/security/data_leak_guard.py", lines=127, sha256_prefix="2f368f58f7166028")
    ledger.record_check_completed("sha256", evidence="Đã tính SHA-256 khớp tuyệt đối")
    rep2 = ledger.evaluate_coverage()
    assert rep2["coverage_percent"] == 100.0
    assert rep2["is_complete"]
    assert len(rep2["missing_files"]) == 0
    assert len(rep2["missing_checks"]) == 0


def test_findings_schema_valid_confirmed():
    payload = {
        "task_id": "TASK-001",
        "verdict": "confirmed",
        "findings": [
            {
                "file": "core/security/egress_gate.py",
                "line_count": 150,
                "sha256_16": "a5932abe94b11d1e",
                "classes": ["CentralizedEgressGate", "EgressDecision"],
                "functions": ["evaluate_payload", "authorize_discuss_mission"],
                "mechanism": "Đọc data_leak_guard.has_active_alert(mission_id) -> reason='reverse_solicitation_alert_active'",
                "severity": "high",
                "evidence": "core/security/egress_gate.py:92-110",
            }
        ],
        "canary": "NP3-CANARY-20261017-9E4B2F81",
        "coverage_percent": 100.0,
        "unresolved_facts": [],
        "notes": "Kiểm toán hoàn tất với đầy đủ bằng chứng xác thực",
    }
    ok, err, report = validate_findings_dict(payload)
    assert ok
    assert err is None
    assert report.verdict == "confirmed"
    assert report.findings[0].line_count == 150
    assert report.canary == "NP3-CANARY-20261017-9E4B2F81"


def test_findings_schema_anti_pattern_9_guard():
    # Anti-Pattern #9: needs_validation tuyệt đối không được có severity
    payload = {
        "task_id": "TASK-001",
        "verdict": "needs_validation",
        "findings": [
            {
                "file": "core/security/egress_gate.py",
                "severity": "critical",  # VI PHẠM: needs_validation không được gán severity
                "evidence": "Không đọc được tệp",
            }
        ],
        "coverage_percent": 0.0,
        "unresolved_facts": ["Chưa thực thi view_file thành công"],
    }
    ok, err, report = validate_findings_dict(payload)
    assert not ok
    assert "Anti-Pattern #9 vi phạm" in err
    assert report is None


def test_findings_schema_invalid_verdict():
    payload = {
        "task_id": "TASK-001",
        "verdict": "maybe_vulnerable",  # Verdict ngoài danh sách chuẩn
        "findings": [],
    }
    ok, err, report = validate_findings_dict(payload)
    assert not ok
    assert "Input should be 'confirmed', 'needs_validation' or 'rejected'" in err


def test_project_agent_loop_coverage_ledger_wiring():
    from core.kernel.project_agent_loop import ProjectAgentLoop
    loop = ProjectAgentLoop(executor_gateway=None, project_root=".", mode="audit")
    
    # Initialize ledger via simulated goal
    goal = "Kiểm toán core/security/egress_gate.py và core/security/data_leak_guard.py với mã canary NP3-CANARY-9999"
    loop._coverage_ledger = CoverageLedger("TASK-001", goal)
    
    # 1. When files are not read yet -> pre_submission_check fails due to missing files in ledger
    ans_without_read = "Báo cáo kiểm toán: NP3-CANARY-9999 class EgressGate hàm run"
    ok, missing = loop._pre_submission_check(ans_without_read, goal)
    assert not ok
    assert any("Chưa đọc đủ các tệp bắt buộc theo Coverage Ledger" in m for m in missing)
    
    # 2. When files are recorded into ledger -> pre_submission_check passes
    loop._coverage_ledger.record_file_read("core/security/egress_gate.py", lines=150, sha256_prefix="a5932abe94b11d1e")
    loop._coverage_ledger.record_file_read("core/security/data_leak_guard.py", lines=127, sha256_prefix="2f368f58f7166028")
    ok, missing = loop._pre_submission_check(ans_without_read, goal)
    assert ok
    assert len(missing) == 0


def test_project_agent_loop_finalize_findings_schema_block():
    from core.kernel.project_agent_loop import ProjectAgentLoop
    loop = ProjectAgentLoop(executor_gateway=None, project_root=".", mode="audit")
    goal = "Kiểm toán core/security/egress_gate.py với NP3-CANARY-8888"
    loop._coverage_ledger = CoverageLedger("TASK-001", goal)
    loop._coverage_ledger.record_file_read("core/security/egress_gate.py", lines=150, sha256_prefix="a5932abe94b11d1e")
    loop._coverage_ledger.record_check_completed("canary_verification", evidence="NP3-CANARY-8888")
    
    answer_text = "Kết quả phân tích: egress_gate.py có 150 dòng. Mã Canary: NP3-CANARY-8888."
    final_output = loop._finalize(answer_text, "TASK-001")
    
    assert "### 📊 MACHINE-READABLE FINDINGS (C4 FindingsSchema)" in final_output
    assert '"verdict": "confirmed"' in final_output
    assert '"canary": "NP3-CANARY-8888"' in final_output
    assert '"coverage_percent": 100.0' in final_output

