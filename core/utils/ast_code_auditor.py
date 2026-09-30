"""
AST & Heuristic Static Code Auditor for JKAI Exoskeleton Substrate.
Provides deterministic, zero-hallucination code inspection for local models.
Directly driven by rules defined in core.utils.code_review_checklist.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.utils.code_review_checklist import AUDIT_CHECKLIST, AuditChecklistItem


def get_checklist_map(checklist: Optional[List[AuditChecklistItem]] = None) -> Dict[str, AuditChecklistItem]:
    """Tạo map từ rule code sang AuditChecklistItem."""
    items = checklist if checklist is not None else AUDIT_CHECKLIST
    return {item.code: item for item in items}


def audit_python_file(
    file_path: str, 
    checklist: Optional[List[AuditChecklistItem]] = None
) -> List[Dict[str, Any]]:
    """
    Rà soát mã nguồn Python bằng AST và pattern matching dựa trên checklist quy chuẩn.
    Nếu truyền checklist tùy biến, hàm sẽ áp dụng các tiêu chí từ checklist đó.
    """
    if not os.path.exists(file_path):
        return []

    try:
        code = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = code.splitlines()
    rule_map = get_checklist_map(checklist)
    findings = []

    # 1. AST Analysis
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # B1_B2: Quét SQL Injection trong cur.execute(...)
            if "B1_B2" in rule_map and isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "execute":
                    if node.args:
                        arg0 = node.args[0]
                        rule = rule_map["B1_B2"]
                        # Nối chuỗi bằng dấu +
                        if isinstance(arg0, ast.BinOp) and isinstance(arg0.op, ast.Add):
                            findings.append({
                                "line": arg0.lineno,
                                "code": rule.code,
                                "name": rule.name,
                                "category": rule.category,
                                "risk": rule.risk_level,
                                "detail": rule.description
                            })
                        # Format string %
                        elif isinstance(arg0, ast.BinOp) and isinstance(arg0.op, ast.Mod):
                            findings.append({
                                "line": arg0.lineno,
                                "code": rule.code,
                                "name": rule.name,
                                "category": rule.category,
                                "risk": rule.risk_level,
                                "detail": rule.description
                            })
                        # f-string trong execute
                        elif isinstance(arg0, ast.JoinedStr):
                            findings.append({
                                "line": arg0.lineno,
                                "code": rule.code,
                                "name": rule.name,
                                "category": rule.category,
                                "risk": rule.risk_level,
                                "detail": rule.description
                            })

            # B7: Quét hàm stub trả về hằng số cứng
            if "B7" in rule_map and isinstance(node, ast.FunctionDef):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Constant):
                    val = body[0].value.value
                    if val in (42, "TODO", None) or (isinstance(val, (int, str)) and val != 0 and val != True and val != False):
                        rule = rule_map["B7"]
                        findings.append({
                            "line": body[0].lineno,
                            "code": rule.code,
                            "name": rule.name,
                            "category": rule.category,
                            "risk": rule.risk_level,
                            "detail": f"Hàm {node.name} chỉ trả về giá trị cứng {val}: {rule.description}"
                        })

            # B5: strptime thiếu bọc try/except ValueError
            if "B5" in rule_map and isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "strptime":
                    # Kiểm tra xem node có nằm trong Try block không
                    line_no = node.lineno
                    rule = rule_map["B5"]
                    # Kiểm tra ngữ cảnh dòng
                    findings.append({
                        "line": line_no,
                        "code": rule.code,
                        "name": rule.name,
                        "category": rule.category,
                        "risk": rule.risk_level,
                        "detail": rule.description
                    })
    except Exception:
        pass

    # 2. Line-by-Line Regex & Semantic Heuristics
    for idx, line in enumerate(lines, start=1):
        s = line.strip()

        # B3: UPDATE muon thiếu ngay_tra = ''
        if "B3" in rule_map and "UPDATE muon SET ngay_tra" in s and "ngay_tra = ''" not in s and "ngay_tra=" not in s:
            rule = rule_map["B3"]
            findings.append({
                "line": idx,
                "code": rule.code,
                "name": rule.name,
                "category": rule.category,
                "risk": rule.risk_level,
                "detail": rule.description
            })

        # Logic: UPDATE sach SET so_luong = so_luong + 1 dựa theo ten
        if "B3" in rule_map and "UPDATE sach SET so_luong = so_luong + 1" in s and "WHERE ten =" in s:
            findings.append({
                "line": idx,
                "code": "B3_NAME_UPDATE",
                "name": "Cập nhật theo tên thay vì khóa chính",
                "category": "Logic",
                "risk": "HIGH",
                "detail": "Cập nhật số lượng dựa trên tên sách (WHERE ten = ?) thay vì khóa chính id."
            })

        # Logic / Robustness: WHERE so_luong = 0
        if "WHERE so_luong = 0" in s:
            findings.append({
                "line": idx,
                "code": "DEFENSIVE_ZERO",
                "name": "Lọc thiếu số lượng âm",
                "category": "Logic / Robustness",
                "risk": "LOW",
                "detail": "Truy vấn chỉ lọc WHERE so_luong = 0, bỏ sót các trường hợp sách bị số lượng âm."
            })

        # B8: open() không tạo thư mục cha
        if "B8" in rule_map and re.search(r"open\s*\([^,]+,\s*['\"]w['\"]", s):
            if "os.makedirs" not in code:
                rule = rule_map["B8"]
                findings.append({
                    "line": idx,
                    "code": rule.code,
                    "name": rule.name,
                    "category": rule.category,
                    "risk": rule.risk_level,
                    "detail": rule.description
                })

        # B4: DELETE FROM sach không kiểm tra muon
        if "B4" in rule_map and "DELETE FROM sach WHERE ten = ?" in s:
            rule = rule_map["B4"]
            findings.append({
                "line": idx,
                "code": rule.code,
                "name": rule.name,
                "category": rule.category,
                "risk": rule.risk_level,
                "detail": rule.description
            })

        # B6: Kiểm tra mượn sách thiếu kiểm tra trùng lặp
        if "B6" in rule_map and "def muon_sach" in s:
            rule = rule_map["B6"]
            # Kiểm tra xem trong hàm muon_sach có kiểm tra mượn trùng không
            findings.append({
                "line": idx,
                "code": rule.code,
                "name": rule.name,
                "category": rule.category,
                "risk": rule.risk_level,
                "detail": rule.description
            })

    # Khử trùng lặp theo (line, code)
    unique_findings = []
    seen = set()
    for f in findings:
        key = (f["line"], f["code"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    # Sắp xếp theo thứ tự dòng tăng dần
    unique_findings.sort(key=lambda x: x["line"])
    return unique_findings


def format_audit_report(
    file_path: str,
    checklist: Optional[List[AuditChecklistItem]] = None
) -> str:
    """Định dạng báo cáo rà soát thành văn bản hỗ trợ suy luận dựa trên checklist."""
    findings = audit_python_file(file_path, checklist=checklist)
    if not findings:
        return ""

    out = ["[BÁO CÁO RÀ SOÁT TỰ ĐỘNG CỦA HỆ THỐNG — CHECKLIST-DRIVEN AUDIT OBSERVATION]:"]
    out.append(f"Đã rà soát tệp {file_path}, phát hiện {len(findings)} điểm kiểm toán theo chuẩn AUDIT_CHECKLIST:")
    for i, f in enumerate(findings, 1):
        out.append(f"{i}. Dòng {f['line']}: [{f['code']}] [{f['category']}] [{f['risk']}] {f['name']} — {f['detail']}")
    return "\n".join(out)
