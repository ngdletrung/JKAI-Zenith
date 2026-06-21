import re
import ast
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field

@dataclass
class RiskFactor:
    level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    category: str
    description: str
    snippet: str = ""

@dataclass
class RiskReport:
    score: int = 0  # 0 to 100
    factors: List[RiskFactor] = field(default_factory=list)
    is_dangerous: bool = False

class SecurityAuditor:
    """
    🛡️ JKAI ZENITH: THẨM ĐỊNH VIÊN AN NINH (SECURITY AUDITOR v1.0)
    Phân tích tĩnh (Static Analysis) các thay đổi mã nguồn để phát hiện rủi ro.
    """

    DANGEROUS_FUNCTIONS = {
        'eval': 'Thực thi mã Python từ chuỗi (Vô cùng nguy hiểm)',
        'exec': 'Thực thi mã Python động',
        'os.system': 'Chạy lệnh shell hệ thống trực tiếp',
        'subprocess.Popen': 'Khởi tạo tiến trình con (Cần kiểm soát args)',
        'subprocess.call': 'Chạy lệnh hệ thống',
        'subprocess.run': 'Chạy lệnh hệ thống',
        'shutil.rmtree': 'Xóa thư mục đệ quy (Rủi ro mất dữ liệu)',
        'os.remove': 'Xóa tệp tin',
        'os.unlink': 'Xóa tệp tin',
        'pickle.loads': 'Deserialization không an toàn',
        'base64.b64decode': 'Có thể che giấu mã độc hoặc payload'
    }

    SUSPICIOUS_PATTERNS = [
        (r'https?://[^\s\'"]+', 'Phát hiện URL lạ (Nguy cơ rò rỉ dữ liệu hoặc tải mã độc)'),
        (r'\b[A-Za-z0-9+/]{40,}\b', 'Chuỗi Base64 dài (Nghi ngờ mã hóa payload)'),
        (r'(?i)chmod\s+\+x', 'Cấp quyền thực thi cho tệp tin'),
        (r'\.bashrc|\.profile|\/etc\/shadow|\/etc\/passwd', 'Truy cập tệp tin hệ thống nhạy cảm'),
        (r'nc\s+-e|bash\s+-i', 'Dấu hiệu Reverse Shell'),
        (r'(\d{1,3}\.){3}\d{1,3}', 'Phát hiện địa chỉ IP trực tiếp')
    ]

    def __init__(self):
        pass

    def audit_diff(self, diff_content: str) -> RiskReport:
        """Phân tích nội dung thay đổi (diff) thưa Master."""
        report = RiskReport()
        
        # 1. Phân tích các hàm nguy hiểm
        for func, desc in self.DANGEROUS_FUNCTIONS.items():
            pattern = rf'\b{func}\('
            matches = re.findall(pattern, diff_content)
            if matches:
                level = "HIGH" if func in ['eval', 'exec', 'os.system'] else "MEDIUM"
                report.factors.append(RiskFactor(
                    level=level,
                    category="DANGEROUS_FUNC",
                    description=f"{desc}: `{func}`",
                    snippet=func
                ))
                report.score += 20 if level == "HIGH" else 10

        # 2. Phân tích các Pattern nghi vấn
        for pattern, desc in self.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, diff_content)
            if matches:
                report.factors.append(RiskFactor(
                    level="MEDIUM",
                    category="SUSPICIOUS_PATTERN",
                    description=desc,
                    snippet=matches[0] if isinstance(matches[0], str) else str(matches[0])
                ))
                report.score += 15

        # 3. Phân tích ngữ cảnh Python (nếu là file .py)
        # (Ở đây ta chỉ quét sơ bộ qua regex, có thể mở rộng bằng AST nếu cần)
        
        # 4. Tổng kết rủi ro
        if report.score >= 40:
            report.is_dangerous = True
        
        # Cap score at 100
        report.score = min(report.score, 100)
        
        return report

    def format_report_for_log(self, report: RiskReport) -> str:
        """Định dạng báo cáo để hiển thị trên Nhật ký thưa Master."""
        if not report.factors:
            return "✅ Không phát hiện rủi ro mã nguồn đáng kể."
        
        status = "🚨 [RỦI RO CAO]" if report.is_dangerous else "⚠️ [CẢNH BÁO]"
        lines = [f"{status} Điểm rủi ro: **{report.score}/100**"]
        
        for factor in report.factors:
            lines.append(f"- **[{factor.level}]** {factor.category}: {factor.description}")
            
        return "\n".join(lines)

# Singleton Instance
auditor = SecurityAuditor()
