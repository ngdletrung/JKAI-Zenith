import os
import json
import asyncio
from typing import Dict, Any, List
from core.utils.engine import engine

class ExecutiveForge:
    def __init__(self):
        self.role = "STRATEGIC_ANALYST"

    async def forge_strategic_proposal(self, project_data: str, objectives: str, task_id: str = "sys") -> str:
        """Kiến tạo đề xuất chiến lược dựa trên dữ liệu và mục tiêu."""
        engine.publish_mission_log("EXECUTIVE", "🏛️ Đang khởi động Lò đúc Chiến lược...", task_id)
        
        prompt = f"""
        [HỆ THỐNG KIẾN TẠO CHIẾN LƯỢC ZENITH v2.0]
        Nhiệm vụ: Soạn thảo một BẢN ĐỀ XUẤT CHIẾN LƯỢC (Strategic Proposal) đẳng cấp Elite.
        
        DỮ LIỆU DỰ ÁN:
        {project_data}
        
        MỤC TIÊU CỦA MASTER:
        {objectives}
        
        YÊU CẦU ĐỊNH DẠNG:
        1. Sử dụng văn phong sắc sảo, chuyên nghiệp, phong cách Sovereign.
        2. Cấu trúc gồm:
           - Tầm nhìn & Mục tiêu.
           - Phân tích Thực trạng (dựa trên dữ liệu).
           - Giải pháp Chiến lược (Đề xuất cụ thể).
           - Lộ trình thực thi (Roadmap).
           - Đánh giá Rủi ro & Hiệu quả.
        3. Trình bày bằng Markdown Elite, sử dụng các ký hiệu biểu tượng (Icons) chuẩn Zenith.
        """
        
        engine.publish_progress(40, "Đang chưng cất dữ liệu đa chiều...", task_id)
        proposal = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role=self.role,
            task_id=task_id
        )
        
        engine.publish_mission_log("EXECUTIVE", "✅ Đã đúc xong Bản đề xuất Chiến lược!", task_id)
        engine.publish_progress(100, "Nhiệm vụ hoàn tất.", task_id)
        
        return proposal

    async def generate_executive_summary(self, complex_content: str, task_id: str = "sys") -> str:
        """Tóm tắt điều hành dành riêng cho Tổng Giám Đốc."""
        engine.publish_mission_log("EXECUTIVE", "📊 Đang cô đọng thông tin cho Master...", task_id)
        
        prompt = f"""
        Tóm tắt nội dung sau đây thành một BẢN TÓM TẮT ĐIỀU HÀNH (Executive Summary).
        - Chỉ tập trung vào các thông số quan trọng nhất (KPIs).
        - Đưa ra khuyến nghị hành động ngay lập tức.
        - Tối đa 500 từ.
        
        NỘI DUNG:
        {complex_content}
        """
        
        summary = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="CHIEF_OF_STAFF",
            task_id=task_id
        )
        return summary

# 🚀 Singleton
_instance = ExecutiveForge()

async def forge_proposal(**kwargs):
    return await _instance.forge_strategic_proposal(**kwargs)

async def summarize(**kwargs):
    return await _instance.generate_executive_summary(**kwargs)
