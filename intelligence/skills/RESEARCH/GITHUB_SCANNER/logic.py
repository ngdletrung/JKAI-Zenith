import os
import sys
import logging

# [ZENITH FILE DIRECTIVE]
# - File: logic.py
# - Role: Implementation of GITHUB_SCANNER skill
# - Status: Active | Version: 1.0.0

# Thêm đường dẫn gốc vào sys.path để import các module khác
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import SEARCH_WEB_GLOBAL
from core.utils.engine import engine

logger = logging.getLogger("JKAI.GitHubScanner")

async def GITHUB_SCANNER(query: str) -> str:
    """
    Quét và phân tích xu hướng GitHub cho tháng 05/2026.
    
    Args:
        query (str): Chủ đề hoặc từ khóa cần quét (ví dụ: "AI", "Web Development").
        
    Returns:
        str: Bảng Markdown chứa kết quả quét.
    """
    # 1. Chuẩn hóa truy vấn tìm kiếm cho thời điểm tháng 05/2026
    search_query = f"trending github repositories {query} May 2026"
    logger.info(f"🔍 [GITHUB-SCANNER]: Đang trinh sát GitHub cho: {search_query}")
    
    # 2. Thực thi siêu tìm kiếm toàn cầu
    try:
        res = await SEARCH_WEB_GLOBAL(search_query, search_depth="advanced")
        
        if res.get("status") != "success":
            return f"❌ [ERROR]: Trình sát thất bại. Chi tiết: {res.get('msg', 'Unknown error')}"
        
        raw_data = res.get("answer") or res.get("output", {}).get("content", "")
        if not raw_data:
            return "⚠️ [WARNING]: Không tìm thấy dữ liệu thực tế cho xu hướng GitHub này trong tháng 05/2026."
            
        # 3. Sử dụng LLM Engine để chuyển đổi dữ liệu thô thành bảng Markdown chuẩn Zenith
        prompt = (
            "Bạn là Chuyên gia Phân tích GitHub của JKAI Zenith.\n"
            "Nhiệm vụ: Trích xuất các kho lưu trữ (repos) nổi bật từ dữ liệu thô bên dưới.\n"
            "Yêu cầu:\n"
            "- Trình bày dưới dạng bảng Markdown: | Tên Repo | Link | Số sao | Mô tả ngắn gọn |\n"
            "- Chỉ lấy các repo liên quan đến xu hướng tháng 05/2026.\n"
            "- Nếu không có thông tin về số sao, ghi 'N/A'.\n"
            "- Trả về duy nhất bảng Markdown, không có văn bản dẫn nhập hoặc kết luận.\n\n"
            f"DỮ LIỆU THÔ:\n{raw_data}"
        )
        
        engine_res = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="SUMMARIZER",
            task_id="github_scanner_extraction"
        )
        
        table_content = ""
        if isinstance(engine_res, dict) and "answer" in engine_res:
            table_content = engine_res["answer"]
        else:
            table_content = str(engine_res)
            
        return table_content

    except Exception as e:
        logger.exception(f"💥 [CRITICAL]: Lỗi hệ thống khi thực thi GITHUB_SCANNER: {e}")
        return f"❌ [SYSTEM ERROR]: Đã xảy ra lỗi khi quét GitHub: {str(e)}"
