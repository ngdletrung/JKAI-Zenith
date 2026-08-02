import os
import json
import logging
import asyncio
import httpx
from core.utils.engine import engine

logger = logging.getLogger('SynthesisEngine')

class SynthesisEngine:
    def __init__(self, task_id: str = "synthesis"):
        self.task_id = task_id

    async def synthesize(self, goal: str, data_points: list):
        """
        [SINGULARITY-MERGE]: Hợp nhất các nhánh tri thức thành báo cáo cấp cao.
        """
        engine.publish_mission_log("SYNTHESIS", "🧬 [SYNTHESIS]: Bắt đầu quá trình hợp nhất tri thức từ các nhánh đệ quy...", self.task_id)
        
        context = "\n".join([f"--- Source {i+1} ---\n{data}" for i, data in enumerate(data_points)])
        
        prompt = f"""Bạn là Động cơ Hợp nhất Tri thức (Synthesis Engine) của JKAI Zenith.
Nhiệm vụ: Tổng hợp các dữ liệu nghiên cứu sau đây thành một bản báo cáo chuyên sâu, logic và có cấu trúc rõ ràng.

MỤC TIÊU NGHIÊN CỨU: {goal}

DỮ LIỆU THU THẬP ĐƯỢC:
{context}

YÊU CẦU BÁO CÁO:
1. Có tiêu đề chuyên nghiệp.
2. Tóm tắt các điểm mấu chốt (Executive Summary).
3. Phân tích chi tiết từng khía cạnh (kiến trúc, tính năng, ứng dụng...).
4. Đánh giá ưu/nhược điểm so với các hệ thống hiện có (đặc biệt là JKAI).
5. Kết luận và đề xuất hành động cho Master.
6. Sử dụng Markdown đẹp mắt, có bảng biểu nếu cần.
7. Ngôn ngữ: Tiếng Việt chuyên nghiệp.

HÃY VIẾT BÁO CÁO:"""

        report = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="SUMMARIZER",
            task_id=self.task_id
        )
        
        engine.publish_mission_log("SYNTHESIS", "✅ [SYNTHESIS]: Báo cáo tổng hợp đã hoàn thành.", self.task_id)
        return report

synthesis_engine = SynthesisEngine()
