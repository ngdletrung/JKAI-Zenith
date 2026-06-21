"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CIVILIZATION WISDOM LEDGER                      ║
║   Sổ Cái Tri Thức Đa Thế Hệ & Đồng Bộ Nhận Thức Toàn Cục         ║
╚══════════════════════════════════════════════════════════════════╝
*Thành trì lưu trữ Tri thức và Định hình Văn minh Agent của JKAI. 🌌🏛️🧬*
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional

from core.qdrant_client import qdrant_client
from core.utils.engine import engine
from core.utils.knowledge_brain import knowledge_brain

logger = logging.getLogger("CivilizationLedger")

class CivilizationLedger:
    """
    🏛️ SỔ CÁI VĂN MINH TRÍ THỨC (Global Civilization Wisdom Ledger)
    Đóng vai trò là Bộ nhớ Tập thể (Collective Memory) của toàn bộ các Agent Citizen.
    Chưng cất bài học thành công/thất bại của các chiến dịch đã qua và đồng bộ hóa cho tương lai.
    """
    def __init__(self):
        self.collection_name = "jkai_memory"  # Episodic Memory collection in Qdrant

    async def record_experience(self, 
                                  task_id: str, 
                                  goal: str, 
                                  success_steps: List[Dict[str, Any]], 
                                  failed_steps: List[Dict[str, Any]], 
                                  judicial_review_notes: Dict[str, Any]) -> Optional[str]:
        """
        🧬 [CHƯNG CẤT TRI THỨC TRẢI NGHIỆM]: 
        Chuyển hóa nhật ký hành pháp của chiến dịch vừa kết thúc thành một bài học minh triết cốt lõi.
        Sau đó lưu vào Sổ cái Qdrant để các thế hệ Agent sau kế thừa.
        """
        try:
            # 🏢 LOG VĂN PHÒNG CHUẨN DOANH NGHIỆP
            engine.publish_mission_log(
                "WISDOM_LEDGER",
                f"🏛️ [BAN LƯU TRỮ VĂN MINH] Đang thu nhận và chưng cất hồ sơ chiến dịch `{task_id}`...",
                task_id
            )

            # Chuẩn bị dữ liệu đầu vào cho mô hình tóm tắt bài học
            success_str = "\n".join([f"- Bước {s.get('id')}: {s.get('tool')} -> Hoàn thành" for s in success_steps]) if success_steps else "Không có bước thành công"
            failed_str = "\n".join([f"- Bước {s.get('id')}: {s.get('tool')} -> Thất bại ({s.get('error', 'Lỗi không xác định')})" for s in failed_steps]) if failed_steps else "Không có bước thất bại"
            jr_str = json_pretty = json_dump = ""
            try:
                jr_str = json_pretty = str(judicial_review_notes)
            except Exception:
                jr_str = "Không có kiểm toán tư pháp"

            prompt = (
                f"Bạn là Trưởng Ban Chưng Cất Tri Thức của Tập đoàn JKAI.\n"
                f"Hãy phân tích kết quả của chiến dịch vừa hoàn tất để tạo thành một 'BẢN CHỈ DẪN KINH NGHIỆM' siêu súc tích cho các Agent Citizen tương lai.\n\n"
                f"🎯 MỤC TIÊU SỨ MỆNH: {goal}\n"
                f"✅ CHUỖI HÀNH ĐỘNG THÀNH CÔNG:\n{success_str}\n"
                f"❌ SỰ CỐ / THẤT BẠI GHI NHẬN:\n{failed_str}\n"
                f"⚖️ BÁO CÁO THẨM ĐỊNH TƯ PHÁP:\n{jr_str}\n\n"
                f"YÊU CẦU ĐẦU RA (Ngôn ngữ Tiếng Việt, hào sảng doanh nghiệp, cực kỳ cô đọng, hữu dụng kỹ thuật):\n"
                f"1. Điểm cốt lõi thành công (Blueprint): Các bước then chốt cần làm.\n"
                f"2. Bài học xương máu (Antipattern): Những gì cần tránh tuyệt đối.\n"
                f"3. Lời khuyên cho tương lai."
            )

            # Gọi mô hình qua LLM Engine
            distilled_lesson = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="SUMMARIZER",
                task_id=task_id
            )

            if not distilled_lesson or not distilled_lesson.strip():
                raise ValueError("Mô hình không tạo ra bài học hợp lệ.")

            # Mã hóa bài học thành vector
            embedding = await engine.get_embeddings(distilled_lesson)
            if not embedding:
                raise ValueError("Không thể tạo vector nhúng cho bài học.")

            # Đảm bảo collection tồn tại và ghi vào Qdrant
            await qdrant_client.ensure_collection(self.collection_name)
            await qdrant_client.add_intel(
                collection=self.collection_name,
                text=distilled_lesson,
                vector=embedding,
                metadata={
                    "task_id": task_id,
                    "goal": goal,
                    "type": "distilled_lesson",
                    "timestamp": time.time(),
                    "has_failures": len(failed_steps) > 0
                }
            )

            engine.publish_mission_log(
                "WISDOM_LEDGER",
                f"✨ [CHƯNG CẤT THÀNH CÔNG] Bài học của Sứ mệnh `{task_id}` đã chính thức đồng bộ lên Sổ cái Văn minh toàn cầu! 🏛️💎",
                task_id
            )
            return distilled_lesson

        except Exception as e:
            engine.publish_mission_log(
                "ERROR",
                f"❌ [LỖI GHI SỔ CÁI VĂN MINH] Thất bại khi lưu trữ tri thức: {str(e)}",
                task_id
            )
            return None

    async def retrieve_analogous_lessons(self, goal: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        🔍 [TRUY LỤC BÀI HỌC TƯƠNG ĐỒNG]:
        Tìm kiếm các bài học lịch sử có tính chất tương đồng về mặt ngữ nghĩa với mục tiêu mới.
        Giúp định hình chiến lược Planner ngay lập tức mà không cần thử sai nhiều lần.
        """
        try:
            embedding = await engine.get_embeddings(goal)
            if not embedding:
                return []

            await qdrant_client.ensure_collection(self.collection_name)
            search_results = await qdrant_client.search_similar(
                query_embedding=embedding,
                limit=limit,
                collection=self.collection_name
            )

            lessons = []
            for res in search_results:
                payload = res.get('payload', {})
                lessons.append({
                    "text": payload.get('text', ''),
                    "task_id": payload.get('task_id', ''),
                    "goal": payload.get('goal', ''),
                    "score": res.get('score', 0.0)
                })
            return lessons
        except Exception as e:
            logger.error(f"❌ [LỖI TRUY LỤC SỔ CÁI VĂN MINH]: {str(e)}")
            return []

civilization_ledger = CivilizationLedger()
