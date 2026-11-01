# -*- coding: utf-8 -*-
"""
Phân loại phán quyết tư pháp (T5 Judicial Review) trước khi kết thúc mission.

Fail-closed: phán quyết méo mó (không phải dict) hoặc FAIL mà không có bằng
chứng nào thì mission phải dừng. FAIL một phần (0 < score < 1) chỉ cảnh báo —
dừng ở đó sẽ biến một lỗi báo sai thành một lỗi vận hành.
"""

STOP = "stop"
PARTIAL = "partial"
PASS = "pass"


def classify_judicial_outcome(judicial_review) -> str:
    if not isinstance(judicial_review, dict):
        return STOP
    try:
        score = float(judicial_review.get("accuracy_score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    if judicial_review.get("verdict") != "FAIL":
        return PASS
    return STOP if score <= 0.0 else PARTIAL
