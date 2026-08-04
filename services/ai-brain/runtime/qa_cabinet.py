import json
import logging
import asyncio
import time
from core.utils.engine import engine

logger = logging.getLogger('QA_CABINET')

class QACabinet:
    """
    JKAI ZENITH: BAN KIEM DUYET CL (QA CABINET)
    Thực hiện đánh giá song song (Parallel Fan-out) qua 3 đặc vụ chuyên trách thưa Master:
    - code-reviewer (Độ sạch mã nguồn, Readability)
    - security-auditor (An ninh, Rò rỉ thông tin)
    - test-engineer (Độ phủ kiểm thử, Test cases)
    """

    def __init__(self):
        pass

    async def perform_fanout_review(self, goal: str, diff_text: str, task_id: str = "qa_fanout") -> dict:
        """Chạy song song 3 đặc vụ thẩm định mã nguồn thưa Master."""
        engine.publish_mission_log("QA", "[QA-CABINET]: Bắt đầu phân rã thẩm định song song qua 3 Ban chuyên trách...", task_id)
        
        t0 = time.time()
        
        # Tạo tasks cho 3 đặc vụ
        tasks = {
            "code_reviewer": self._run_code_reviewer(goal, diff_text, task_id),
            "security_auditor": self._run_security_auditor(goal, diff_text, task_id),
            "test_engineer": self._run_test_engineer(goal, diff_text, task_id)
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        reports = {}
        for name, res in zip(tasks.keys(), results):
            if isinstance(res, Exception):
                reports[name] = f"Error during review: {res}"
                engine.publish_mission_log("QA_ERR", f"[QA-FAIL]: Ban {name} gặp lỗi: {res}", task_id)
            else:
                reports[name] = res
        
        latency = (time.time() - t0) * 1000
        engine.publish_mission_log("QA", f"[QA-CABINET]: Hoàn tất thẩm định song song trong {latency:.0f}ms thưa Master.", task_id)
        
        # Tổng hợp báo cáo
        summary = (
            "--- [BÁO CÁO THẨM ĐỊNH TỔNG HỢP] ---\n\n"
            f"1. CODE REVIEWER:\n{reports.get('code_reviewer')}\n\n"
            f"2. SECURITY AUDITOR:\n{reports.get('security_auditor')}\n\n"
            f"3. TEST ENGINEER:\n{reports.get('test_engineer')}"
        )
        
        return {
            "status": "success",
            "summary": summary,
            "latency_ms": latency,
            "reports": reports
        }

    async def _run_code_reviewer(self, goal: str, diff_text: str, task_id: str) -> str:
        prompt = (
            "Bạn là Senior Code Reviewer của JKAI Zenith. Hãy đánh giá đoạn diff sau dựa trên:\n"
            "- Tính chính xác so với mục tiêu\n"
            "- Tính dễ đọc và tuân thủ quy chuẩn viết code\n"
            "- Kiến trúc và sự phụ thuộc\n"
            f"Mục tiêu: {goal}\n"
            f"Diff:\n{diff_text}"
        )
        res = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="CRITIC",
            task_id=task_id,
            skip_memory=True
        )
        return str(res)

    async def _run_security_auditor(self, goal: str, diff_text: str, task_id: str) -> str:
        prompt = (
            "Bạn là Chuyên gia An ninh Thông tin (Security Auditor) của JKAI Zenith. Hãy rà soát đoạn diff sau để:\n"
            "- Phát hiện rò rỉ khóa bí mật, API keys, mật khẩu\n"
            "- Phát hiện lỗi bảo mật nghiêm trọng (SQL injection, XSS, Buffer Overflow)\n"
            "- Kiểm tra tính an toàn của đầu vào dữ liệu\n"
            f"Mục tiêu: {goal}\n"
            f"Diff:\n{diff_text}"
        )
        res = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="CRITIC",
            task_id=task_id,
            skip_memory=True
        )
        return str(res)

    async def _run_test_engineer(self, goal: str, diff_text: str, task_id: str) -> str:
        prompt = (
            "Bạn là Test Engineer của JKAI Zenith. Hãy đánh giá đoạn diff sau và kiểm tra xem:\n"
            "- Các test case đã phủ đủ các trường hợp biên chưa?\n"
            "- Logic kiểm thử có chính xác và phản ánh đúng yêu cầu không?\n"
            "- Có bất kỳ lỗ hổng kiểm thử nào không?\n"
            f"Mục tiêu: {goal}\n"
            f"Diff:\n{diff_text}"
        )
        res = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="CRITIC",
            task_id=task_id,
            skip_memory=True
        )
        return str(res)
