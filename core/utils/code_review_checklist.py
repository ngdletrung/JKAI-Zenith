"""
Physical Code Review Checklist & Rule Definitions for JKAI Exoskeleton Substrate.
Contains standard detection criteria for security, logic, robustness, and stub patterns.
Includes B5 (silent datetime parsing) and B6 (business logic concurrency/duplicate state).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass(frozen=True)
class AuditChecklistItem:
    code: str
    category: str
    name: str
    description: str
    risk_level: str
    sample_pattern: str


AUDIT_CHECKLIST: List[AuditChecklistItem] = [
    AuditChecklistItem(
        code="B1_B2",
        category="Bảo mật",
        name="SQL Injection (Nối chuỗi / Format)",
        description="Nối chuỗi thô hoặc dùng toán tử %/f-string trong cur.execute() thay vì parameterized query (?).",
        risk_level="CRITICAL",
        sample_pattern='cur.execute("SELECT ... " + var)'
    ),
    AuditChecklistItem(
        code="B3",
        category="Logic",
        name="Cập nhật thiếu điều kiện lọc trạng thái",
        description="Câu lệnh UPDATE hoặc DELETE thiếu điều kiện lọc trạng thái hiện tại (ví dụ thiếu AND ngay_tra = ''), gây ghi đè dữ liệu lịch sử.",
        risk_level="HIGH",
        sample_pattern="UPDATE muon SET ngay_tra = ? WHERE ten_doc_gia = ? AND ten_sach = ?"
    ),
    AuditChecklistItem(
        code="B4",
        category="Toàn vẹn dữ liệu",
        name="Xóa bản ghi cha khi bản ghi con đang tham chiếu",
        description="Xóa trực tiếp bản ghi khỏi bảng chính mà không kiểm tra ràng buộc khóa ngoại trong bảng giao dịch (gây mồ côi dữ liệu).",
        risk_level="HIGH",
        sample_pattern="DELETE FROM sach WHERE ten = ?"
    ),
    AuditChecklistItem(
        code="B5",
        category="Robustness",
        name="Phân tích ngày tháng thiếu kiểm soát ngoại lệ (Silent Date Parse Crash)",
        description="Sử dụng datetime.strptime() trực tiếp trên dữ liệu người dùng/chuỗi lưu trữ mà không bọc trong try/except ValueError, gây crash chương trình khi gặp dữ liệu ngày tháng không chuẩn.",
        risk_level="MEDIUM",
        sample_pattern='datetime.strptime(ngay_str, "%d/%m/%Y")'
    ),
    AuditChecklistItem(
        code="B6",
        category="Logic nghiệp vụ",
        name="Bỏ qua kiểm tra trùng lặp trạng thái nghiệp vụ (Duplicate State Check)",
        description="Thực hiện hành động mượn/đăng ký mới mà không kiểm tra xem đối tượng/độc giả đã đang nắm giữ tài nguyên đó chưa (cho phép mượn trùng cuốn sách chưa trả).",
        risk_level="HIGH",
        sample_pattern="SELECT * FROM muon WHERE ten_doc_gia = ? AND ten_sach = ? AND ngay_tra = ''"
    ),
    AuditChecklistItem(
        code="B7",
        category="Stub",
        name="Mã giả lập / Placeholder chưa hoàn thiện",
        description="Hàm chỉ trả về hằng số cứng (stub mock ví dụ return 42 hoặc TODO) mà không thực hiện logic tính toán nghiệp vụ thực tế.",
        risk_level="LOW",
        sample_pattern="return 42"
    ),
    AuditChecklistItem(
        code="B8",
        category="Robustness",
        name="Ghi tệp tin không kiểm tra thư mục cha",
        description="Mở tệp để ghi bằng open(path, 'w') mà không đảm bảo thư mục cha đã tồn tại qua os.makedirs(..., exist_ok=True).",
        risk_level="MEDIUM",
        sample_pattern="with open(duong_dan, 'w') as f:"
    ),
]


def get_checklist_json() -> str:
    """Xuất danh mục checklist kiểm toán dưới dạng JSON chuẩn."""
    return json.dumps([asdict(item) for item in AUDIT_CHECKLIST], ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(get_checklist_json())
