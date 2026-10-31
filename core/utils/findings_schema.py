import json
from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ValidationError


class FindingItem(BaseModel):
    """Chi tiết một mục phát hiện kiểm toán mã nguồn."""
    file: str = Field(description="Đường dẫn tương đối tới tệp mã nguồn được kiểm toán")
    line_count: Optional[int] = Field(default=None, description="Tổng số dòng thực tế đo đạc được")
    sha256_16: Optional[str] = Field(default=None, description="16 ký tự hex đầu của mã băm SHA-256")
    classes: List[str] = Field(default_factory=list, description="Danh sách các class định nghĩa trong tệp")
    functions: List[str] = Field(default_factory=list, description="Danh sách các hàm/phương thức định nghĩa trong tệp")
    mechanism: Optional[str] = Field(default=None, description="Giải thích cơ chế bảo mật hoặc logic hoạt động")
    severity: Optional[str] = Field(default=None, description="Mức độ nghiêm trọng (bắt buộc null nếu là needs_validation)")
    evidence: Optional[str] = Field(default=None, description="Bằng chứng trích xuất từ tệp (source trace: dòng, code snippet)")


class AuditReport(BaseModel):
    """
    C4 Implementation: Machine-Readable Findings Schema cho JKAI Zenith.
    Tham chiếu Cloudflare report-schema.json:
    Cung cấp định dạng JSON có cấu trúc, có thể kiểm định bằng máy (schema validation),
    phân loại rạch ròi 3 phán quyết: confirmed | needs_validation | rejected.
    """
    task_id: str = Field(description="Mã định danh nhiệm vụ (ví dụ: TASK-001)")
    verdict: Literal["confirmed", "needs_validation", "rejected"] = Field(
        description="Phán quyết cuối cùng của đợt kiểm toán"
    )
    findings: List[FindingItem] = Field(default_factory=list, description="Danh sách các phát hiện kỹ thuật")
    canary: Optional[str] = Field(default=None, description="Mã Canary chống rò rỉ nếu nhiệm vụ yêu cầu")
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Tỷ lệ bao phủ kiểm toán từ Coverage Ledger")
    unresolved_facts: List[str] = Field(
        default_factory=list, 
        description="Danh sách các sự kiện chưa thể giải quyết (bắt buộc có khi verdict == needs_validation)"
    )
    notes: Optional[str] = Field(default=None, description="Ghi chú tổng kết hoặc khuyến nghị kỹ thuật")


def validate_findings_dict(data: dict) -> Tuple[bool, Optional[str], Optional[AuditReport]]:
    """Xác thực một dictionary đối chiếu với AuditReport schema."""
    try:
        report = AuditReport.model_validate(data)
        # Anti-Pattern #9 Guard: Không được có severity khi verdict == needs_validation
        if report.verdict == "needs_validation":
            for f in report.findings:
                if f.severity is not None:
                    return False, f"Anti-Pattern #9 vi phạm: Finding '{f.file}' có severity='{f.severity}' trong khi verdict='needs_validation'.", None
        return True, None, report
    except ValidationError as err:
        return False, str(err), None
    except Exception as ex:
        return False, f"Lỗi không xác định khi xác thực findings schema: {ex}", None


def validate_findings_json(json_str: str) -> Tuple[bool, Optional[str], Optional[AuditReport]]:
    """Xác thực một chuỗi JSON đối chiếu với AuditReport schema."""
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return False, "Dữ liệu JSON đầu vào phải là một Object/Dict.", None
        return validate_findings_dict(data)
    except json.JSONDecodeError as jde:
        return False, f"Chuỗi không phải JSON hợp lệ: {jde}", None
