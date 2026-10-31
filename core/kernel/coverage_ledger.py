import re
import json
from typing import List, Dict, Any, Optional, Set
from pathlib import Path


class CoverageLedger:
    """
    C3 Implementation: Deterministic Coverage Ledger cho các tác vụ kiểm toán (Audit Tasks).
    Đúc kết từ Cloudflare security-audit-skill:
    Theo dõi chính xác các tệp bắt buộc và các hạng mục kiểm định (checks),
    loại bỏ triệt để hiện tượng 'đọc 1 file rồi vội vã nộp bài'.
    """

    def __init__(self, task_id: str, goal: str = ""):
        self.task_id = task_id
        self.goal = goal or ""
        self.required_files: List[str] = self._extract_required_files(self.goal)
        self.read_files: Set[str] = set()
        self.file_metadata: Dict[str, Dict[str, Any]] = {}
        self.required_checks: List[str] = self._extract_required_checks(self.goal)
        self.completed_checks: Set[str] = set()
        self.check_evidence: Dict[str, str] = {}

    def _extract_required_files(self, goal: str) -> List[str]:
        if not goal:
            return []
        matches = re.findall(r"\b[\w/\\-]+\.py\b", goal)
        unique_files = []
        for m in matches:
            clean = m.replace("\\", "/").strip()
            if not clean.startswith("test_") and clean not in unique_files:
                unique_files.append(clean)
        return unique_files

    def _extract_required_checks(self, goal: str) -> List[str]:
        low = goal.lower()
        checks = []
        if any(k in low for k in ["dòng", "line", "line count", "line_count"]):
            checks.append("line_count")
        if any(k in low for k in ["sha", "sha256", "sha-256", "mã băm"]):
            checks.append("sha256")
        if any(k in low for k in ["class", "lớp"]):
            checks.append("class_list")
        if any(k in low for k in ["hàm", "function", "method", "phương thức"]):
            checks.append("function_list")
        if any(k in low for k in ["cơ chế", "mechanism", "giải thích", "phối hợp"]):
            checks.append("mechanism_explanation")
        if any(k in low for k in ["canary", "np-"]) or re.search(r"np\d-", low):
            checks.append("canary_verification")
        return checks

    def record_file_read(self, file_path: str, lines: Optional[int] = None, sha256_prefix: Optional[str] = None):
        """Ghi nhận một tệp đã được đọc thành công qua view_file hoặc tool."""
        norm_path = file_path.replace("\\", "/").strip()
        self.read_files.add(norm_path)
        meta = self.file_metadata.get(norm_path, {})
        if lines is not None:
            meta["lines"] = lines
        if sha256_prefix is not None:
            meta["sha256_16"] = sha256_prefix
        self.file_metadata[norm_path] = meta

    def record_check_completed(self, check_name: str, evidence: str = ""):
        """Ghi nhận một hạng mục kiểm định đã hoàn tất có bằng chứng."""
        self.completed_checks.add(check_name)
        if evidence:
            self.check_evidence[check_name] = evidence

    def evaluate_coverage(self) -> Dict[str, Any]:
        """Tính toán tỷ lệ phần trăm bao phủ kiểm toán."""
        # Kiểm tra tỷ lệ đọc file
        matched_files = set()
        for req in self.required_files:
            req_name = Path(req).name.lower()
            for rd in self.read_files:
                if req in rd or req_name == Path(rd).name.lower():
                    matched_files.add(req)
                    break

        file_coverage = (len(matched_files) / len(self.required_files)) if self.required_files else 1.0
        check_coverage = (len(self.completed_checks) / len(self.required_checks)) if self.required_checks else 1.0

        # Trọng số: Đọc file chiếm 60%, hoàn thành các checks chiếm 40%
        if self.required_files and self.required_checks:
            total_percent = (file_coverage * 0.6 + check_coverage * 0.4) * 100.0
        elif self.required_files:
            total_percent = file_coverage * 100.0
        elif self.required_checks:
            total_percent = check_coverage * 100.0
        else:
            total_percent = 100.0

        missing_files = [f for f in self.required_files if f not in matched_files]
        missing_checks = [c for c in self.required_checks if c not in self.completed_checks]

        is_complete = (len(missing_files) == 0 and len(missing_checks) == 0)

        return {
            "task_id": self.task_id,
            "required_files": self.required_files,
            "read_files": list(self.read_files),
            "missing_files": missing_files,
            "required_checks": self.required_checks,
            "completed_checks": list(self.completed_checks),
            "missing_checks": missing_checks,
            "coverage_percent": round(total_percent, 1),
            "is_complete": is_complete,
            "file_metadata": self.file_metadata,
        }

    def files_fully_read(self) -> bool:
        """True only when the goal named at least one required file and all of them were read.

        An empty required_files list must not count as complete: evaluate_coverage()
        would otherwise yield missing_files=[] and is_complete=True.
        """
        if not self.required_files:
            return False
        missing = self.evaluate_coverage().get("missing_files") or []
        return len(missing) == 0

    def to_json(self) -> str:
        return json.dumps(self.evaluate_coverage(), ensure_ascii=False, indent=2)

    def to_markdown_summary(self) -> str:
        report = self.evaluate_coverage()
        status_icon = "✅" if report["is_complete"] else "⚠️"
        lines = [
            f"### {status_icon} Báo Cáo Độ Bao Phủ Kiểm Toán (Coverage Ledger: {report['coverage_percent']}%)",
            f"- **Tệp bắt buộc ({len(report['read_files'])}/{len(report['required_files'])}):** " + (", ".join(report['required_files']) or "Không có"),
            f"- **Tệp còn thiếu:** " + (", ".join(report['missing_files']) if report['missing_files'] else "Không có (Đã đọc đủ)"),
            f"- **Hạng mục kiểm tra ({len(report['completed_checks'])}/{len(report['required_checks'])}):** " + (", ".join(report['completed_checks']) or "Chưa có"),
            f"- **Hạng mục còn thiếu:** " + (", ".join(report['missing_checks']) if report['missing_checks'] else "Hoàn tất 100%"),
        ]
        return "\n".join(lines)
