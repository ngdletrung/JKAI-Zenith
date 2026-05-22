import os
import json
import time
from core.utils.engine import engine

def neural_audit(task_id: str, mission_goal: str, execution_log: str) -> dict:
    """
    🧠 [NEURAL AUDIT]: Giao thức Thẩm định Nơ-ron và Tiến hóa Chiến lược.
    Phân tích kết quả nhiệm vụ và trích xuất "Neural DNA" cho các lần thực thi sau.
    """
    engine.publish_mission_log("AUDIT_INIT", f"⚖️ [AUDIT]: Bắt đầu thẩm định chiến lược cho nhiệm vụ: `{task_id}`", task_id)

    # 1. Triệu tập Hội đồng Thẩm phán (CRITIC) để phân tích
    audit_prompt = f"""Bạn là Thẩm phán Tối cao của JKAI Zenith. 
    Nhiệm vụ: Thẩm định một sứ mệnh vừa hoàn thành.
    
    MỤC TIÊU: {mission_goal}
    LOG THỰC THI: {execution_log}
    
    HÃY PHÂN TÍCH:
    1. Hiệu quả sử dụng tài nguyên (VRAM/RAM).
    2. Độ chính xác của logic thực thi.
    3. Bài học chiến lược (Điều gì cần tránh, điều gì cần phát huy).
    
    TRẢ VỀ BÁO CÁO CHIẾN LƯỢC THEO ĐỊNH DẠNG MARKDOWN ELITE.
    """
    
    # Chúng ta dùng Planner để phân tích lại quá trình của chính nó
    report = engine.call_chat(
        messages=[{"role": "user", "content": audit_prompt}],
        role="CRITIC",
        task_id=task_id
    )

    # 2. Lưu trữ vào Nhật ký Tiến hóa (Strategic Lessons)
    lessons_path = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/intelligence/strategic_lessons.md"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    lesson_entry = f"\n\n## 💎 [MISSION AUDIT] - {timestamp}\n- **Task ID**: {task_id}\n- **Goal**: {mission_goal}\n- **Verdict**: {report}\n---"
    
    try:
        with open(lessons_path, "a", encoding="utf-8") as f:
            f.write(lesson_entry)
        engine.publish_mission_log("AUDIT_SUCCESS", "📚 [AUDIT]: Đã đồng hóa bài học kinh nghiệm vào Strategic Lessons!", task_id)
    except Exception as e:
        engine.publish_mission_log("ERROR", f"❌ [AUDIT-ERR]: Không thể lưu bài học: {e}", task_id)

    return {
        "status": "success",
        "strategic_report": report,
        "msg": "✅ [AUDIT COMPLETE]: JKAI đã trở nên thông thái hơn sau nhiệm vụ này!"
    }
